from __future__ import annotations

from tests.eval.agent_adapter import evaluate_agent_case
from tests.eval.cases import (
    AGENT_PROPOSAL_CASES,
    GRAPH_QA_CASES,
    SAFETY_CASES,
)
from tests.eval.graph_adapter import evaluate_graph_case
from tests.eval.runner import (
    EvalResult,
    format_summary,
    summarize_results,
)
from tests.eval.safety_adapter import evaluate_safety_case

from app.core.graph_state import scan_project

from pathlib import Path


FIXTURE_REPO = Path(__file__).resolve().parent / "fixture_repo"


def run_graph_evaluation() -> list[EvalResult]:
    state = scan_project(FIXTURE_REPO)

    return [
        evaluate_graph_case(case, state)
        for case in GRAPH_QA_CASES
    ]


def run_agent_evaluation() -> list[EvalResult]:
    return [
        evaluate_agent_case(case)
        for case in AGENT_PROPOSAL_CASES
    ]


def run_safety_evaluation() -> list[EvalResult]:
    return [
        evaluate_safety_case(case.case_id)
        for case in SAFETY_CASES
    ]


def main() -> int:
    print("Running Orion evaluation suite")
    print(f"Fixture repository: {FIXTURE_REPO}")

    results: list[EvalResult] = []

    print("\n[1/3] Graph QA")
    graph_results = run_graph_evaluation()
    results.extend(graph_results)

    print("\n[2/3] Agent Proposal")
    agent_results = run_agent_evaluation()
    results.extend(agent_results)

    print("\n[3/3] Safety")
    safety_results = run_safety_evaluation()
    results.extend(safety_results)

    summary = summarize_results(results)

    print()
    print(format_summary(summary))
    print()

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.case_id}: {result.score:.1%}")

        if not result.passed:
            print(f"       {result.details}")

    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())