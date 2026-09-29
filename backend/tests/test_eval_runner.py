from __future__ import annotations

import unittest

from tests.eval.cases import EvalCase
from tests.eval.runner import (
    EvalResult,
    format_summary,
    run_case,
    run_evaluation,
    summarize_results,
)


class TestEvalRunner(unittest.TestCase):
    def test_run_case_returns_executor_result(self):
        case = EvalCase(
            case_id="test-001",
            category="graph_qa",
            prompt="Test prompt",
        )

        result = run_case(
            case,
            lambda current: EvalResult(
                case_id=current.case_id,
                category=current.category,
                passed=True,
                score=1.0,
            ),
        )

        self.assertEqual(result.case_id, "test-001")
        self.assertTrue(result.passed)
        self.assertEqual(result.score, 1.0)

    def test_run_case_rejects_wrong_case_id(self):
        case = EvalCase(
            case_id="test-001",
            category="graph_qa",
            prompt="Test prompt",
        )

        with self.assertRaises(ValueError):
            run_case(
                case,
                lambda current: EvalResult(
                    case_id="wrong-id",
                    category=current.category,
                    passed=True,
                    score=1.0,
                ),
            )

    def test_run_case_rejects_invalid_score(self):
        case = EvalCase(
            case_id="test-001",
            category="graph_qa",
            prompt="Test prompt",
        )

        with self.assertRaises(ValueError):
            run_case(
                case,
                lambda current: EvalResult(
                    case_id=current.case_id,
                    category=current.category,
                    passed=True,
                    score=1.5,
                ),
            )

    def test_run_evaluation_runs_all_cases(self):
        seen: list[str] = []

        def executor(case: EvalCase) -> EvalResult:
            seen.append(case.case_id)
            return EvalResult(
                case_id=case.case_id,
                category=case.category,
                passed=True,
                score=1.0,
            )

        results = run_evaluation(executor)

        self.assertEqual(len(results), 11)
        self.assertEqual(len(seen), 11)
        self.assertEqual(
            {result.case_id for result in results},
            set(seen),
        )

    def test_run_evaluation_filters_by_category(self):
        results = run_evaluation(
            lambda case: EvalResult(
                case_id=case.case_id,
                category=case.category,
                passed=True,
                score=1.0,
            ),
            category="safety",
        )

        self.assertEqual(len(results), 4)
        self.assertTrue(
            all(result.category == "safety" for result in results)
        )

    def test_summarize_empty_results(self):
        summary = summarize_results([])

        self.assertEqual(summary["cases"], 0)
        self.assertEqual(summary["passed"], 0)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["pass_rate"], 0.0)
        self.assertEqual(summary["average_score"], 0.0)
        self.assertEqual(summary["by_category"], {})

    def test_summarize_results(self):
        results = [
            EvalResult("a", "graph_qa", True, 1.0),
            EvalResult("b", "graph_qa", False, 0.0),
            EvalResult("c", "safety", True, 1.0),
        ]

        summary = summarize_results(results)

        self.assertEqual(summary["cases"], 3)
        self.assertEqual(summary["passed"], 2)
        self.assertEqual(summary["failed"], 1)
        self.assertAlmostEqual(summary["pass_rate"], 2 / 3)
        self.assertAlmostEqual(summary["average_score"], 2 / 3)

        self.assertEqual(summary["by_category"]["graph_qa"]["cases"], 2)
        self.assertEqual(summary["by_category"]["graph_qa"]["passed"], 1)
        self.assertEqual(summary["by_category"]["safety"]["cases"], 1)
        self.assertEqual(summary["by_category"]["safety"]["passed"], 1)

    def test_format_summary_contains_key_metrics(self):
        results = [
            EvalResult("a", "graph_qa", True, 1.0),
            EvalResult("b", "graph_qa", False, 0.0),
        ]

        output = format_summary(summarize_results(results))

        self.assertIn("Orion Evaluation", output)
        self.assertIn("Cases:         2", output)
        self.assertIn("Passed:        1", output)
        self.assertIn("Failed:        1", output)
        self.assertIn("Pass rate:", output)
        self.assertIn("Average score:", output)
        self.assertIn("graph_qa", output)


if __name__ == "__main__":
    unittest.main()