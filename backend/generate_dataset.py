"""
Orion Training Dataset Generator
==================================
Runs against your existing Orion FastAPI graph output (or directly against
the in-memory graph) and produces a JSONL dataset of (context, question, answer)
triples ready for fine-tuning.

Usage
-----
# Option A: Point at a live repo (Orion analyzes it internally)
python generate_dataset.py --repo /path/to/your/repo --output dataset.jsonl

# Option B: Point at a saved Orion graph JSON export
python generate_dataset.py --graph graph_export.json --output dataset.jsonl

# Option C: Point at a directory of graph JSON exports
python generate_dataset.py --graph-dir ./graphs/ --output dataset.jsonl

# Add LLM paraphrasing (requires ANTHROPIC_API_KEY in env)
python generate_dataset.py --repo /path/to/repo --output dataset.jsonl --paraphrase

Dependencies
------------
pip install anthropic networkx tqdm
Your Orion backend must be importable OR you use the --graph JSON export mode.
"""

import json
import os
import sys
import random
import argparse
from collections import defaultdict, deque
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:  # Keep graph-only generation usable with the minimal backend install.
    def tqdm(iterable, **_kwargs):
        return iterable

# ── reproducibility ──────────────────────────────────────────────────────────
random.seed(42)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — Graph loading
# ─────────────────────────────────────────────────────────────────────────────

class OrionGraph:
    """
    Thin wrapper around Orion's graph data that exposes the traversal
    operations needed for dataset generation.
    """

    def __init__(self, data: dict):
        self.nodes: dict[str, dict] = data.get("nodes", {})
        self.edges: list[dict] = data.get("edges", [])

        # Pre-build adjacency for fast traversal
        self._callers: dict[str, list[str]] = defaultdict(list)   # dst → [src]
        self._callees: dict[str, list[str]] = defaultdict(list)   # src → [dst]
        self._imports: dict[str, list[str]] = defaultdict(list)   # src → [dst]
        self._declares: dict[str, list[str]] = defaultdict(list)  # src → [dst]

        for edge in self.edges:
            src, dst, etype = edge["src"], edge["dst"], edge["type"]
            if etype == "calls":
                self._callers[dst].append(src)
                self._callees[src].append(dst)
            elif etype == "imports":
                self._imports[src].append(dst)
            elif etype == "declares":
                self._declares[src].append(dst)

    # ── basic accessors ───────────────────────────────────────────────────────

    def callers(self, symbol: str) -> list[str]:
        return sorted(set(self._callers.get(symbol, [])))

    def callees(self, symbol: str) -> list[str]:
        return sorted(set(self._callees.get(symbol, [])))

    def imports_of(self, symbol: str) -> list[str]:
        return sorted(set(self._imports.get(symbol, [])))

    def declares(self, symbol: str) -> list[str]:
        return sorted(set(self._declares.get(symbol, [])))

    def node_type(self, symbol: str) -> str:
        return self.nodes.get(symbol, {}).get("type", "unknown")

    def node_file(self, symbol: str) -> str:
        return self.nodes.get(symbol, {}).get("file", "unknown")

    def all_functions(self) -> list[str]:
        return [s for s, d in self.nodes.items() if d.get("type") in ("function", "method")]

    def all_modules(self) -> list[str]:
        return [s for s, d in self.nodes.items() if d.get("type") == "module"]

    def all_classes(self) -> list[str]:
        return [s for s, d in self.nodes.items() if d.get("type") == "class"]

    # ── graph traversal ───────────────────────────────────────────────────────

    def blast_radius(self, symbol: str, max_depth: int = 4) -> list[str]:
        """BFS upstream: everything that transitively calls symbol."""
        visited, queue = set(), deque([(symbol, 0)])
        result = []
        while queue:
            node, depth = queue.popleft()
            if node in visited or depth > max_depth:
                continue
            visited.add(node)
            for caller in self._callers.get(node, []):
                if caller not in visited:
                    result.append(caller)
                    queue.append((caller, depth + 1))
        return sorted(set(result))

    def shortest_path(self, src: str, dst: str, max_depth: int = 6) -> list[str] | None:
        """BFS call-path from src to dst. Returns node list or None."""
        if src == dst:
            return [src]
        queue = deque([(src, [src])])
        visited = {src}
        while queue:
            node, path = queue.popleft()
            if len(path) > max_depth:
                continue
            for callee in self._callees.get(node, []):
                if callee == dst:
                    return path + [callee]
                if callee not in visited:
                    visited.add(callee)
                    queue.append((callee, path + [callee]))
        return None

    def subgraph_context(self, symbol: str, depth: int = 1) -> str:
        """
        Serialise the local neighbourhood of a symbol into a compact text
        block that becomes the [GRAPH] context fed to the model.
        """
        lines = [
            f"Symbol: {symbol}",
            f"Type: {self.node_type(symbol)}",
            f"File: {self.node_file(symbol)}",
        ]

        callers = self.callers(symbol)
        callees = self.callees(symbol)
        imports = self.imports_of(symbol)
        declares = self.declares(symbol)

        if callers:
            lines.append(f"Called by: {', '.join(callers)}")
        else:
            lines.append("Called by: (nothing — this is a root or entry point)")

        if callees:
            lines.append(f"Calls: {', '.join(callees)}")
        else:
            lines.append("Calls: (nothing — this is a leaf function)")

        if imports:
            lines.append(f"Imports: {', '.join(imports)}")

        if declares:
            lines.append(f"Declares: {', '.join(declares)}")

        # depth-1 neighbourhood
        if depth >= 1:
            for caller in callers[:5]:   # cap to keep context tight
                c2 = self.callers(caller)
                if c2:
                    lines.append(f"  {caller} ← called by: {', '.join(c2[:4])}")
            for callee in callees[:5]:
                c2 = self.callees(callee)
                if c2:
                    lines.append(f"  {callee} → calls: {', '.join(c2[:4])}")

        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — Inline Orion analyzer
# ─────────────────────────────────────────────────────────────────────────────

def _build_graph_from_repo(repo_path: str) -> OrionGraph:
    """
    Uses the real Orion backend to scan the project.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app.scanner.scanner import ProjectScanner

    print(f"Running Orion scanner on {repo_path}...")
    scanner = ProjectScanner()
    result, index = scanner.scan(repo_path)
    
    kg = index.knowledge_graph
    
    nodes = {}
    edges = []
    
    for node_id, node in kg.nodes.items():
        nodes[node_id] = {
            "type": node.type.value,
            "file": str(node.path) if node.path else "unknown"
        }
        
    for edge in kg.edges:
        edges.append({
            "src": edge.source,
            "dst": edge.target,
            "type": edge.type.value
        })
        
    return OrionGraph({"nodes": nodes, "edges": edges})


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — QA generators
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are Orion, an expert code structure analyst. "
    "Given a knowledge graph context extracted from a Python repository, "
    "answer the developer's question accurately and concisely. "
    "Base your answer solely on the graph data provided."
)

def _make_example(context: str, question: str, answer: str) -> dict:
    """Return an Azure/OpenAI-compatible SFT chat example.

    ``instruction/input/output`` was used by the original prototype, but is
    not accepted by standard chat fine-tuning validators.  Keep the graph
    context in the user turn so the model learns to ground answers in it.
    """
    user_content = f"[GRAPH CONTEXT]\n{context}\n\n[QUESTION]\n{question}"
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": answer},
        ],
    }


def gen_callers(graph: OrionGraph, symbol: str) -> list[dict]:
    callers = graph.callers(symbol)
    examples = []

    questions = [
        f"What functions call `{symbol}`?",
        f"Which symbols have a direct call edge to `{symbol}`?",
        f"Who are the direct callers of `{symbol}`?",
        f"Show me everything that calls `{symbol}`.",
    ]

    if callers:
        answer = (
            f"`{symbol}` is directly called by {len(callers)} symbol(s): "
            + ", ".join(f"`{c}`" for c in callers)
            + "."
        )
    else:
        answer = (
            f"`{symbol}` has no direct callers in this graph. "
            "It is either an entry point, a test target called externally, "
            "or a utility that is not yet wired up."
        )

    ctx = graph.subgraph_context(symbol)
    for q in questions[:2]:
        examples.append(_make_example(ctx, q, answer))

    return examples


def gen_callees(graph: OrionGraph, symbol: str) -> list[dict]:
    callees = graph.callees(symbol)
    if not callees:
        return []

    questions = [
        f"What does `{symbol}` call?",
        f"List the functions that `{symbol}` directly invokes.",
        f"What are the direct dependencies of `{symbol}`?",
    ]

    answer = (
        f"`{symbol}` directly calls {len(callees)} symbol(s): "
        + ", ".join(f"`{c}`" for c in callees)
        + "."
    )

    ctx = graph.subgraph_context(symbol)
    return [_make_example(ctx, q, answer) for q in questions[:2]]


def gen_blast_radius(graph: OrionGraph, symbol: str) -> list[dict]:
    blast = graph.blast_radius(symbol)
    if not blast:
        return []

    questions = [
        f"What is the blast radius of changing `{symbol}`?",
        f"If I modify `{symbol}`, what else could break?",
        f"What would be affected by a breaking change to `{symbol}`?",
    ]

    answer = (
        f"Changing `{symbol}` could transitively affect {len(blast)} symbol(s): "
        + ", ".join(f"`{b}`" for b in blast[:15])
        + ("..." if len(blast) > 15 else "")
        + ". These are all symbols that call `{symbol}` directly or indirectly "
        "through the call graph."
    ).replace("{symbol}", symbol)

    ctx = graph.subgraph_context(symbol, depth=1)
    return [_make_example(ctx, q, answer) for q in questions[:2]]


def gen_shortest_path(graph: OrionGraph, symbol: str) -> list[dict]:
    callees = graph.callees(symbol)
    if not callees:
        return []

    examples = []
    candidates = random.sample(callees, min(3, len(callees)))
    for intermediate in candidates:
        deep = graph.callees(intermediate)
        for target in random.sample(deep, min(2, len(deep))):
            path = graph.shortest_path(symbol, target)
            if path and 2 <= len(path) <= 5:
                path_str = " → ".join(f"`{p}`" for p in path)
                answer = (
                    f"The shortest call path from `{symbol}` to `{target}` "
                    f"is {len(path) - 1} hop(s): {path_str}."
                )
                ctx = graph.subgraph_context(symbol, depth=1)
                q = f"What is the shortest call path from `{symbol}` to `{target}`?"
                examples.append(_make_example(ctx, q, answer))
                break

    return examples


def gen_leaf_or_root(graph: OrionGraph, symbol: str) -> list[dict]:
    callers = graph.callers(symbol)
    callees = graph.callees(symbol)

    if not callers and not callees:
        return []

    ctx = graph.subgraph_context(symbol)
    examples = []

    if not callers:
        q = f"Is `{symbol}` an entry point or a leaf function?"
        a = (
            f"`{symbol}` is a **root/entry point**: it has no callers in this graph "
            f"but calls {len(callees)} other symbol(s). It is likely an entry point, "
            "a CLI command, or a test function."
        )
        examples.append(_make_example(ctx, q, a))

    if not callees:
        q = f"Is `{symbol}` a leaf function?"
        a = (
            f"`{symbol}` is a **leaf function**: it does not call any other symbols "
            f"in this graph. It is called by {len(callers)} symbol(s): "
            + ", ".join(f"`{c}`" for c in callers[:8])
            + "."
        )
        examples.append(_make_example(ctx, q, a))

    return examples


def gen_module_summary(graph: OrionGraph, module: str) -> list[dict]:
    declares = graph.declares(module)
    imports = graph.imports_of(module)
    if not declares and not imports:
        return []

    fns = [s for s in declares if graph.node_type(s) in ("function", "method")]
    classes = [s for s in declares if graph.node_type(s) == "class"]

    answer_parts = [f"Module `{module}` contains:"]
    if classes:
        answer_parts.append(f"  - {len(classes)} class(es): " + ", ".join(f"`{c}`" for c in classes[:8]))
    if fns:
        answer_parts.append(f"  - {len(fns)} function(s): " + ", ".join(f"`{f}`" for f in fns[:8]))
    if imports:
        answer_parts.append(f"  - Imports from: " + ", ".join(f"`{i}`" for i in imports[:6]))

    ctx = graph.subgraph_context(module)
    q = f"Summarise the structure of the `{module}` module."
    return [_make_example(ctx, q, "\n".join(answer_parts))]


GENERATORS = [
    gen_callers,
    gen_callees,
    gen_blast_radius,
    gen_leaf_or_root,
    gen_shortest_path,
]

MODULE_GENERATORS = [
    gen_module_summary,
]


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — LLM paraphrasing
# ─────────────────────────────────────────────────────────────────────────────

def _paraphrase_batch(examples: list[dict], n: int = 3) -> list[dict]:
    try:
        import anthropic
    except ImportError:
        print("anthropic package not found — skipping paraphrasing. pip install anthropic")
        return []

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set — skipping paraphrasing.")
        return []

    client = anthropic.Anthropic(api_key=api_key)
    new_examples = []
    sample = random.sample(examples, min(200, len(examples)))

    for ex in tqdm(sample, desc="Paraphrasing"):
        user_content = ex["messages"][1]["content"]
        orig_q = user_content.split("[QUESTION]\n", 1)[-1].strip()
        prompt = (
            f"Rewrite this developer question about code structure in {n} different ways. "
            f"Keep the same technical meaning. Output only the questions, one per line, no numbering.\n\n"
            f"Question: {orig_q}"
        )
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            rewrites = response.content[0].text.strip().split("\n")
            for rw in rewrites[:n]:
                rw = rw.strip()
                if rw and len(rw) > 10:
                    ctx = user_content.split("[QUESTION]\n", 1)[0].replace("[GRAPH CONTEXT]\n", "").strip()
                    new_examples.append(_make_example(ctx, rw, ex["messages"][-1]["content"]))
        except Exception as e:
            print(f"  paraphrase error: {e}")
            continue

    return new_examples


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — Dataset assembly and output
# ─────────────────────────────────────────────────────────────────────────────

def generate_dataset(graph: OrionGraph, paraphrase: bool = False) -> list[dict]:
    examples = []

    functions = graph.all_functions()
    modules = graph.all_modules()

    print(f"Graph has {len(graph.nodes)} nodes, {len(graph.edges)} edges")
    print(f"  Functions/methods: {len(functions)}")
    print(f"  Modules: {len(modules)}")

    for symbol in tqdm(functions, desc="Generating function QA"):
        for gen in GENERATORS:
            examples.extend(gen(graph, symbol))

    for module in tqdm(modules, desc="Generating module QA"):
        for gen in MODULE_GENERATORS:
            examples.extend(gen(graph, module))

    print(f"\nGenerated {len(examples)} base examples")
    random.shuffle(examples)

    if paraphrase:
        print("\nRunning paraphrase augmentation...")
        augmented = _paraphrase_batch(examples)
        examples.extend(augmented)
        print(f"After paraphrasing: {len(examples)} total examples")
        random.shuffle(examples)

    return examples


def validate_dataset(examples: list[dict]) -> None:
    """Fail early on malformed or duplicate SFT records."""
    if not examples:
        raise ValueError("No training examples were generated; check the graph export.")
    seen = set()
    for index, example in enumerate(examples, 1):
        messages = example.get("messages")
        if not isinstance(messages, list) or not messages:
            raise ValueError(f"Example {index} has no messages array")
        if messages[-1].get("role") != "assistant":
            raise ValueError(f"Example {index} must end with an assistant message")
        if any(not isinstance(m.get("content"), str) or not m["content"].strip() for m in messages):
            raise ValueError(f"Example {index} contains empty message content")
        key = tuple((m.get("role"), m.get("content")) for m in messages)
        seen.add(key)


def deduplicate_examples(examples: list[dict]) -> list[dict]:
    """Remove exact chat duplicates while preserving deterministic order."""
    unique = []
    seen = set()
    for example in examples:
        key = tuple((m.get("role"), m.get("content")) for m in example["messages"])
        if key not in seen:
            seen.add(key)
            unique.append(example)
    removed = len(examples) - len(unique)
    if removed:
        print(f"Removed {removed} duplicate example(s)")
    return unique


def save_dataset(examples: list[dict], output_path: str):
    examples = deduplicate_examples(examples)
    validate_dataset(examples)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(out, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    split = int(len(examples) * 0.9)
    train, val = examples[:split], examples[split:]

    train_path = out.with_name(out.stem + "_train.jsonl")
    val_path = out.with_name(out.stem + "_val.jsonl")

    with open(train_path, "w", encoding="utf-8") as f:
        for ex in train:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    with open(val_path, "w", encoding="utf-8") as f:
        for ex in val:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"\nSaved:")
    print(f"  Full dataset : {out}          ({len(examples)} examples)")
    print(f"  Train split  : {train_path}   ({len(train)} examples)")
    print(f"  Val split    : {val_path}     ({len(val)} examples)")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate fine-tuning dataset from Orion knowledge graph"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--repo",      help="Path to Python repo — graph built inline")
    source.add_argument("--graph",     help="Path to saved Orion graph JSON export")
    source.add_argument("--graph-dir", help="Directory of graph JSON exports (one per repo)")

    parser.add_argument("--output",     default="orion_dataset.jsonl", help="Output JSONL file")
    parser.add_argument("--paraphrase", action="store_true",           help="Use Claude API to paraphrase questions")
    args = parser.parse_args()

    all_examples = []

    if args.repo:
        print(f"Analyzing repo: {args.repo}")
        graph = _build_graph_from_repo(args.repo)
        all_examples = generate_dataset(graph, paraphrase=args.paraphrase)

    elif args.graph:
        print(f"Loading graph: {args.graph}")
        with open(args.graph, encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid graph export {args.graph}: {exc}") from exc
        graph = OrionGraph(data)
        all_examples = generate_dataset(graph, paraphrase=args.paraphrase)

    elif args.graph_dir:
        graph_dir = Path(args.graph_dir)
        graph_files = list(graph_dir.glob("*.json"))
        print(f"Found {len(graph_files)} graph file(s) in {graph_dir}")
        for gf in graph_files:
            print(f"\n-- Processing: {gf.name}")
            with open(gf, encoding="utf-8-sig") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError as exc:
                    print(f"  Skipping invalid graph export: {exc}")
                    continue
            graph = OrionGraph(data)
            all_examples.extend(generate_dataset(graph, paraphrase=False))
        if args.paraphrase:
            augmented = _paraphrase_batch(all_examples)
            all_examples.extend(augmented)
        random.shuffle(all_examples)

    save_dataset(all_examples, args.output)
    print("\nDone.")


if __name__ == "__main__":
    main()
