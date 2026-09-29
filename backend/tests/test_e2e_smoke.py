"""
End-to-end smoke test for Orion Production v1 core workflows.

Tests:
1. Scanning a project and polling job completion
2. Graph stats and symbol search
3. Creating an edit proposal
4. Listing edit proposals via API
5. Applying an approved proposal and verifying validation execution
6. Listing audit log events
"""

from __future__ import annotations

import time
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.auth import ROLE_ADMIN, generate_api_key, hash_key, key_id_from_hash
from app.core.config import settings
from app.core.persistence import OrionPersistence
from app.main import app


def test_e2e_production_workflow():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        old_roots = settings.ALLOWED_ROOTS
        settings.ALLOWED_ROOTS = str(root)

        try:
            db_path = root / "test_orion.db"
            persistence = OrionPersistence(db_path)

            raw_key = generate_api_key()
            hashed = hash_key(raw_key)
            persistence.create_api_key(
                key_id=key_id_from_hash(hashed),
                name="test-admin",
                key_hash=hashed,
                role=ROLE_ADMIN,
            )

            # 1. Create a dummy Python project
            target_file = root / "sample.py"
            test_file = root / "test_sample.py"

            target_file.write_text("def greet(name: str) -> str:\n    return f'Hello, {name}'\n", encoding="utf-8")
            test_file.write_text(
                "from sample import greet\n\ndef test_greet():\n    assert greet('World') == 'Hello, World'\n",
                encoding="utf-8",
            )

            with TestClient(app) as client:
                app.state.persistence = persistence
                headers = {"X-API-Key": raw_key}

                # 2. Trigger Scan
                scan_resp = client.post("/graph/scan", json={"path": str(root)}, headers=headers)
                assert scan_resp.status_code in (200, 202), scan_resp.text
                job_id = scan_resp.json()["job_id"]
                assert job_id

                # 3. Poll Scan until done
                for _ in range(30):
                    poll_resp = client.get(f"/graph/scan/{job_id}", headers=headers)
                    assert poll_resp.status_code == 200
                    status = poll_resp.json()["status"]
                    if status == "done":
                        break
                    time.sleep(0.1)
                else:
                    pytest.fail("Scan background job did not complete within timeout.")

                # 4. Check Graph Stats
                stats_resp = client.get("/graph/stats", headers=headers)
                assert stats_resp.status_code == 200
                assert stats_resp.json()["nodes"] >= 1

                # 5. Search Symbols
                search_resp = client.get("/graph/search?q=greet", headers=headers)
                assert search_resp.status_code == 200
                assert len(search_resp.json()["results"]) >= 1

                # 6. Create Edit Proposal
                proposal_payload = {
                    "objective": "Update greet to say Hi",
                    "edits": [
                        {
                            "path": "sample.py",
                            "find": "return f'Hello, {name}'",
                            "replace": "return f'Hi, {name}'",
                        },
                        {
                            "path": "test_sample.py",
                            "find": "assert greet('World') == 'Hello, World'",
                            "replace": "assert greet('World') == 'Hi, World'",
                        },
                    ],
                    "validation": "pytest",
                    "test_paths": ["test_sample.py"],
                }
                create_resp = client.post("/agent/proposals", json=proposal_payload, headers=headers)
                assert create_resp.status_code == 201, create_resp.text
                proposal = create_resp.json()
                pid = proposal["proposal_id"]
                assert proposal["status"] == "proposed"
                assert "diff" in proposal

                # 7. List Proposals via GET /agent/proposals
                list_resp = client.get("/agent/proposals", headers=headers)
                assert list_resp.status_code == 200
                items = list_resp.json()["proposals"]
                assert any(p["proposal_id"] == pid for p in items)

                # 8. Apply Proposal & Validate
                apply_resp = client.post(f"/agent/proposals/{pid}/apply", json={"approved": True}, headers=headers)
                assert apply_resp.status_code == 200, apply_resp.text
                applied = apply_resp.json()
                assert applied["status"] == "applied"
                assert applied["validation"]["passed"] is True

                # Verify file content updated
                assert target_file.read_text(encoding="utf-8") == "def greet(name: str) -> str:\n    return f'Hi, {name}'\n"

                # 9. List Audit Log
                audit_resp = client.get("/agent/audit", headers=headers)
                assert audit_resp.status_code == 200
                events = audit_resp.json()["events"]
                assert len(events) >= 1
        finally:
            settings.ALLOWED_ROOTS = old_roots
