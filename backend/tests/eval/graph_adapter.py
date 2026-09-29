from __future__ import annotations

from typing import Any

from app.core.graph_state import GraphState
from tests.eval.cases import EvalCase
from tests.eval.runner import EvalResult


def _names(nodes: list[Any]) -> list[str]:
    """Extract stable qualified symbol names from graph nodes."""
    names: list[str] = []

    for node in nodes:
        name = getattr(node, "qualified_name", None) or getattr(node, "name", None)
        if name:
            names.append(str(name))

    return sorted(set(names))


def _find_symbol(state: GraphState, symbol: str) -> Any | None:
    """Resolve a symbol using Orion's deterministic graph query layer."""
    return state.query.get_symbol(symbol)


def _exact_list_score(actual: list[str], expected: list[str]) -> float:
    """
    Return a deterministic exact-set score.

    Ordering is intentionally ignored because callers/callees are graph
    relationships rather than ordered sequences.
    """
    return 1.0 if sorted(set(actual)) == sorted(set(expected)) else 0.0


def evaluate_graph_case(
    case: EvalCase,
    state: GraphState,
) -> EvalResult:
    """
    Evaluate one graph QA case against a real Orion GraphState.

    Scores are based on deterministic structural ground truth rather than
    natural-language similarity.
    """
    expected = case.expected
    operation = expected.get("operation")

    if operation == "symbol_lookup":
        symbol = str(expected["symbol"])
        node = _find_symbol(state, symbol)

        passed = node is not None

        return EvalResult(
            case_id=case.case_id,
            category=case.category,
            passed=passed,
            score=1.0 if passed else 0.0,
            details={
                "operation": operation,
                "symbol": symbol,
                "found": passed,
            },
        )

    if operation == "callers":
        symbol = str(expected["symbol"])
        node = _find_symbol(state, symbol)

        if node is None:
            return EvalResult(
                case_id=case.case_id,
                category=case.category,
                passed=False,
                score=0.0,
                details={
                    "operation": operation,
                    "symbol": symbol,
                    "error": "symbol_not_found",
                },
            )

        actual = _names(state.query.callers_of(symbol))
        expected_symbols = [
            str(item)
            for item in expected.get("expected_symbols", [])
        ]

        score = _exact_list_score(actual, expected_symbols)

        return EvalResult(
            case_id=case.case_id,
            category=case.category,
            passed=score == 1.0,
            score=score,
            details={
                "operation": operation,
                "symbol": symbol,
                "actual": actual,
                "expected": sorted(set(expected_symbols)),
            },
        )

    if operation == "callees":
        symbol = str(expected["symbol"])
        node = _find_symbol(state, symbol)

        if node is None:
            return EvalResult(
                case_id=case.case_id,
                category=case.category,
                passed=False,
                score=0.0,
                details={
                    "operation": operation,
                    "symbol": symbol,
                    "error": "symbol_not_found",
                },
            )

        actual = _names(state.query.callees_of(symbol))
        expected_symbols = [
            str(item)
            for item in expected.get("expected_symbols", [])
        ]

        score = _exact_list_score(actual, expected_symbols)

        return EvalResult(
            case_id=case.case_id,
            category=case.category,
            passed=score == 1.0,
            score=score,
            details={
                "operation": operation,
                "symbol": symbol,
                "actual": actual,
                "expected": sorted(set(expected_symbols)),
            },
        )

    if operation == "impact":
        symbol = str(expected["symbol"])
        node = _find_symbol(state, symbol)

        if node is None:
            return EvalResult(
                case_id=case.case_id,
                category=case.category,
                passed=False,
                score=0.0,
                details={
                    "operation": operation,
                    "symbol": symbol,
                    "error": "symbol_not_found",
                },
            )

        impact = state.query.impact_of(symbol)

        actual_direct_count = int(impact.get("direct_count", 0))
        actual_total_count = int(impact.get("total_count", 0))
        actual_modules = sorted(
            str(item)
            for item in impact.get("affected_modules", [])
        )

        expected_direct_count = int(
            expected.get("expected_direct_callers", 0)
        )
        expected_total_count = int(
            expected.get("expected_total_callers", 0)
        )
        expected_modules = sorted(
            str(item)
            for item in expected.get("expected_affected_modules", [])
        )

        direct_ok = actual_direct_count == expected_direct_count
        total_ok = actual_total_count == expected_total_count
        modules_ok = actual_modules == expected_modules

        checks = [
            direct_ok,
            total_ok,
            modules_ok,
        ]

        score = sum(checks) / len(checks)

        return EvalResult(
            case_id=case.case_id,
            category=case.category,
            passed=score == 1.0,
            score=score,
            details={
                "operation": operation,
                "symbol": symbol,
                "actual": {
                    "direct_callers": actual_direct_count,
                    "total_callers": actual_total_count,
                    "affected_modules": actual_modules,
                },
                "expected": {
                    "direct_callers": expected_direct_count,
                    "total_callers": expected_total_count,
                    "affected_modules": expected_modules,
                },
            },
        )

    if operation == "path":
        source = str(expected["from_symbol"])
        target = str(expected["to_symbol"])

        actual_path = state.query.path_between(source, target)

        expected_path = [
            str(item)
            for item in expected.get("expected_path", [])
        ]

        actual = list(actual_path) if actual_path else []

        passed = actual == expected_path

        return EvalResult(
            case_id=case.case_id,
            category=case.category,
            passed=passed,
            score=1.0 if passed else 0.0,
            details={
                "operation": operation,
                "from_symbol": source,
                "to_symbol": target,
                "actual": actual,
                "expected": expected_path,
            },
        )

    return EvalResult(
        case_id=case.case_id,
        category=case.category,
        passed=False,
        score=0.0,
        details={
            "error": f"unsupported_operation:{operation}",
        },
    )