from __future__ import annotations

from pathlib import Path

from app.core.graph_state import scan_project
from tests.eval.cases import GRAPH_QA_CASES
from tests.eval.graph_adapter import evaluate_graph_case
from tests.eval.runner import summarize_results, format_summary


FIXTURE_REPO = Path(__file__).resolve().parent / "fixture_repo"


def main() -> int:
    """Scan the controlled fixture and evaluate Orion's graph behavior."""
    print(f"Scanning evaluation fixture: {FIXTURE_REPO}")

    state = scan_project(FIXTURE_REPO)

    print(
        f"Graph built: "
        f"{state.graph.node_count} nodes, "
        f"{state.graph.edge_count} edges"
    )

    results = [
        evaluate_graph_case(case, state)
        for case in GRAPH_QA_CASES
    ]

    print()
    print(format_summary(summarize_results(results)))
    print()

    for result in results:
        status = "PASS" if result.passed else "FAIL"

        print(
            f"[{status}] "
            f"{result.case_id}: "
            f"{result.score:.1%}"
        )

        if not result.passed:
            print(f"       {result.details}")

    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())