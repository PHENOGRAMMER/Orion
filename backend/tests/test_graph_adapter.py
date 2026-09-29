from __future__ import annotations

import unittest

from app.core.graph_state import GraphState
from app.scanner.knowledge_graph import (
    Edge,
    EdgeType,
    KnowledgeGraph,
    KnowledgeGraphQuery,
    Node,
    NodeType,
    SymbolSearchIndex,
)
from tests.eval.cases import EvalCase
from tests.eval.graph_adapter import evaluate_graph_case


class TestGraphAdapter(unittest.TestCase):
    def setUp(self):
        graph = KnowledgeGraph()

        scanner = Node(
            id="symbol:ProjectScanner.scan",
            type=NodeType.FUNCTION,
            name="scan",
            qualified_name="ProjectScanner.scan",
            module="scanner",
        )

        parse = Node(
            id="symbol:Parser.parse",
            type=NodeType.FUNCTION,
            name="parse",
            qualified_name="Parser.parse",
            module="parser",
        )

        validate = Node(
            id="symbol:Validator.validate",
            type=NodeType.FUNCTION,
            name="validate",
            qualified_name="Validator.validate",
            module="validator",
        )

        caller = Node(
            id="symbol:Application.run",
            type=NodeType.FUNCTION,
            name="run",
            qualified_name="Application.run",
            module="application",
        )

        for node in (scanner, parse, validate, caller):
            graph.add_node(node)

        graph.add_edge(
            Edge(
                source="symbol:Application.run",
                target="symbol:ProjectScanner.scan",
                type=EdgeType.CALLS,
            )
        )

        graph.add_edge(
            Edge(
                source="symbol:ProjectScanner.scan",
                target="symbol:Parser.parse",
                type=EdgeType.CALLS,
            )
        )

        graph.add_edge(
            Edge(
                source="symbol:ProjectScanner.scan",
                target="symbol:Validator.validate",
                type=EdgeType.CALLS,
            )
        )

        query = KnowledgeGraphQuery(graph)
        self.state = GraphState(
            graph=graph,
            query=query,
            search=SymbolSearchIndex.from_graph(graph),
            project_path="/mock/project",
        )

    def test_symbol_lookup(self):
        case = EvalCase(
            case_id="test-symbol",
            category="graph_qa",
            prompt="Find ProjectScanner.scan.",
            expected={
                "operation": "symbol_lookup",
                "symbol": "ProjectScanner.scan",
            },
        )

        result = evaluate_graph_case(case, self.state)

        self.assertTrue(result.passed)
        self.assertEqual(result.score, 1.0)
        self.assertTrue(result.details["found"])

    def test_missing_symbol_fails(self):
        case = EvalCase(
            case_id="test-missing",
            category="graph_qa",
            prompt="Find Missing.symbol.",
            expected={
                "operation": "symbol_lookup",
                "symbol": "Missing.symbol",
            },
        )

        result = evaluate_graph_case(case, self.state)

        self.assertFalse(result.passed)
        self.assertEqual(result.score, 0.0)
        self.assertFalse(result.details["found"])

    def test_callers_are_returned(self):
        case = EvalCase(
            case_id="test-callers",
            category="graph_qa",
            prompt="Find callers of ProjectScanner.scan.",
            expected={
                "operation": "callers",
                "symbol": "ProjectScanner.scan",
                "expected_symbols": ["Application.run"],
            },
        )

        result = evaluate_graph_case(case, self.state)

        self.assertTrue(result.passed)
        self.assertEqual(result.score, 1.0)
        self.assertEqual(
            result.details["actual"],
            ["Application.run"],
        )

    def test_callees_are_returned(self):
        case = EvalCase(
            case_id="test-callees",
            category="graph_qa",
            prompt="Find callees of ProjectScanner.scan.",
            expected={
                "operation": "callees",
                "symbol": "ProjectScanner.scan",
                "expected_symbols": [
                    "Parser.parse",
                    "Validator.validate",
                ],
            },
        )

        result = evaluate_graph_case(case, self.state)

        self.assertTrue(result.passed)
        self.assertEqual(result.score, 1.0)
        self.assertEqual(
            result.details["actual"],
            [
                "Parser.parse",
                "Validator.validate",
            ],
        )

    def test_impact_is_returned(self):
        case = EvalCase(
            case_id="test-impact",
            category="graph_qa",
            prompt="Find the impact of changing ProjectScanner.scan.",
            expected={
                "operation": "impact",
                "symbol": "ProjectScanner.scan",
                "expected_direct_callers": 1,
                "expected_total_callers": 1,
                "expected_affected_modules": ["application"],
            },
        )

        result = evaluate_graph_case(case, self.state)

        self.assertTrue(result.passed)
        self.assertEqual(result.score, 1.0)
        self.assertEqual(result.details["actual"]["direct_callers"], 1)
        self.assertGreaterEqual(result.details["actual"]["total_callers"], 1)

    def test_missing_symbol_for_callers_fails(self):
        case = EvalCase(
            case_id="test-missing-callers",
            category="graph_qa",
            prompt="Find callers of Missing.symbol.",
            expected={
                "operation": "callers",
                "symbol": "Missing.symbol",
            },
        )

        result = evaluate_graph_case(case, self.state)

        self.assertFalse(result.passed)
        self.assertEqual(result.score, 0.0)
        self.assertEqual(
            result.details["error"],
            "symbol_not_found",
        )

    def test_missing_symbol_for_callees_fails(self):
        case = EvalCase(
            case_id="test-missing-callees",
            category="graph_qa",
            prompt="Find callees of Missing.symbol.",
            expected={
                "operation": "callees",
                "symbol": "Missing.symbol",
            },
        )

        result = evaluate_graph_case(case, self.state)

        self.assertFalse(result.passed)
        self.assertEqual(result.score, 0.0)
        self.assertEqual(
            result.details["error"],
            "symbol_not_found",
        )

    def test_missing_symbol_for_impact_fails(self):
        case = EvalCase(
            case_id="test-missing-impact",
            category="graph_qa",
            prompt="Find the impact of Missing.symbol.",
            expected={
                "operation": "impact",
                "symbol": "Missing.symbol",
            },
        )

        result = evaluate_graph_case(case, self.state)

        self.assertFalse(result.passed)
        self.assertEqual(result.score, 0.0)
        self.assertEqual(
            result.details["error"],
            "symbol_not_found",
        )


if __name__ == "__main__":
    unittest.main()