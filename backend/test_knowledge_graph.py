from __future__ import annotations

"""
Knowledge Graph smoke test.

Usage:
    python backend/test_knowledge_graph.py backend
    python backend/test_knowledge_graph.py /path/to/any/python/project
"""


import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.scanner.scanner import ProjectScanner
from app.scanner.knowledge_graph.query import KnowledgeGraphQuery


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_knowledge_graph.py <project_path>")
        sys.exit(1)

    project_path = Path(sys.argv[1]).resolve()
    print(f"Scanning: {project_path}\n")

    scanner = ProjectScanner()
    result, index = scanner.scan(project_path)

    query = KnowledgeGraphQuery(index.knowledge_graph)
    stats = query.stats()

    # ------------------------------------------------------------------
    # Overall stats
    # ------------------------------------------------------------------
    nt = stats["by_node_type"]
    et = stats["by_edge_type"]

    print("=" * 60)
    print("KNOWLEDGE GRAPH STATS")
    print("=" * 60)
    print(f"  Nodes          : {stats['nodes']}")
    print(f"    files        : {nt.get('file', 0)}")
    print(f"    modules      : {nt.get('module', 0)}")
    print(f"    classes      : {nt.get('class', 0)}")
    print(f"    functions    : {nt.get('function', 0)}")
    print(f"    methods      : {nt.get('method', 0)}")
    print(f"    variables    : {nt.get('variable', 0)}")
    print()
    print(f"  Edges          : {stats['edges']}")
    print(f"    declares     : {et.get('declares', 0)}")
    print(f"    imports      : {et.get('imports', 0)}")
    print(f"    calls        : {et.get('calls', 0)}")
    print()

    # ------------------------------------------------------------------
    # Spot-check: find a class with call edges and show its callees
    # ------------------------------------------------------------------
    print("=" * 60)
    print("SAMPLE: symbols with most outgoing call edges")
    print("=" * 60)

    from collections import Counter
    from app.scanner.knowledge_graph.models import EdgeType

    g = index.knowledge_graph
    call_out = Counter(
        edge.source
        for edge in g.edges
        if edge.type == EdgeType.CALLS
    )

    for node_id, count in call_out.most_common(5):
        node = g.get_node(node_id)
        if node is None:
            continue
        qn = node.qualified_name or node_id
        print(f"\n  {qn}  ({count} calls out)")
        callees = query.callees_of(qn)
        for c in callees[:6]:
            print(f"    -> {c.qualified_name}")
        if len(callees) > 6:
            print(f"    ... and {len(callees) - 6} more")

    # ------------------------------------------------------------------
    # Spot-check: callers_of — pick top 3 symbols by incoming call edges
    # ------------------------------------------------------------------
    call_in = Counter(
        edge.target
        for edge in g.edges
        if edge.type == EdgeType.CALLS
    )
    probe_names = [
        g.get_node(nid).qualified_name
        for nid, _ in call_in.most_common(3)
        if g.get_node(nid) is not None and g.get_node(nid).qualified_name
    ]

    print()
    print("=" * 60)
    print("SAMPLE: callers_of probe symbols")
    print("=" * 60)

    for probe in probe_names:
        # find by simple name suffix
        matches = [
            qn for qn in (
                node.qualified_name
                for node in g.nodes.values()
                if node.qualified_name
            )
            if qn.endswith(f".{probe}") or qn == probe
        ]
        for qn in matches[:1]:
            callers = query.callers_of(qn)
            print(f"\n  callers_of({qn})  [{len(callers)} total]")
            for c in callers[:6]:
                print(f"    <- {c.qualified_name}")
            if len(callers) > 6:
                print(f"    ... and {len(callers) - 6} more")

    # ------------------------------------------------------------------
    # Spot-check: impact analysis
    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    print("SAMPLE: impact_of probe symbol")
    print("=" * 60)

    for probe in probe_names:
        matches = [
            qn for qn in (
                node.qualified_name
                for node in g.nodes.values()
                if node.qualified_name
            )
            if qn.endswith(f".{probe}") or qn == probe
        ]
        for qn in matches[:1]:
            impact = query.impact_of(qn)
            print(f"\n  impact_of({qn})")
            print(f"    direct callers  : {impact['direct_count']}")
            print(f"    total affected  : {impact['total_count']}")
            print(f"    affected modules: {len(impact['affected_modules'])}")
            for m in impact["affected_modules"][:5]:
                print(f"      {m}")
            break
        else:
            continue
        break

    # ------------------------------------------------------------------
    # Spot-check: path_between
    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    print("SAMPLE: path_between two symbols")
    print("=" * 60)

    # Pick the two symbols with the most call edges as from/to
    if len(call_out) >= 2:
        top = call_out.most_common(2)
        n1 = g.get_node(top[0][0])
        n2 = g.get_node(top[1][0])
        if n1 and n2 and n1.qualified_name and n2.qualified_name:
            path = query.path_between(n1.qualified_name, n2.qualified_name)
            print(f"\n  {n1.qualified_name}")
            print(f"  -> {n2.qualified_name}")
            if path:
                print(f"  Path ({len(path)} hops):")
                for step in path:
                    print(f"    {step}")
            else:
                print("  No direct call path found.")

    print()


if __name__ == "__main__":
    main()