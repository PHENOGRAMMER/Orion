from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.persistence import OrionPersistence
from app.main import app


class AgentAPIWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

        self.sample = self.root / "sample.py"
        self.original = "VALUE = 1\n"
        self.updated = "VALUE = 2\n"
        self.sample.write_text(self.original, encoding="utf-8")

        # Mock an active GraphState and persistence so endpoints succeed
        class MockGraphState:
            project_path = str(self.root)

        app.state.graph_state = MockGraphState()
        db_path = self.root / "orion_test.db"
        app.state.persistence = OrionPersistence(db_path)
        self.client = TestClient(app)

    def tearDown(self):
        if hasattr(app.state, "graph_state"):
            delattr(app.state, "graph_state")
        if hasattr(app.state, "persistence"):
            delattr(app.state, "persistence")
        self.tmp.cleanup()

    def _auth_headers(self) -> dict[str, str]:
        return {"X-API-Key": settings.ADMIN_API_KEY}

    def _create_payload(self) -> dict:
        return {
            "objective": "Update sample value.",
            "edits": [
                {
                    "path": "sample.py",
                    "find": "VALUE = 1",
                    "replace": "VALUE = 2",
                }
            ],
        }

    def test_create_proposal_requires_auth_when_enabled(self):
        with patch.object(settings, "AUTH_ENABLED", True):
            response = self.client.post(
                "/agent/proposals",
                json=self._create_payload(),
            )

        self.assertEqual(response.status_code, 401)

    def test_create_proposal_requires_admin(self):
        viewer_key = "ob_live_viewer_test"

        class FakeUser:
            role = "viewer"

        with patch.object(settings, "AUTH_ENABLED", True), patch(
            "app.api.agent.CurrentUser",
            FakeUser,
        ):
            response = self.client.post(
                "/agent/proposals",
                headers={"X-API-Key": viewer_key},
                json=self._create_payload(),
            )

        self.assertIn(response.status_code, (401, 403, 500))

    def test_create_proposal_returns_proposed_state(self):
        with patch.object(settings, "AUTH_ENABLED", False):
            response = self.client.post(
                "/agent/proposals",
                json=self._create_payload(),
            )

        self.assertEqual(response.status_code, 201)

        body = response.json()

        self.assertIn("proposal_id", body)
        self.assertEqual(body["status"], "proposed")

        # Creating a proposal must not mutate the repository.
        self.assertEqual(
            self.sample.read_text(encoding="utf-8"),
            self.original,
        )

    def test_apply_requires_explicit_approval(self):
        with patch.object(settings, "AUTH_ENABLED", False):
            create_response = self.client.post(
                "/agent/proposals",
                json=self._create_payload(),
            )

        self.assertEqual(create_response.status_code, 201)

        proposal_id = create_response.json()["proposal_id"]

        with patch.object(settings, "AUTH_ENABLED", False):
            response = self.client.post(
                f"/agent/proposals/{proposal_id}/apply",
                json={"approved": False},
            )

        self.assertIn(response.status_code, (400, 409, 422))

        self.assertEqual(
            self.sample.read_text(encoding="utf-8"),
            self.original,
        )

    def test_approved_apply_changes_file(self):
        with patch.object(settings, "AUTH_ENABLED", False):
            create_response = self.client.post(
                "/agent/proposals",
                json=self._create_payload(),
            )

        self.assertEqual(create_response.status_code, 201)

        proposal_id = create_response.json()["proposal_id"]

        fake_val = {
            "mode": "backend-tests",
            "passed": True,
            "validated": True,
            "command": None,
            "returncode": 0,
            "output": "ok",
        }

        with patch.object(settings, "AUTH_ENABLED", False), patch(
            "app.agent.workflow._run_validation", return_value=fake_val
        ):
            response = self.client.post(
                f"/agent/proposals/{proposal_id}/apply",
                json={"approved": True},
            )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.sample.read_text(encoding="utf-8"),
            self.updated,
        )

    def test_proposal_can_be_retrieved_after_creation(self):
        with patch.object(settings, "AUTH_ENABLED", False):
            create_response = self.client.post(
                "/agent/proposals",
                json=self._create_payload(),
            )

        self.assertEqual(create_response.status_code, 201)

        proposal_id = create_response.json()["proposal_id"]

        with patch.object(settings, "AUTH_ENABLED", False):
            response = self.client.get(
                f"/agent/proposals/{proposal_id}",
            )

        self.assertEqual(response.status_code, 200)

        body = response.json()

        self.assertEqual(body["proposal_id"], proposal_id)
        self.assertEqual(body["status"], "proposed")


if __name__ == "__main__":
    unittest.main()