"""
Tests for Orion's supervised agent edit workflow.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.workflow import AgentWorkflow, AgentWorkflowError, TextEdit  # noqa: E402
from app.core.persistence import OrionPersistence  # noqa: E402


class AgentWorkflowTests(unittest.TestCase):

    def test_create_and_apply_proposal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "app.py"
            target.write_text("def greet():\n    return 'hello'\n", encoding="utf-8")

            workflow = AgentWorkflow(OrionPersistence(root / "orion.db"))
            proposal = workflow.create_proposal(
                project_root=root,
                objective="Change the greeting",
                edits=[
                    TextEdit(
                        path="app.py",
                        find="return 'hello'",
                        replace="return 'hi'",
                    )
                ],
                validation="none",
                allow_test_modes=True,
            )

            self.assertEqual(proposal["status"], "proposed")
            self.assertIn("-    return 'hello'", proposal["diff"])
            self.assertIn("+    return 'hi'", proposal["diff"])

            # Internal evaluation mode explicitly treats validation as passed.
            result = workflow.apply_proposal(proposal["proposal_id"])
            self.assertEqual(result["status"], "applied")
            self.assertTrue(result["validation"]["passed"])
            self.assertFalse(result["validation"]["validated"])
            self.assertEqual(target.read_text(encoding="utf-8"), "def greet():\n    return 'hi'\n")

    def test_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root.parent / "outside.py"
            outside.write_text("x = 1\n", encoding="utf-8")

            workflow = AgentWorkflow()
            with self.assertRaises(AgentWorkflowError):
                workflow.create_proposal(
                    project_root=root,
                    objective="Escape",
                    edits=[TextEdit(path="../outside.py", find="x = 1", replace="x = 2")],
                    validation="none",
                allow_test_modes=True,
                )

    def test_rejects_stale_file_on_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "app.py"
            target.write_text("value = 1\n", encoding="utf-8")

            workflow = AgentWorkflow(OrionPersistence(root / "orion.db"))
            proposal = workflow.create_proposal(
                project_root=root,
                objective="Change value",
                edits=[TextEdit(path="app.py", find="value = 1", replace="value = 2")],
                validation="none",
                allow_test_modes=True,
            )

            target.write_text("value = 10\n", encoding="utf-8")

            with self.assertRaises(AgentWorkflowError):
                workflow.apply_proposal(proposal["proposal_id"])

            self.assertEqual(target.read_text(encoding="utf-8"), "value = 10\n")

    def test_proposal_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "app.py"
            target.write_text("name = 'orion'\n", encoding="utf-8")
            db_path = root / "orion.db"

            first = AgentWorkflow(OrionPersistence(db_path))
            proposal = first.create_proposal(
                project_root=root,
                objective="Rename display name",
                edits=[TextEdit(path="app.py", find="'orion'", replace="'Orion'")],
                validation="none",
                allow_test_modes=True,
            )

            second = AgentWorkflow(OrionPersistence(db_path))
            loaded = second.load_proposal(proposal["proposal_id"])

            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["objective"], "Rename display name")
            self.assertEqual(loaded["status"], "proposed")


    def test_validation_failure_rolls_back_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)

            file_path = project / "example.py"
            file_path.write_text(
                "VALUE = 1\n",
                encoding="utf-8",
            )

            workflow = AgentWorkflow(OrionPersistence(project / "orion.db"))

            proposal = workflow.create_proposal(
                project_root=project,
                objective="Change value",
                edits=[
                    TextEdit(
                        path="example.py",
                        find="VALUE = 1",
                        replace="VALUE = 2",
                    )
                ],
                validation="backend-tests",
            )

            failed_validation = {
                "mode": "backend-tests",
                "passed": False,
                "command": ["fake"],
                "returncode": 1,
                "output": "Tests failed.",
            }

            with patch(
                "app.agent.workflow._run_validation",
                return_value=failed_validation,
            ):
                result = workflow.apply_proposal(
                    proposal["proposal_id"]
                )

            self.assertEqual(result["status"], "failed")
            self.assertEqual(
                result["summary"],
                "Validation failed; all changes were rolled back.",
            )

            self.assertEqual(
                file_path.read_text(encoding="utf-8"),
                "VALUE = 1\n",
            )

    def test_validation_failure_rolls_back_all_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)

            first = project / "first.py"
            second = project / "second.py"

            first.write_text(
                "VALUE = 1\n",
                encoding="utf-8",
            )

            second.write_text(
                "VALUE = 10\n",
                encoding="utf-8",
            )

            workflow = AgentWorkflow(OrionPersistence(project / "orion.db"))

            proposal = workflow.create_proposal(
                project_root=project,
                objective="Change both values",
                edits=[
                    TextEdit(
                        path="first.py",
                        find="VALUE = 1",
                        replace="VALUE = 2",
                    ),
                    TextEdit(
                        path="second.py",
                        find="VALUE = 10",
                        replace="VALUE = 20",
                    ),
                ],
                validation="backend-tests",
            )

            failed_validation = {
                "mode": "backend-tests",
                "passed": False,
                "command": ["fake"],
                "returncode": 1,
                "output": "Tests failed.",
            }

            with patch(
                "app.agent.workflow._run_validation",
                return_value=failed_validation,
            ):
                result = workflow.apply_proposal(
                    proposal["proposal_id"]
                )

            self.assertEqual(result["status"], "failed")

            self.assertEqual(
                first.read_text(encoding="utf-8"),
                "VALUE = 1\n",
            )

            self.assertEqual(
                second.read_text(encoding="utf-8"),
                "VALUE = 10\n",
            )

    def test_proposal_creation_is_audited(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "app.py"
            target.write_text("value = 1\n", encoding="utf-8")

            store = OrionPersistence(root / "orion.db")
            workflow = AgentWorkflow(store)
            
            class FakeActor:
                key_id = "test_key_1"
                name = "Test Admin"
                role = "admin"

            proposal = workflow.create_proposal(
                project_root=root,
                objective="Test audit",
                edits=[TextEdit(path="app.py", find="value = 1", replace="value = 2")],
                validation="none",
                allow_test_modes=True,
                actor=FakeActor(),
            )

            events = store.list_audit_events()
            self.assertEqual(len(events), 1)
            e = events[0]
            self.assertEqual(e["action"], "proposal.created")
            self.assertEqual(e["status"], "success")
            self.assertEqual(e["resource_type"], "edit_proposal")
            self.assertEqual(e["resource_id"], proposal["proposal_id"])
            self.assertEqual(e["actor_key_id"], "test_key_1")

    def test_successful_apply_is_audited(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "app.py"
            target.write_text("value = 1\n", encoding="utf-8")

            store = OrionPersistence(root / "orion.db")
            workflow = AgentWorkflow(store)

            proposal = workflow.create_proposal(
                project_root=root,
                objective="Test audit",
                edits=[TextEdit(path="app.py", find="value = 1", replace="value = 2")],
                validation="none",
                allow_test_modes=True,
            )
            
            success_validation = {
                "mode": "none",
                "passed": True,
                "validated": True,
            }
            with patch("app.agent.workflow._run_validation", return_value=success_validation):
                workflow.apply_proposal(proposal["proposal_id"])

            events = store.list_audit_events()
            self.assertEqual(len(events), 2)
            applied_event = events[0]
            self.assertEqual(applied_event["action"], "proposal.applied")
            self.assertEqual(applied_event["status"], "success")

    def test_failed_validation_is_audited(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "app.py"
            target.write_text("value = 1\n", encoding="utf-8")

            store = OrionPersistence(root / "orion.db")
            workflow = AgentWorkflow(store)

            proposal = workflow.create_proposal(
                project_root=root,
                objective="Test audit",
                edits=[TextEdit(path="app.py", find="value = 1", replace="value = 2")],
                validation="backend-tests",
            )
            
            failed_validation = {
                "mode": "backend-tests",
                "passed": False,
                "command": ["fake"],
                "returncode": 1,
                "output": "Tests failed.",
            }
            with patch("app.agent.workflow._run_validation", return_value=failed_validation):
                workflow.apply_proposal(proposal["proposal_id"])

            events = store.list_audit_events()
            self.assertEqual(len(events), 2)
            failed_event = events[0]
            self.assertEqual(failed_event["action"], "proposal.failed")
            self.assertEqual(failed_event["status"], "failed")
            self.assertTrue(failed_event["details"].get("rolled_back"))

    def test_audit_failure_does_not_break_successful_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "app.py"
            target.write_text("value = 1\n", encoding="utf-8")

            store = OrionPersistence(root / "orion.db")
            workflow = AgentWorkflow(store)

            proposal = workflow.create_proposal(
                project_root=root,
                objective="Test audit",
                edits=[TextEdit(path="app.py", find="value = 1", replace="value = 2")],
                validation="none",
                allow_test_modes=True,
            )
            
            success_validation = {
                "mode": "none",
                "passed": True,
                "validated": True,
            }
            
            with patch("app.agent.workflow._run_validation", return_value=success_validation):
                with patch.object(store, "record_audit_event", side_effect=RuntimeError("DB exploded")):
                    result = workflow.apply_proposal(proposal["proposal_id"])
            
            self.assertEqual(result["status"], "applied")


if __name__ == "__main__":
    unittest.main(verbosity=2)
