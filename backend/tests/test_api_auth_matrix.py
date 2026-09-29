"""Integration tests for the production API authentication boundary."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.agent import router as agent_router
from app.api.auth import router as auth_router
from app.api.graph import router as graph_router
from app.api.graph_exporter import router as export_router
from app.api.orion_llm_router import router as llm_router
from app.core.auth import (
    ROLE_ADMIN,
    ROLE_VIEWER,
    generate_api_key,
    hash_key,
    key_id_from_hash,
)
from app.core.config import settings
from app.core.graph_state import GraphState
from app.core.persistence import OrionPersistence
from app.scanner.knowledge_graph.graph import KnowledgeGraph
from app.scanner.knowledge_graph.query import KnowledgeGraphQuery
from app.scanner.knowledge_graph.search import SymbolSearchIndex


class APIAuthMatrixTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

        self.db = OrionPersistence(self.root / "orion.db")

        self.admin_key = self._create_key("admin", ROLE_ADMIN)
        self.viewer_key = self._create_key("viewer", ROLE_VIEWER)

        graph = KnowledgeGraph()

        self.app = FastAPI()
        self.app.state.persistence = self.db
        self.app.state.graph_state = GraphState(
            graph=graph,
            query=KnowledgeGraphQuery(graph),
            search=SymbolSearchIndex.from_graph(graph),
            project_path=str(self.root),
        )

        self.app.include_router(auth_router, prefix="/auth")
        self.app.include_router(graph_router, prefix="/graph")
        self.app.include_router(export_router)
        self.app.include_router(llm_router, prefix="/llm")
        self.app.include_router(agent_router, prefix="/agent")

        self.old_auth = settings.AUTH_ENABLED
        self.old_roots = settings.ALLOWED_ROOTS

        settings.AUTH_ENABLED = True
        settings.ALLOWED_ROOTS = str(self.root)

    def tearDown(self):
        settings.AUTH_ENABLED = self.old_auth
        settings.ALLOWED_ROOTS = self.old_roots
        self.tmp.cleanup()

    def _create_key(self, name: str, role: str) -> str:
        raw = generate_api_key()
        hashed = hash_key(raw)

        self.db.create_api_key(
            key_id_from_hash(hashed),
            name,
            hashed,
            role,
        )

        return raw

    def test_every_protected_route_rejects_missing_key(self):
        routes = [
            ("GET", "/auth/keys", None),
            ("GET", "/graph/stats", None),
            ("GET", "/graph/search?q=x", None),
            ("GET", "/graph/scan/unknown", None),
            ("GET", "/graph/browse", None),
            ("GET", "/graph/path?from=x&to=y", None),
            ("GET", "/graph/symbol/missing", None),
            ("GET", "/graph/symbol/missing/impact", None),
            ("GET", "/export?download=true", None),
            ("POST", "/graph/scan", {"path": str(self.root)}),
            (
                "POST",
                "/agent/proposals",
                {
                    "objective": "x",
                    "edits": [
                        {
                            "path": "x.py",
                            "find": "a",
                            "replace": "b",
                        }
                    ],
                },
            ),
            ("GET", "/agent/proposals/missing", None),
            (
                "POST",
                "/agent/proposals/missing/apply",
                {"approved": True},
            ),
            (
                "POST",
                "/llm/ask",
                {
                    "question": "x",
                    "focal_symbol": "missing",
                },
            ),
            (
                "POST",
                "/llm/stream",
                {
                    "question": "x",
                    "focal_symbol": "missing",
                },
            ),
            ("GET", "/llm/health", None),
            ("GET", "/llm/debug/missing", None),
            ("POST", "/llm/warm", None),
        ]

        client = TestClient(self.app)

        for method, path, body in routes:
            kwargs = {}

            if body is not None:
                kwargs["json"] = body

            response = client.request(
                method,
                path,
                **kwargs,
            )

            self.assertEqual(
                response.status_code,
                401,
                f"{method} {path}: {response.text}",
            )

    def test_viewer_is_denied_every_admin_only_route(self):
        routes = [
            (
                "POST",
                "/auth/keys",
                {
                    "name": "x",
                    "role": "viewer",
                },
            ),
            ("DELETE", "/auth/keys/unknown", None),
            (
                "POST",
                "/graph/scan",
                {
                    "path": str(self.root),
                },
            ),
            (
                "POST",
                "/agent/proposals",
                {
                    "objective": "x",
                    "edits": [
                        {
                            "path": "x.py",
                            "find": "a",
                            "replace": "b",
                        }
                    ],
                },
            ),
            (
                "POST",
                "/agent/proposals/missing/apply",
                {
                    "approved": True,
                },
            ),
            ("POST", "/llm/warm", None),
        ]

        client = TestClient(self.app)

        headers = {
            "X-API-Key": self.viewer_key,
        }

        for method, path, body in routes:
            kwargs = {
                "headers": headers,
            }

            if body is not None:
                kwargs["json"] = body

            response = client.request(
                method,
                path,
                **kwargs,
            )

            self.assertEqual(
                response.status_code,
                403,
                f"{method} {path}: {response.text}",
            )

    def test_viewer_can_read_graph(self):
        client = TestClient(self.app)

        headers = {
            "X-API-Key": self.viewer_key,
        }

        self.assertEqual(
            client.get(
                "/graph/stats",
                headers=headers,
            ).status_code,
            200,
        )

        self.assertEqual(
            client.get(
                "/graph/search?q=x",
                headers=headers,
            ).status_code,
            200,
        )

        self.assertEqual(
            client.get(
                "/graph/path?from=x&to=y",
                headers=headers,
            ).status_code,
            200,
        )

        self.assertEqual(
            client.get(
                "/graph/scan/unknown",
                headers=headers,
            ).status_code,
            404,
        )

        self.assertEqual(
            client.get(
                "/graph/browse",
                headers=headers,
            ).status_code,
            200,
        )

    def test_auth_can_be_disabled_for_local_development(self):
        settings.AUTH_ENABLED = False

        response = TestClient(self.app).get("/graph/stats")

        self.assertEqual(response.status_code, 200)

    def test_revoked_key_loses_access(self):
        client = TestClient(self.app)

        headers = {
            "X-API-Key": self.viewer_key,
        }

        self.assertEqual(
            client.get(
                "/graph/stats",
                headers=headers,
            ).status_code,
            200,
        )

        self.assertTrue(
            self.db.revoke_api_key(
                key_id_from_hash(
                    hash_key(self.viewer_key)
                )
            )
        )

        self.assertEqual(
            client.get(
                "/graph/stats",
                headers=headers,
            ).status_code,
            401,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)