import sys
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api.graph import router as graph_router
from app.core.graph_state import GraphState, publish
from app.scanner.knowledge_graph.graph import KnowledgeGraph
from app.scanner.knowledge_graph.models import EdgeType, GraphEdge, GraphNode
from app.scanner.knowledge_graph.query import KnowledgeGraphQuery


class GraphPathRouteTests(unittest.TestCase):
    def build_app(self):
        patcher = patch("app.core.config.settings.AUTH_ENABLED", False)
        patcher.start()
        self.addCleanup(patcher.stop)
        app = FastAPI()
        app.include_router(graph_router, prefix="/graph")

        graph = KnowledgeGraph()
        for symbol in ["pkg.A", "pkg.B", "pkg.C"]:
            graph.add_node(
                GraphNode(
                    id=f"symbol:{symbol}",
                    type="function",
                    name=symbol.split(".")[-1],
                    qualified_name=symbol,
                    module="pkg",
                    path=None,
                    line=1,
                )
            )
        graph.add_edge(GraphEdge(source="symbol:pkg.A", target="symbol:pkg.B", type=EdgeType.CALLS))
        graph.add_edge(GraphEdge(source="symbol:pkg.B", target="symbol:pkg.C", type=EdgeType.CALLS))

        publish(app.state, GraphState(
            graph=graph,
            query=KnowledgeGraphQuery(graph),
            search=None,
            project_path="/tmp/project",
        ))
        return app

    def test_graph_path_accepts_from_and_to_aliases_and_returns_hops(self):
        app = self.build_app()
        client = TestClient(app)

        response = client.get("/graph/path?from=pkg.A&to=pkg.C")

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["path"], ["pkg.A", "pkg.B", "pkg.C"])
        self.assertEqual(payload["hops"], 2)


if __name__ == "__main__":
    unittest.main()
