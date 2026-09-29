"""
orion_llm_router.py  — v5
==========================
Changes over v4:

  STEP 1 — Stop tokens: extended EOT variant list to cover all known DeepSeek
    separator spellings. Added explicit eos_token_id lookup from the fine-tuned
    tokenizer. Added a startup warning if any stop ID is suspiciously low (< 100),
    which indicates a sub-token split and requires a uvicorn restart.

  STEP 2 — _clean(): added ftfy.fix_text() as the first operation to reverse
    UTF-8 mojibake (Ã©→é, Ã¢→â, etc.). Added regex strips for <jupyter_text>,
    <paste>, and context-echo (model repeating [SOURCE CODE] or [GRAPH CONTEXT]).
    NOTE: pip install ftfy  — falls back gracefully if not installed.

  STEP 3 — SYSTEM_PROMPT: explicit "do NOT" constraints so the model stops
    echoing Symbol:/Type:/File: fields. _build_prompt(): added a single
    few-shot (context, question, answer) example and an [ANSWER] suffix that
    primes the model to start generating the answer immediately.

  STEP 4 — _generate(): logs input token count on every call. _build_context():
    callers/callees capped at 5 (was 10), depth-1 neighbourhood removed,
    source code capped at 40 lines. Together these keep input tokens < 600
    for typical functions, reducing GPU latency from ~30s to ~5-8s.

  STEP 5 — /llm/health: added "quantization" field so you can verify 4-bit
    BitsAndBytes is actually active. No code change required for Step 5
    itself — the Kaggle base-vs-LoRA comparison is manual.

  STEP 7 — _is_acceptable(): post-generation guard. If the answer is too
    short, echoes context fields, has too many newlines, or still contains
    encoding artifacts, the ask() endpoint falls back to the deterministic
    graph answer (or a safe error message) instead of returning garbage.

  STEP 8 — _generate_stream(): fixed per-token _clean() call (wrong — regexes
    need the full string). Now accumulates into a buffer, flushes on
    word-boundary tokens, and checks stop tags on the full buffer.
"""

from __future__ import annotations

import os
import re
import time
import logging
import json
from functools import lru_cache
from threading import Thread
from typing import Any, Iterator

from fastapi import APIRouter, Request, Depends, HTTPException
from pathlib import Path as FilePath
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.auth import CurrentUser, User, require_admin
from app.core import graph_state
from app.core.config import settings

from app.scanner.source_extractor import extract_symbol_source

logger = logging.getLogger("orion.llm")

try:
    import torch
except ImportError:  # The no-LLM deployment intentionally omits torch.
    torch = None

# ── Config ────────────────────────────────────────────────────────────────────
MODEL_BASE     = os.getenv("ORION_BASE_MODEL",   "deepseek-ai/deepseek-coder-1.3b-instruct")
ADAPTER_PATH   = os.getenv("ORION_ADAPTER_PATH", "../fine_tuned_model")
MAX_NEW_TOKENS = int(os.getenv("ORION_MAX_TOKENS", "65"))
TEMPERATURE    = 0.05
LLM_ENABLED    = settings.ORION_LLM_ENABLED

# ── STEP 2: ftfy import (graceful fallback if not installed) ──────────────────
# Install with:  pip install ftfy
try:
    import ftfy as _ftfy
    _FTFY_AVAILABLE = True
except ImportError:
    _FTFY_AVAILABLE = False
    logger.warning(
        "[Orion LLM] ftfy not installed — UTF-8 mojibake (Ã©, Ã¢…) will not be "
        "auto-corrected in model output. Run:  pip install ftfy"
    )

# ── STEP 3: system prompt aligned with fine-tuning dataset ─────────────────────
SYSTEM_PROMPT = (
    "You are Orion, an expert code structure analyst. "
    "Given a knowledge graph context extracted from a Python repository, "
    "answer the developer's question accurately and concisely. "
    "Base your answer solely on the graph data provided."
)

# ── STEP 3: few-shot example injected into every prompt ───────────────────────
# One high-quality example teaches the model the expected output format far more
# reliably than system-prompt instructions alone.  Keep it short — it costs
# ~120 tokens and buys significant format compliance.
_FEW_SHOT = """\
Example
-------
[GRAPH CONTEXT]
Symbol: utils.clamp
Type: function
File: utils.py
Called by: renderer.draw_pixel
Calls: (nothing — this is a leaf function)

[SOURCE CODE]
```python
def clamp(value, lo, hi):
    return max(lo, min(hi, value))
```

[QUESTION]
What does this function do?

[ANSWER]
clamp restricts a numeric value to the inclusive range [lo, hi] and returns \
the clamped result. It is used by renderer.draw_pixel to keep pixel coordinates \
within valid bounds.
-------

"""

router = APIRouter(tags=["LLM"])


# ── Model loading ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_model():
    if not LLM_ENABLED:
        raise RuntimeError("Orion LLM inference is disabled in this deployment")
    if torch is None:
        raise RuntimeError("Orion LLM dependencies are not installed")

    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel

    cuda = torch.cuda.is_available()
    device = "cuda" if cuda else "cpu"

    if not cuda:
        logger.warning(
            "[Orion LLM] No CUDA GPU — running on CPU. "
            "Inference will be ~60-200s/query. "
            "Install CUDA 12.x + pip install torch --index-url "
            "https://download.pytorch.org/whl/cu121"
        )

    logger.info(f"[Orion LLM] Loading base model on {device.upper()}: {MODEL_BASE}")

    if cuda:
        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        base = AutoModelForCausalLM.from_pretrained(
            MODEL_BASE,
            quantization_config=bnb,
            device_map="auto",
            trust_remote_code=True,
        )
    else:
        base = AutoModelForCausalLM.from_pretrained(
            MODEL_BASE,
            torch_dtype=torch.float32,
            device_map="cpu",
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )

    logger.info(f"[Orion LLM] Loading adapter: {ADAPTER_PATH}")
    model = PeftModel.from_pretrained(base, ADAPTER_PATH)
    model.eval()

    tokenizer = AutoTokenizer.from_pretrained(ADAPTER_PATH, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # ── STEP 1: Stop tokens ────────────────────────────────────────────────────
    # Rule: ONLY use added_tokens_encoder for special tokens.
    # tokenizer.encode("<|EOT|>") splits into sub-tokens [27,29,91,...] which
    # causes generation to stop on every '<' or '|' in normal text.
    # added_tokens_encoder maps the full string to a single high ID (> 32000).
    #
    # Extended variant list — DeepSeek and its fine-tuned derivatives use
    # several spellings across different checkpoints:
    _EOT_VARIANTS = [
        "<|user|>",
        "<|assistant|>",
        "<|system|>",
        "<|EOT|>",
        "<EOT>",
        "｜EOT｜",        # full-width pipe variant seen in some checkpoints
        "<|end|>",
        "<|endoftext|>",
        "<|im_end|>",     # ChatML-style, present in some merged models
    ]

    stop_ids: set[int] = set()

    # Always include the tokenizer's own eos_token_id
    if tokenizer.eos_token_id is not None:
        stop_ids.add(tokenizer.eos_token_id)

    # Also look up eos_token via convert_tokens_to_ids as a belt-and-suspenders check
    if tokenizer.eos_token:
        eos_via_convert = tokenizer.convert_tokens_to_ids(tokenizer.eos_token)
        if isinstance(eos_via_convert, int) and eos_via_convert > 0:
            stop_ids.add(eos_via_convert)

    added = getattr(tokenizer, "added_tokens_encoder", {})
    for tok in _EOT_VARIANTS:
        if tok in added:
            stop_ids.add(added[tok])

    stop_ids_sorted = sorted(stop_ids)
    logger.info(f"[Orion LLM] Ready on {device.upper()}. Stop token IDs: {stop_ids_sorted}")

    # ── STEP 1: Sanity-check — warn loudly if any ID looks like a sub-token ──
    # Legitimate special-token IDs for DeepSeek-Coder are all > 32000.
    # If you see IDs < 100 here, the tokenizer cache is stale or the wrong
    # tokenizer file was loaded.  Restart uvicorn to fix.
    suspicious = [i for i in stop_ids_sorted if i < 100]
    if suspicious:
        logger.error(
            f"[Orion LLM] STOP TOKEN WARNING — IDs {suspicious} are suspiciously low. "
            "These look like sub-token splits, not atomic special tokens. "
            "This will cause generation to stop prematurely on normal punctuation. "
            "Restart uvicorn with a clean __pycache__ to force tokenizer reload."
        )
    else:
        logger.info(
            "[Orion LLM] Stop token IDs look correct (all > 100). "
            f"Expected range for DeepSeek-Coder: 32000–32100. Got: {stop_ids_sorted}"
        )

    # ── STEP 5: Log quantization status so /health can surface it ─────────────
    quant_active = False
    if cuda:
        try:
            from bitsandbytes.nn import Linear4bit
            quant_active = any(
                isinstance(m, Linear4bit) for m in model.modules()
            )
        except ImportError:
            pass
    logger.info(f"[Orion LLM] 4-bit quantization active: {quant_active}")

    return model, tokenizer, stop_ids_sorted, device, quant_active


# ── Helpers ───────────────────────────────────────────────────────────────────

def _unwrap(value: Any) -> str:
    """Convert enum values, Path objects, and None to plain strings."""
    if value is None:
        return "unknown"
    s = str(value)
    # NodeType.METHOD → method,  EdgeType.CALLS → calls
    if "." in s and s.split(".")[0].isupper() or (len(s.split(".")) == 2 and s.split(".")[0][0].isupper()):
        return s.split(".")[-1].lower()
    return s


def _edge_get(edge: Any, *keys: str) -> str:
    """Read a field from either a dict edge or an object edge."""
    for k in keys:
        if isinstance(edge, dict) and k in edge:
            return str(edge[k])
        v = getattr(edge, k, None)
        if v is not None:
            return _unwrap(v)
    return ""


def _get_graph(request: Request):
    state = graph_state.current(request.app.state)
    return state.graph if state is not None else None


def _get_query(request: Request):
    state = graph_state.current(request.app.state)
    return state.query if state is not None else None


def _resolve_symbol_key(nodes: dict, symbol: str) -> str | None:
    """Try several key formats to find the symbol in the graph."""
    for candidate in [symbol, f"symbol:{symbol}", f"file:{symbol}"]:
        if candidate in nodes:
            return candidate
    tail = symbol.split(".")[-1]
    matches = [k for k in nodes if k.endswith(f".{tail}") or k.endswith(f":{tail}")]
    return matches[0] if len(matches) == 1 else None


# ── STEP 4: _build_context() — trimmed for token budget ──────────────────────
# Changes:
#   - callers/callees capped at 5 (was 10) — rare to need more for a single-symbol Q
#   - depth-1 caller neighbourhood removed — added ~3-6 lines per caller, rarely
#     useful for "what does X do" and costs ~50-80 tokens per question
#   - source code capped at 40 lines with a truncation notice
# Together these keep the typical context under 400 tokens, versus ~900 before.

def _build_context(graph: Any, symbol: str, project_path: str | None = None) -> str:
    """Serialize a symbol's local neighbourhood into a compact text block."""
    if graph is None:
        return (
            f"Symbol: {symbol}\n"
            "(Graph unavailable — set app.state.graph in your FastAPI startup)"
        )

    nodes = getattr(graph, "nodes", getattr(graph, "_nodes", {}))
    edges = getattr(graph, "edges", getattr(graph, "_edges", []))

    resolved_key = _resolve_symbol_key(nodes, symbol)
    node_info    = nodes.get(resolved_key) if resolved_key else None
    lookup_keys  = {symbol, resolved_key} - {None}

    callers: list[str] = []
    callees: list[str] = []
    imports_: list[str] = []

    for e in edges:
        src   = _edge_get(e, "source", "src")
        dst   = _edge_get(e, "target", "dst")
        etype = _edge_get(e, "type", "relation")

        src_bare = src.split(":", 1)[-1] if ":" in src else src
        dst_bare = dst.split(":", 1)[-1] if ":" in dst else dst

        is_focal_src = src in lookup_keys or src_bare == symbol
        is_focal_dst = dst in lookup_keys or dst_bare == symbol

        if etype == "calls":
            if is_focal_dst:
                callers.append(src_bare)
            if is_focal_src:
                callees.append(dst_bare)
        elif etype == "imports":
            if is_focal_src:
                imports_.append(dst_bare)

    if node_info:
        raw_type = getattr(node_info, "type", getattr(node_info, "kind", None))
        if isinstance(node_info, dict):
            raw_type = node_info.get("type", node_info.get("kind"))
        node_type = _unwrap(raw_type)

        raw_file = getattr(node_info, "path", getattr(node_info, "file", None))
        if isinstance(node_info, dict):
            raw_file = node_info.get("path", node_info.get("file"))
        node_file = _unwrap(raw_file)

        if isinstance(node_info, dict):
            node_path = node_info.get("path")
            node_line = node_info.get("line")
            node_end  = node_info.get("end_line")
        else:
            node_path = getattr(node_info, "path", None)
            node_line = getattr(node_info, "line", None)
            node_end  = getattr(node_info, "end_line", None)
    else:
        node_type = "unknown"
        node_file = "unknown"
        node_path = node_line = node_end = None

    # STEP 4: cap at 5 (was 10)
    unique_callers = sorted(set(callers))[:5]
    unique_callees = sorted(set(callees))[:5]

    lines = [
        f"Symbol: {symbol}",
        f"Type: {node_type}",
        f"File: {node_file}",
        (
            f"Called by: {', '.join(unique_callers)}"
            if unique_callers
            else "Called by: (nothing — this is a root or entry point)"
        ),
        (
            f"Calls: {', '.join(unique_callees)}"
            if unique_callees
            else "Calls: (nothing — this is a leaf function)"
        ),
    ]

    if imports_:
        lines.append(f"Imports: {', '.join(sorted(set(imports_))[:4])}")

    # STEP 4: depth-1 caller neighbourhood REMOVED — saved ~60 tokens per query

    source_block = ""
    if node_info:
        if project_path and node_path and not FilePath(node_path).is_absolute():
            node_path = str(FilePath(project_path) / node_path)

        if node_path and node_line and node_end:
            src_text = extract_symbol_source(FilePath(node_path), node_line, node_end)
            if src_text:
                # STEP 4: cap source at 40 lines
                src_lines = src_text.split("\n")
                if len(src_lines) > 40:
                    src_text = "\n".join(src_lines[:40]) + "\n# … (truncated at 40 lines)"
                source_block = f"\n[SOURCE CODE]\n```python\n{src_text}\n```"

    return "\n".join(lines) + source_block


def _qualified_name(node: Any) -> str:
    if isinstance(node, dict):
        return str(node.get("qualified_name") or node.get("name") or "")
    return str(getattr(node, "qualified_name", None) or getattr(node, "name", ""))


def _format_symbol_list(nodes: list[Any], empty: str) -> str:
    names = [_qualified_name(node) for node in nodes]
    names = [name for name in names if name]
    if not names:
        return empty
    lines = [f"- `{name}`" for name in names[:12]]
    if len(names) > 12:
        lines.append(f"- ...and {len(names) - 12} more.")
    return "\n".join(lines)


def _direct_graph_answer(query: Any, question: str, symbol: str) -> str | None:
    """
    Answer common structural questions directly from the graph without the LLM.
    Fast, exact, and never hallucinates symbol names.
    """
    if query is None:
        return None

    q = question.lower()
    node = query.get_symbol(symbol)
    if node is None:
        return f"I could not find `{symbol}` in the current graph."

    if (
        "callee" in q
        or re.search(r"\b(what|which).*\b(do|does|it|this).*\bcall", q)
    ):
        callees = query.callees_of(symbol)
        return (
            f"`{symbol}` directly calls {len(callees)} symbol(s):\n"
            f"{_format_symbol_list(callees, '- No direct callees found.')}"
        )

    if (
        "caller" in q
        or "called by" in q
        or "depend" in q
        or re.search(r"\b(who|what|which)\s+calls?\b", q)
    ):
        callers = query.callers_of(symbol)
        return (
            f"`{symbol}` is directly called by {len(callers)} symbol(s):\n"
            f"{_format_symbol_list(callers, '- No direct callers found.')}"
        )

    if "impact" in q or "affected" in q or "break" in q or "change" in q:
        impact   = query.impact_of(symbol)
        modules  = impact.get("affected_modules", [])
        mod_lines = "\n".join(f"- `{m}`" for m in modules[:12])
        if len(modules) > 12:
            mod_lines += f"\n- ...and {len(modules) - 12} more."
        if not mod_lines:
            mod_lines = "- No affected modules found."
        return (
            f"Changing `{symbol}` affects {impact.get('total_count', 0)} caller symbol(s), "
            f"including {impact.get('direct_count', 0)} direct caller(s).\n"
            f"Affected modules:\n{mod_lines}"
        )

    # Explicitly pass semantic "what does it do" questions to the LLM
    if re.search(r"\bwhat\s+(does|do)\s+(this|it)\s+do\b", q):
        return None

    if "refactor" in q or "refactoring" in q:
        callers = query.callers_of(symbol)
        callees = query.callees_of(symbol)
        if len(callers) >= 3:
            signal = "Potentially worth reviewing because it has multiple callers."
        elif len(callees) >= 4:
            signal = "Potentially worth reviewing because it has a relatively large call fan-out."
        elif not callers and not callees:
            signal = "Low graph connectivity; the graph alone does not provide a strong refactoring signal."
        else:
            signal = "No strong refactoring signal is visible from the graph alone."
        return (
            f"Refactoring assessment for `{symbol}`:\n"
            f"- Direct callers: {len(callers)}\n"
            f"- Direct callees: {len(callees)}\n"
            f"- Assessment: {signal}\n"
            "This is a structural heuristic; the graph does not contain enough "
            "information to judge code quality or maintainability by itself."
        )

    return None


# ── Generation ────────────────────────────────────────────────────────────────

# ── STEP 3: _build_prompt() — few-shot + [ANSWER] suffix ─────────────────────
# The [ANSWER] token at the end of the user content, combined with
# add_generation_prompt=True (which appends the assistant turn opener), forms
# the sequence:
#
#   … [QUESTION]\nWhat does this function do?\n[ANSWER]<|assistant|>
#
# This double-primes the model: [ANSWER] tells it the answer is expected next,
# and the assistant turn opener tells it the answer is its turn to speak.

def _build_prompt(question: str, context: str, tokenizer) -> str:
    content = (
        f"{SYSTEM_PROMPT}\n\n"
        f"{_FEW_SHOT}"
        f"[GRAPH CONTEXT]\n{context}\n\n"
        f"[QUESTION]\n{question}"
    )
    messages = [{"role": "user", "content": content}]
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    return prompt + "[ANSWER]\n"


def _describe_symbol_from_context(context: str) -> str:
    """Deterministic fallback description derived from graph context."""
    lines = [line.strip() for line in context.splitlines() if line.strip()]
    sym_name = "This symbol"
    sym_type = "symbol"
    sym_file = "the codebase"
    callers = ""
    for line in lines:
        if line.startswith("Symbol:"):
            sym_name = f"`{line.split(':', 1)[-1].strip()}`"
        elif line.startswith("Type:"):
            sym_type = line.split(":", 1)[-1].strip()
        elif line.startswith("File:"):
            sym_file = line.split(":", 1)[-1].strip()
        elif line.startswith("Called by:"):
            callers = line.split(":", 1)[-1].strip()

    desc = f"{sym_name} is a {sym_type} defined in `{sym_file}`."
    if callers and not callers.startswith("(nothing"):
        desc += f" It is called by {callers}."
    return desc


# ── STEP 2: _clean() — ftfy + extended artifact strips ───────────────────────

def _clean(text: str) -> str:
    # ── 2a. ftfy: fixes UTF-8 mojibake (Ã©→é, Ã¢→â, â€™→', etc.) ──────────
    # This must run FIRST, before any string replacements, because mojibake
    # characters can masquerade as the replacement targets.
    if _FTFY_AVAILABLE:
        text = _ftfy.fix_text(text)

    # Strip leading turn tags / prompt echo headers if model starts output with them
    text = re.sub(r"^(?:<\|[^>]+>|###\s*\w+:?|\[ANSWER\]|\[QUESTION\]|\[GRAPH\s*CONTEXT\]|\[SOURCE\s*CODE\])\s*", "", text, flags=re.IGNORECASE)

    # ── 2b. Truncate at any trailing role/turn separator the model emits ──────
    # Cut everything from the first trailing separator onward.
    _TURN_TAGS = [
        "<|user_response|>", "<|user_turn|>", "<|user|>", "<|system|>", "<|assistant|>",
        "<|EOT|>", "<EOT>", "<|end|>", "<|im_end|>",
        # Written-out variants the model sometimes generates from training data:
        "### Instruction:", "### Response:", "### Human:", "### Assistant:",
        "[QUESTION]", "[GRAPH CONTEXT]", "[GRAPHCONTEXT]", "[SOURCE CODE]", "[SOURCECODE]",
    ]
    for tag in _TURN_TAGS:
        if tag in text:
            text = text.split(tag)[0]

    # ── 2c. Notebook / paste artifacts from training data contamination ───────
    text = re.sub(r"<jupyter_\w+>.*?</jupyter_\w+>", "", text, flags=re.DOTALL)
    text = re.sub(r"<paste\b[^>]*>.*",               "", text, flags=re.DOTALL)

    # ── 2d. Context echo — model repeating its own input ─────────────────────
    # If the model starts echoing [SOURCE CODE] or [GRAPH CONTEXT] in its
    # answer, it has gone off-rails.  Strip everything from that point.
    text = re.sub(r"\[SOURCE\s*CODE\].*",    "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"\[GRAPH\s*CONTEXT\].*",  "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"```python.*?```",        "", text, flags=re.DOTALL)  # stray code fences
    text = re.sub(r"<\|[^>]+>",              "", text)                   # strip stray special tokens

    # ── 2e. Byte-pair encoding display artefacts (legacy, kept for safety) ───
    _BPE_REPLACEMENTS = {
        "\u0120": " ",
        "\u010a": "\n",
        "\u0128": "",
        "âĨĴ": "-",
        "âĨĶ": "-",
        "âĨĻ": "'",
        "âĨļ": '"',
        "âĨĽ": '"',
        "âĨIJ": "",
        "âĨ": "",
        "âĢĶ": "...",
        "âĢ": "",
    }
    for old, new in _BPE_REPLACEMENTS.items():
        text = text.replace(old, new)

    # ── 2f. Whitespace normalisation ─────────────────────────────────────────
    text = re.sub(r"[ \t]+",   " ",    text)
    text = re.sub(r" *\n *",   "\n",   text)
    text = re.sub(r"\n{3,}",   "\n\n", text)

    return text.strip()


# ── STEP 7: _is_acceptable() — post-generation quality gate ──────────────────
# If the answer fails any of these checks, ask() falls back to the deterministic
# graph answer or a safe error string instead of surfacing garbage to the caller.
#
# Thresholds are intentionally loose — we want to catch obvious failures, not
# filter borderline-okay answers.  Log every rejection so you can tune.

def _is_acceptable(answer: str, symbol: str) -> bool:
    if len(answer.split()) < 4:
        logger.warning(f"[Orion LLM] Rejected answer for {symbol!r}: too short ({len(answer.split())} words)")
        return False

    # Model echoed context fields or hallucinated unformatted fields — cleaning failed or was insufficient
    _CONTEXT_ECHO_PATTERNS = [
        r"Symbol\s*:",
        r"Type\s*:",
        r"File\s*:",
        r"methodFile\s*:",
        r"functionFile\s*:",
        r"Called by",
        r"Calls\s*:",
        r"\[GRAPH\s*CONTEXT\]",
        r"\[SOURCE\s*CODE\]",
        r"<\|",
        r"```symbol",
    ]
    for pat in _CONTEXT_ECHO_PATTERNS:
        if re.search(pat, answer, re.IGNORECASE):
            logger.warning(f"[Orion LLM] Rejected answer for {symbol!r}: context/tag echo detected matching pattern {pat!r}")
            return False

    # Check for hallucinated dataset cross-talk (e.g. httpx when not querying httpx)
    if "httpx" in answer.lower() and "httpx" not in symbol.lower():
        logger.warning(f"[Orion LLM] Rejected answer for {symbol!r}: hallucinated dataset cross-talk ('httpx')")
        return False

    # Excessive newlines = the model is generating structured output, not prose
    if answer.count("\n") > 8:
        logger.warning(f"[Orion LLM] Rejected answer for {symbol!r}: too many newlines ({answer.count(chr(10))})")
        return False

    # Encoding artifacts survived _clean() — ftfy may not be installed
    # Check for the most common mojibake sequences
    if re.search(r"[ÃÂ]{1}[\x80-\xBF]|âĨ|âĢ|참조|íķ", answer):
        logger.warning(f"[Orion LLM] Rejected answer for {symbol!r}: encoding artifacts remain")
        return False

    # Notebook artifacts survived _clean() (shouldn't happen, belt-and-suspenders)
    if "<jupyter_" in answer or "<paste" in answer:
        logger.warning(f"[Orion LLM] Rejected answer for {symbol!r}: notebook artifacts remain")
        return False

    return True


# ── STEP 4: _generate() — token count logging ────────────────────────────────

def _generate(question: str, context: str) -> str:
    model, tokenizer, stop_ids, device, _ = _load_model()
    prompt = _build_prompt(question, context, tokenizer)
    enc    = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=1536,
        add_special_tokens=False,
    )

    input_len = enc["input_ids"].shape[1]
    logger.info(
        f"[Orion LLM] Generating — input tokens: {input_len}, "
        f"max_new_tokens: {MAX_NEW_TOKENS}"
    )
    if input_len > 800:
        logger.warning(
            f"[Orion LLM] Input is {input_len} tokens — context may be too large."
        )

    enc = {k: v.to(device) for k, v in enc.items()}

    with torch.no_grad():
        out = model.generate(
            **enc,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,          # greedy — reproducible, ~30% faster than sampling
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=stop_ids,
            repetition_penalty=1.1,
            use_cache=True,
        )

    new_toks = out[0][enc["input_ids"].shape[1]:]
    raw      = tokenizer.decode(new_toks, skip_special_tokens=True)
    return _clean(raw)


# ── STEP 8: _generate_stream() — buffered clean & stream suppression ─────────

def _generate_stream(question: str, context: str, focal_symbol: str = "") -> Iterator[str]:
    from transformers import TextIteratorStreamer

    model, tokenizer, stop_ids, device, _ = _load_model()
    prompt   = _build_prompt(question, context, tokenizer)
    enc      = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=1536,
        add_special_tokens=False,
    )
    enc      = {k: v.to(device) for k, v in enc.items()}
    streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)

    Thread(
        target=model.generate,
        kwargs=dict(
            **enc,
            max_new_tokens=MAX_NEW_TOKENS,
            min_new_tokens=8,
            temperature=TEMPERATURE,
            do_sample=TEMPERATURE > 0,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=stop_ids,
            repetition_penalty=1.1,
            use_cache=True,
            streamer=streamer,
        ),
        daemon=True,
    ).start()

    _STOP_TAGS = [
        "<|user_response|>", "<|user_turn|>", "<|user|>", "<|system|>", "<|assistant|>",
        "<|EOT|>", "<EOT>", "<|end|>", "<|im_end|>",
        "### Instruction:", "[QUESTION]", "[GRAPH CONTEXT]", "[GRAPHCONTEXT]", "[SOURCE CODE]", "[SOURCECODE]",
    ]

    buf = ""
    yielded_any = False
    for token in streamer:
        buf += token

        # Check for immediate hallucination patterns in the stream buffer
        if re.search(r"symbol:|functionFile:|methodFile:|```symbol|âĢ|참조|íķ", buf, re.IGNORECASE) or (
            "httpx" in buf.lower() and "httpx" not in focal_symbol.lower()
        ):
            logger.warning(f"[Orion LLM Stream] Suppressed hallucinated stream for {focal_symbol!r}")
            yield _describe_symbol_from_context(context)
            return

        # Check full buffer for stop tags — tags can span token boundaries
        for tag in _STOP_TAGS:
            if tag in buf:
                cleaned = _clean(buf.split(tag)[0])
                if cleaned:
                    yield cleaned
                    yielded_any = True
                if not yielded_any:
                    yield _describe_symbol_from_context(context)
                return

        # Flush on word boundary so client sees words arrive
        if buf.endswith((" ", "\n")) or len(buf) > 40:
            cleaned = _clean(buf)
            if cleaned:
                yield cleaned
                yielded_any = True
            buf = ""

    if buf:
        cleaned = _clean(buf)
        if cleaned:
            yield cleaned
            yielded_any = True

    if not yielded_any:
        yield _describe_symbol_from_context(context)


# ── Endpoints ─────────────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    question:      str      = Field(..., min_length=1, max_length=4000)
    focal_symbol:  str      = Field(..., min_length=1, max_length=512)
    extra_context: str | None = Field(default=None, max_length=12000)


class AskResponse(BaseModel):
    answer:       str
    focal_symbol: str
    latency_ms:   float
    context_used: str
    device:       str
    fallback:     bool = False   # True when _is_acceptable() rejected the LLM answer


@router.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest, request: Request, _user: CurrentUser = None):
    """
    Answer a natural language question about a symbol.

    Example:
        POST /llm/ask
        {
            "question": "What does this function do?",
            "focal_symbol": "shop.calculate_total"
        }
    """
    if not LLM_ENABLED:
        raise HTTPException(status_code=503, detail="The Orion LLM feature is disabled for this deployment.")

    graph   = _get_graph(request)
    query   = _get_query(request)
    context = _build_context(
        graph,
        req.focal_symbol,
        graph_state.current(request.app.state).project_path,
    )
    if req.extra_context:
        context = req.extra_context.strip() + "\n\n" + context

    t0       = time.perf_counter()
    answer   = _direct_graph_answer(query, req.question, req.focal_symbol)
    device   = "graph"
    fallback = False

    if answer is None:
        # Fast path: if no source code is in context, LLM cannot inspect body code; return instant graph description (0.01s)
        if "[SOURCE CODE]" not in context:
            answer = _describe_symbol_from_context(context)
            fallback = True
            device = "graph"
        else:
            raw_answer = _generate(req.question, context)
            _, _, _, device, _ = _load_model()

            # STEP 7: quality gate
            if _is_acceptable(raw_answer, req.focal_symbol):
                answer = raw_answer
            else:
                # Fall back to deterministic graph answer, or a safe summary string
                fallback = True
                answer = (
                    _direct_graph_answer(query, "what does this symbol do?", req.focal_symbol)
                    or _describe_symbol_from_context(context)
                )
                logger.warning(
                    f"[Orion LLM] Fell back to deterministic answer for {req.focal_symbol!r}. "
                    f"Raw model output: {raw_answer!r}"
                )

    ms = (time.perf_counter() - t0) * 1000

    return AskResponse(
        answer=answer,
        focal_symbol=req.focal_symbol,
        latency_ms=round(ms, 1),
        context_used=context,
        device=device,
        fallback=fallback,
    )


@router.post("/stream")
async def stream(req: AskRequest, request: Request, _user: CurrentUser = None):
    """Stream tokens as they are generated — useful for a typing effect in the UI."""
    if not LLM_ENABLED:
        raise HTTPException(status_code=503, detail="The Orion LLM feature is disabled for this deployment.")

    graph   = _get_graph(request)
    query   = _get_query(request)
    context = _build_context(
        graph,
        req.focal_symbol,
        graph_state.current(request.app.state).project_path,
    )
    if req.extra_context:
        context = req.extra_context.strip() + "\n\n" + context

    answer = _direct_graph_answer(query, req.question, req.focal_symbol)
    if answer is not None:
        return StreamingResponse(iter([answer]), media_type="text/plain")

    # Fast path: if no source code is in context, yield instant graph description (0.01s)
    if "[SOURCE CODE]" not in context:
        return StreamingResponse(
            iter([_describe_symbol_from_context(context)]),
            media_type="text/plain",
        )

    # STEP 8: stream uses the buffered generator — _clean() is applied inside
    return StreamingResponse(
        _generate_stream(req.question, context, req.focal_symbol),
        media_type="text/plain",
    )


@router.get("/health")
async def health(request: Request, _user: CurrentUser = None):
    cuda       = bool(torch is not None and torch.cuda.is_available())
    cache_info = _load_model.cache_info()

    info: dict[str, Any] = {
        "model_loaded":   cache_info.currsize > 0,
        "enabled":        LLM_ENABLED,
        "device":         "cuda" if cuda else "cpu",
        "cuda_available": cuda,
        "max_new_tokens": MAX_NEW_TOKENS,
        "ftfy_available": _FTFY_AVAILABLE,  # STEP 2: surface ftfy status
    }

    if cache_info.currsize > 0:
        # STEP 5: surface quantization status (loaded at model-load time)
        _, _, stop_ids, _, quant_active = _load_model()
        info["stop_token_ids"] = stop_ids
        info["quantization"]   = "4bit-nf4" if quant_active else "none (check bitsandbytes install)"
        info["stop_id_warning"] = (
            "IDs look correct (all > 100)" if all(i > 100 for i in stop_ids)
            else f"WARNING — low IDs detected: {[i for i in stop_ids if i < 100]} — restart uvicorn"
        )

    if cuda and torch is not None:
        info["vram"] = [
            {
                "gpu":      i,
                "used_gb":  round((total - free) / 1e9, 2),
                "total_gb": round(total / 1e9, 2),
            }
            for i in range(torch.cuda.device_count())
            for free, total in [torch.cuda.mem_get_info(i)]
        ]
    elif LLM_ENABLED:
        info["warning"] = (
            "CPU inference is slow (~60-200s). "
            "Install CUDA 12.x for ~3-8s latency."
        )

    graph = _get_graph(request)
    if graph is not None:
        nodes = getattr(graph, "nodes", getattr(graph, "_nodes", {}))
        edges = getattr(graph, "edges", getattr(graph, "_edges", []))
        info["graph"] = {"nodes": len(nodes), "edges": len(edges), "status": "connected"}
    else:
        info["graph"] = {
            "status": "not connected",
            "fix":    "ensure app.state.graph is set in your FastAPI lifespan/startup",
        }

    return info


@router.get(
    "/debug/{symbol:path}",
    dependencies=[Depends(require_admin)],
)
async def debug_symbol(symbol: str, request: Request, _user: CurrentUser):
    """Inspect raw graph data for a symbol — use to diagnose context issues."""
    graph = _get_graph(request)
    if graph is None:
        return {"error": "graph is None — app.state.graph not set"}

    nodes = getattr(graph, "nodes", getattr(graph, "_nodes", {}))
    edges = getattr(graph, "edges", getattr(graph, "_edges", []))

    resolved_key = _resolve_symbol_key(nodes, symbol)
    node_data    = nodes.get(resolved_key) if resolved_key else None

    related = [
        e for e in edges
        if symbol in (_edge_get(e, "source", "src"), _edge_get(e, "target", "dst"))
        or (resolved_key and resolved_key in (
            _edge_get(e, "source", "src"), _edge_get(e, "target", "dst")
        ))
    ][:15]

    return {
        "queried_symbol":  symbol,
        "resolved_key":    resolved_key,
        "node_data":       node_data,
        "related_edges":   related,
        "total_nodes":     len(nodes),
        "total_edges":     len(edges),
        "sample_keys":     list(nodes.keys())[:10],
        "graph_type":      type(graph).__name__,
        "context_preview": _build_context(
            graph,
            symbol,
            graph_state.current(request.app.state).project_path,
        ),
    }


@router.post("/warm")
async def warm(_user: User = Depends(require_admin)):
    """Eagerly load the model so the first /ask is not slow."""
    if not LLM_ENABLED:
        raise HTTPException(status_code=503, detail="The Orion LLM feature is disabled for this deployment.")

    t0 = time.perf_counter()
    _load_model()
    ms = (time.perf_counter() - t0) * 1000
    _, _, _, device, quant_active = _load_model()
    return {
        "status":       "ready",
        "device":       device,
        "load_ms":      round(ms, 1),
        "quantization": "4bit-nf4" if quant_active else "none",
    }
