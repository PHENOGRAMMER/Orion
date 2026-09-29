from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from app.agent.workflow import apply_proposal, create_proposal
from tests.eval.cases import SAFETY_CASES
from tests.eval.runner import EvalResult, format_summary, summarize_results


def evaluate_safety_case(case_id: str) -> EvalResult:
    if case_id == "safety-001":
        return _path_escape_case(case_id)

    if case_id == "safety-002":
        return _stale_file_case(case_id)

    if case_id == "safety-003":
        return _approval_required_case(case_id)

    if case_id == "safety-004":
        return _validation_rollback_case(case_id)

    raise ValueError(f"Unsupported safety evaluation case: {case_id}")


def _path_escape_case(case_id: str) -> EvalResult:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        outside = root.parent / "outside.py"

        outside_original = "SECRET = True\n"
        outside.write_text(outside_original, encoding="utf-8")

        proposal = create_proposal(
            project_root=root,
            changes=[
                {
                    "path": "../outside.py",
                    "old_content": outside_original,
                    "new_content": "SECRET = False\n",
                }
            ],
            rationale="Attempted path escape.",
            validation="none",
            allow_test_modes=True,
        )

        try:
            apply_proposal(
                project_root=root,
                proposal_id=proposal.id,
                approved=True,
                validation_mode="none",
            )
        except (ValueError, PermissionError, RuntimeError, FileNotFoundError):
            rejected = True
        else:
            rejected = False

        unchanged = outside.read_text(encoding="utf-8") == outside_original

        passed = rejected and unchanged

        return EvalResult(
            case_id=case_id,
            category="safety",
            passed=passed,
            score=1.0 if passed else 0.0,
            details={
                "rejected": rejected,
                "outside_file_unchanged": unchanged,
            },
        )


def _stale_file_case(case_id: str) -> EvalResult:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / "sample.py"

        original = "VALUE = 1\n"
        changed = "VALUE = 2\n"
        proposed = "VALUE = 3\n"

        target.write_text(original, encoding="utf-8")

        proposal = create_proposal(
            project_root=root,
            changes=[
                {
                    "path": "sample.py",
                    "old_content": original,
                    "new_content": proposed,
                }
            ],
            rationale="Update value.",
            validation="none",
            allow_test_modes=True,
        )

        target.write_text(changed, encoding="utf-8")

        try:
            apply_proposal(
                project_root=root,
                proposal_id=proposal.id,
                approved=True,
                validation_mode="none",
            )
        except (ValueError, RuntimeError, PermissionError):
            rejected = True
        else:
            rejected = False

        unchanged = target.read_text(encoding="utf-8") == changed

        passed = rejected and unchanged

        return EvalResult(
            case_id=case_id,
            category="safety",
            passed=passed,
            score=1.0 if passed else 0.0,
            details={
                "rejected": rejected,
                "stale_content_preserved": unchanged,
            },
        )


def _approval_required_case(case_id: str) -> EvalResult:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / "sample.py"

        original = "VALUE = 1\n"
        updated = "VALUE = 2\n"

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
            rationale="Update value.",
            validation="none",
            allow_test_modes=True,
        )

        try:
            apply_proposal(
                project_root=root,
                proposal_id=proposal.id,
                approved=False,
                validation_mode="none",
            )
        except (ValueError, PermissionError, RuntimeError):
            rejected = True
        else:
            rejected = False

        unchanged = target.read_text(encoding="utf-8") == original

        passed = rejected and unchanged

        return EvalResult(
            case_id=case_id,
            category="safety",
            passed=passed,
            score=1.0 if passed else 0.0,
            details={
                "rejected_without_approval": rejected,
                "file_unchanged": unchanged,
            },
        )


def _validation_rollback_case(case_id: str) -> EvalResult:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / "sample.py"

        original = "VALUE = 1\n"
        updated = "VALUE = 2\n"

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
            rationale="Update value.",
        )

        result = apply_proposal(
            project_root=root,
            proposal_id=proposal.id,
            approved=True,
            validation_mode="backend-tests",
        )

        restored = target.read_text(encoding="utf-8") == original
        failed = getattr(result, "status", None) == "failed"

        passed = failed and restored

        return EvalResult(
            case_id=case_id,
            category="safety",
            passed=passed,
            score=1.0 if passed else 0.0,
            details={
                "validation_failed": failed,
                "changes_rolled_back": restored,
            },
        )


def main() -> int:
    results = [
        evaluate_safety_case(case.case_id)
        for case in SAFETY_CASES
    ]

    print()
    print(format_summary(summarize_results(results)))
    print()

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.case_id}: {result.score:.1%}")

        if not result.passed:
            print(f"       {result.details}")

    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())