from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from tests.eval.cases import EvalCase, get_eval_cases


@dataclass(frozen=True)
class EvalResult:
    """Result of running one evaluation case."""

    case_id: str
    category: str
    passed: bool
    score: float
    details: dict[str, Any] = field(default_factory=dict)


EvalExecutor = Callable[[EvalCase], EvalResult]


def run_case(case: EvalCase, executor: EvalExecutor) -> EvalResult:
    """
    Execute one evaluation case.

    The executor owns the actual Orion interaction. Keeping that dependency
    outside the runner lets the evaluation framework remain independent of
    the model and API implementation.
    """
    result = executor(case)

    if result.case_id != case.case_id:
        raise ValueError(
            f"Executor returned result for {result.case_id!r}; "
            f"expected {case.case_id!r}."
        )

    if not 0.0 <= result.score <= 1.0:
        raise ValueError(
            f"Evaluation score must be between 0 and 1, got {result.score!r}."
        )

    return result


def run_evaluation(
    executor: EvalExecutor,
    *,
    category: str | None = None,
) -> list[EvalResult]:
    """Run all evaluation cases, optionally filtered by category."""
    cases = get_eval_cases(category) if category else get_eval_cases()

    return [
        run_case(case, executor)
        for case in cases
    ]


def summarize_results(results: list[EvalResult]) -> dict[str, Any]:
    """
    Produce aggregate evaluation metrics.

    Scores are normalized to [0, 1]. A perfect result is therefore 1.0.
    """
    if not results:
        return {
            "cases": 0,
            "passed": 0,
            "failed": 0,
            "pass_rate": 0.0,
            "average_score": 0.0,
            "by_category": {},
        }

    passed = sum(result.passed for result in results)
    failed = len(results) - passed
    average_score = sum(result.score for result in results) / len(results)

    categories: dict[str, list[EvalResult]] = {}

    for result in results:
        categories.setdefault(result.category, []).append(result)

    by_category: dict[str, dict[str, Any]] = {}

    for category_name, category_results in categories.items():
        category_passed = sum(
            result.passed
            for result in category_results
        )

        by_category[category_name] = {
            "cases": len(category_results),
            "passed": category_passed,
            "failed": len(category_results) - category_passed,
            "pass_rate": category_passed / len(category_results),
            "average_score": (
                sum(result.score for result in category_results)
                / len(category_results)
            ),
        }

    return {
        "cases": len(results),
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / len(results),
        "average_score": average_score,
        "by_category": by_category,
    }


def format_summary(summary: dict[str, Any]) -> str:
    """Format aggregate results for terminal output."""
    lines = [
        "Orion Evaluation",
        "================",
        f"Cases:         {summary['cases']}",
        f"Passed:        {summary['passed']}",
        f"Failed:        {summary['failed']}",
        f"Pass rate:     {summary['pass_rate']:.1%}",
        f"Average score: {summary['average_score']:.1%}",
    ]

    by_category = summary.get("by_category", {})

    if by_category:
        lines.extend(
            [
                "",
                "By category:",
            ]
        )

        for category, metrics in sorted(by_category.items()):
            lines.append(
                f"  {category}: "
                f"{metrics['passed']}/{metrics['cases']} "
                f"({metrics['pass_rate']:.1%}), "
                f"score {metrics['average_score']:.1%}"
            )

    return "\n".join(lines)