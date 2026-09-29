from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from app.agent.workflow import apply_proposal, create_proposal
from tests.eval.cases import EvalCase
from tests.eval.runner import EvalResult


def evaluate_agent_case(case: EvalCase) -> EvalResult:
    """
    Evaluate Orion's supervised agent proposal workflow.

    These cases intentionally exercise the real proposal creation/apply path
    against an isolated temporary repository.
    """
    if case.case_id == "agent-001":
        return _evaluate_create_proposal(case)

    if case.case_id == "agent-002":
        return _evaluate_apply_proposal(case)

    raise ValueError(f"Unsupported agent evaluation case: {case.case_id}")


def _evaluate_create_proposal(case: EvalCase) -> EvalResult:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / "sample.py"
        original = "def greet(name):\n    return f'Hello {name}'\n"
        target.write_text(original, encoding="utf-8")

        proposal = create_proposal(
            project_root=root,
            changes=[
                {
                    "path": "sample.py",
                    "old_content": original,
                    "new_content": "def greet(name):\n    return f'Hello, {name}!'\n",
                }
            ],
            rationale="Improve greeting punctuation.",
            validation="none",
            allow_test_modes=True,
        )

        checks = [
            proposal is not None,
            getattr(proposal, "status", None) == "proposed",
            len(getattr(proposal, "changes", [])) == 1,
            target.read_text(encoding="utf-8") == original,
        ]

        score = sum(checks) / len(checks)

        return EvalResult(
            case_id=case.case_id,
            category=case.category,
            passed=all(checks),
            score=score,
            details={
                "proposal_created": proposal is not None,
                "status": getattr(proposal, "status", None),
                "change_count": len(getattr(proposal, "changes", [])),
                "source_unchanged": target.read_text(encoding="utf-8") == original,
            },
        )


def _evaluate_apply_proposal(case: EvalCase) -> EvalResult:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / "sample.py"
        original = "def greet(name):\n    return f'Hello {name}'\n"
        updated = "def greet(name):\n    return f'Hello, {name}!'\n"

        target.write_text(original, encoding="utf-8")

        proposal = create_proposal(
            project_root=root,
            changes=[
                {
                    "path": "sample.py",
                    "old_content": original,
                    "new_content": updated,
                }
            ],
            rationale="Improve greeting punctuation.",
            validation="none",
            allow_test_modes=True,
        )

        result = apply_proposal(
            project_root=root,
            proposal_id=proposal.id,
            approved=True,
            validation_mode="none",
        )

        final_content = target.read_text(encoding="utf-8")

        checks = [
            result is not None,
            getattr(result, "status", None) == "applied",
            final_content == updated,
        ]

        score = sum(checks) / len(checks)

        return EvalResult(
            case_id=case.case_id,
            category=case.category,
            passed=all(checks),
            score=score,
            details={
                "apply_result": result is not None,
                "status": getattr(result, "status", None),
                "file_updated": final_content == updated,
            },
        )


if __name__ == "__main__":
    from tests.eval.cases import AGENT_PROPOSAL_CASES
    from tests.eval.runner import format_summary, summarize_results

    results = [
        evaluate_agent_case(case)
        for case in AGENT_PROPOSAL_CASES
    ]

    print()
    print(format_summary(summarize_results(results)))
    print()

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.case_id}: {result.score:.1%}")
        if not result.passed:
            print(f"       {result.details}")

    raise SystemExit(
        0 if all(result.passed for result in results) else 1
    )
