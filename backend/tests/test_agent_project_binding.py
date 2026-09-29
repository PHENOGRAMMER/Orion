from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.agent.workflow import AgentWorkflow, AgentWorkflowError, TextEdit


class AgentProjectBindingTests(unittest.TestCase):
    def test_proposal_cannot_be_applied_to_different_project_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            project_a = base / "project_a"
            project_b = base / "project_b"

            project_a.mkdir()
            project_b.mkdir()

            file_a = project_a / "sample.py"
            file_b = project_b / "sample.py"

            original = "VALUE = 1\n"
            updated = "VALUE = 2\n"

            file_a.write_text(original, encoding="utf-8")
            file_b.write_text(original, encoding="utf-8")

            workflow = AgentWorkflow()

            proposal = workflow.create_proposal(
                project_root=project_a,
                edits=[
                    TextEdit(
                        path="sample.py",
                        find=original,
                        replace=updated,
                    )
                ],
            )

            with self.assertRaises(AgentWorkflowError):
                workflow.apply_proposal(
                    proposal.id,
                    project_root=project_b,
                    approved=True,
                )

            self.assertEqual(
                file_a.read_text(encoding="utf-8"),
                original,
            )
            self.assertEqual(
                file_b.read_text(encoding="utf-8"),
                original,
            )


if __name__ == "__main__":
    unittest.main()