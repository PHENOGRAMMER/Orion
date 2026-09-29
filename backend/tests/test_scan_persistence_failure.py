from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.api import graph


class ScanPersistenceFailureTests(unittest.TestCase):
    def test_scan_persistence_failure_marks_job_as_error(self):
        persistence = SimpleNamespace(
            save_scan_job=lambda *args, **kwargs: None,
            save_graph_state=lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError("DB unavailable")
            ),
            release_scan_lease = lambda *args, **kwargs: True,
            record_audit_event=lambda *args, **kwargs: None,
        )

        app_state = SimpleNamespace(
            persistence=persistence,
        )

        fake_state = SimpleNamespace(
            stats=lambda: {
                "nodes": 2,
                "edges": 1,
            }
        )

        with patch(
            "app.api.graph.graph_state.scan_project",
            return_value=fake_state,
        ), patch(
            "app.api.graph.graph_state.publish"
        ) as publish:

            graph._do_scan(
                app_state,
                "/project-a",
                "test-job",
                None,
            )

        job = graph._jobs["test-job"]

        self.assertEqual(job["status"], "error")
        self.assertIn("DB unavailable", job["message"])


        # Persistence failure must prevent publication.
        publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()