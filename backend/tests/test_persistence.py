"""
Tests for Orion's SQLite persistence layer.

These cover the two production-v1 requirements introduced by Day 2:

- graph snapshots survive a restart and reload into a live queryable graph
- scan job state is stored outside process memory

Stdlib only.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.persistence import OrionPersistence  # noqa: E402
from app.core.graph_state import GraphState  # noqa: E402
from app.scanner.knowledge_graph.graph import KnowledgeGraph  # noqa: E402
from app.scanner.knowledge_graph.models import EdgeType, GraphEdge, GraphNode, NodeType  # noqa: E402
from app.scanner.knowledge_graph.query import KnowledgeGraphQuery  # noqa: E402
from app.scanner.knowledge_graph.search import SymbolSearchIndex  # noqa: E402


def build_state(project_root: Path) -> GraphState:
    graph = KnowledgeGraph()

    graph.add_node(
        GraphNode(
            id="symbol:app.alpha",
            type=NodeType.FUNCTION,
            name="alpha",
            qualified_name="app.alpha",
            module="app",
            path=project_root / "app.py",
            line=3,
        )
    )
    graph.add_node(
        GraphNode(
            id="symbol:app.beta",
            type=NodeType.FUNCTION,
            name="beta",
            qualified_name="app.beta",
            module="app",
            path=project_root / "app.py",
            line=9,
        )
    )
    graph.add_edge(
        GraphEdge(
            source="symbol:app.alpha",
            target="symbol:app.beta",
            type=EdgeType.CALLS,
            metadata={"file": str(project_root / "app.py"), "line": "4"},
        )
    )

    return GraphState(
        graph=graph,
        query=KnowledgeGraphQuery(graph),
        search=SymbolSearchIndex.from_graph(graph),
        project_path=str(project_root),
    )


class TestPersistence(unittest.TestCase):

    def test_graph_state_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            db_path = tmpdir / "orion.db"
            project_root = tmpdir / "project"
            project_root.mkdir()

            persistence = OrionPersistence(db_path)
            state = build_state(project_root)

            persistence.save_graph_state(state)
            loaded = persistence.load_graph_state(str(project_root))

            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.project_path, str(project_root))
            self.assertEqual(loaded.stats()["nodes"], 2)
            self.assertEqual(loaded.stats()["edges"], 1)
            self.assertEqual(loaded.query.callers_of("app.beta")[0].qualified_name, "app.alpha")
            self.assertEqual(loaded.query.callees_of("app.alpha")[0].qualified_name, "app.beta")
            self.assertEqual(loaded.search.search("alpha")[0][1], "app.alpha")

    def test_scan_job_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "orion.db"
            persistence = OrionPersistence(db_path)

            persistence.save_scan_job(
                "abc123",
                {
                    "status": "running",
                    "message": "Scanning project…",
                    "project_path": "/tmp/project",
                    "stats": None,
                },
            )
            persistence.save_scan_job(
                "abc123",
                {
                    "status": "done",
                    "message": "Scanned 2 nodes, 1 edges.",
                    "project_path": "/tmp/project",
                    "stats": {"nodes": 2, "edges": 1},
                },
            )

            job = persistence.load_scan_job("abc123")
            self.assertIsNotNone(job)
            self.assertEqual(job["status"], "done")
            self.assertEqual(job["message"], "Scanned 2 nodes, 1 edges.")
            self.assertEqual(job["project_path"], "/tmp/project")
            self.assertEqual(job["stats"], {"nodes": 2, "edges": 1})


class TestScanJobRecovery(unittest.TestCase):
    def test_incomplete_jobs_are_marked_interrupted(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = OrionPersistence(Path(tmp) / "orion.db")

            store.save_scan_job(
                "pending",
                {
                    "project_path": "/repo",
                    "status": "pending",
                    "message": "Waiting",
                },
            )
            store.save_scan_job(
                "running",
                {
                    "project_path": "/repo",
                    "status": "running",
                    "message": "Scanning",
                },
            )
            store.save_scan_job(
                "done",
                {
                    "project_path": "/repo",
                    "status": "done",
                    "message": "Complete",
                },
            )

            self.assertEqual(store.recover_incomplete_scan_jobs(), 2)

            pending = store.load_scan_job("pending")
            running = store.load_scan_job("running")
            done = store.load_scan_job("done")

            self.assertEqual(pending["status"], "error")
            self.assertEqual(running["status"], "error")
            self.assertIn("interrupted", running["message"])

            self.assertEqual(done["status"], "done")

    def test_recovery_clears_interrupted_scan_leases(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = OrionPersistence(Path(tmp) / "orion.db")
            project = "/repo/project"
            job_id = "job-interrupted"

            store.save_scan_job(
                job_id,
                {
                    "project_path": project,
                    "status": "running",
                    "message": "Scanning project...",
                },
            )
            self.assertTrue(store.acquire_scan_lease(project, job_id))

            # Prior to recovery, a new job cannot acquire the lease
            self.assertFalse(store.acquire_scan_lease(project, "job-new"))

            # Recover incomplete jobs
            recovered_count = store.recover_incomplete_scan_jobs()
            self.assertEqual(recovered_count, 1)

            # Job is marked error
            job = store.load_scan_job(job_id)
            self.assertIsNotNone(job)
            self.assertEqual(job["status"], "error")

            # Stale lease was deleted during recovery, so a new job can now acquire the lease
            self.assertTrue(store.acquire_scan_lease(project, "job-new"))

class TestAuditEvents(unittest.TestCase):
    def test_record_audit_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = OrionPersistence(Path(tmp) / "orion.db")
            store.record_audit_event(
                event_id="evt_1",
                action="scan.started",
                status="success",
            )
            events = store.list_audit_events()
            self.assertEqual(len(events), 1)

    def test_audit_event_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = OrionPersistence(Path(tmp) / "orion.db")
            store.record_audit_event(
                event_id="evt_2",
                action="proposal.applied",
                status="success",
                actor_key_id="key_123",
                actor_name="Agent",
                actor_role="agent",
                resource_type="proposal",
                resource_id="prop_1",
                project_path="/repo",
            )
            events = store.list_audit_events()
            self.assertEqual(len(events), 1)
            e = events[0]
            self.assertEqual(e["event_id"], "evt_2")
            self.assertEqual(e["action"], "proposal.applied")
            self.assertEqual(e["status"], "success")
            self.assertEqual(e["actor_key_id"], "key_123")
            self.assertEqual(e["actor_name"], "Agent")
            self.assertEqual(e["actor_role"], "agent")
            self.assertEqual(e["resource_type"], "proposal")
            self.assertEqual(e["resource_id"], "prop_1")
            self.assertEqual(e["project_path"], "/repo")

    def test_audit_event_with_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = OrionPersistence(Path(tmp) / "orion.db")
            store.record_audit_event(
                event_id="evt_3",
                action="scan.completed",
                status="success",
                details={"nodes": 5, "edges": 3},
            )
            events = store.list_audit_events()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["details"], {"nodes": 5, "edges": 3})

    def test_list_audit_events_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = OrionPersistence(Path(tmp) / "orion.db")
            store.record_audit_event(
                event_id="evt_old",
                action="scan.started",
                status="success",
            )
            import time
            time.sleep(0.01)
            store.record_audit_event(
                event_id="evt_new",
                action="scan.completed",
                status="success",
            )
            events = store.list_audit_events()
            self.assertEqual(len(events), 2)
            self.assertEqual(events[0]["event_id"], "evt_new")
            self.assertEqual(events[1]["event_id"], "evt_old")

    def test_audit_limit_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = OrionPersistence(Path(tmp) / "orion.db")
            for i in range(5):
                store.record_audit_event(
                    event_id=f"evt_{i}",
                    action="scan.started",
                    status="success",
                )
            
            events_2 = store.list_audit_events(limit=2)
            self.assertEqual(len(events_2), 2)
            
            events_0 = store.list_audit_events(limit=0)
            self.assertEqual(len(events_0), 1)

    def test_audit_event_does_not_store_api_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "orion.db"
            store = OrionPersistence(db_path)
            
            store.record_audit_event(
                event_id="evt_auth_failed",
                action="auth.failed",
                status="failure",
                actor_key_id="key_456",
                details={"reason": "invalid key"}
            )
            
            import sqlite3
            import json
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM audit_events WHERE event_id = 'evt_auth_failed'").fetchall()
            conn.close()
            
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["actor_key_id"], "key_456")
            
            # Ensure no extra columns that might store a key
            row_dict = dict(row)
            self.assertNotIn("raw_key", row_dict)
            self.assertNotIn("api_key", row_dict)
            
            # Ensure it's not in details either
            details = json.loads(row["details_json"])
            self.assertNotIn("raw_key", details)

if __name__ == "__main__":
    unittest.main(verbosity=2)
