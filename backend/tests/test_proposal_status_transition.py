import tempfile
import unittest
from pathlib import Path

from app.core.persistence import OrionPersistence


class ProposalStatusTransitionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "orion.db"
        self.store = OrionPersistence(self.db)

        self.store.save_edit_proposal(
            {
                "proposal_id": "proposal-1",
                "project_path": self.tmp.name,
                "objective": "test",
                "status": "proposed",
                "changes": [],
                "diff": "",
                "summary": "test",
                "validation_mode": "backend-tests",
                "validation": None,
            }
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_expected_status_is_required(self):
        self.assertTrue(
            self.store.transition_edit_proposal_status(
                "proposal-1",
                expected_status="proposed",
                new_status="applying",
            )
        )

        proposal = self.store.load_edit_proposal("proposal-1")
        self.assertEqual(proposal["status"], "applying")

    def test_wrong_expected_status_is_rejected(self):
        self.assertFalse(
            self.store.transition_edit_proposal_status(
                "proposal-1",
                expected_status="applied",
                new_status="applying",
            )
        )

        proposal = self.store.load_edit_proposal("proposal-1")
        self.assertEqual(proposal["status"], "proposed")

    def test_second_transition_cannot_claim_same_proposal(self):
        first = self.store.transition_edit_proposal_status(
            "proposal-1",
            expected_status="proposed",
            new_status="applying",
        )

        second = self.store.transition_edit_proposal_status(
            "proposal-1",
            expected_status="proposed",
            new_status="applying",
        )

        self.assertTrue(first)
        self.assertFalse(second)

        proposal = self.store.load_edit_proposal("proposal-1")
        self.assertEqual(proposal["status"], "applying")

    def test_transition_back_to_failed(self):
        self.assertTrue(
            self.store.transition_edit_proposal_status(
                "proposal-1",
                expected_status="proposed",
                new_status="applying",
            )
        )

        self.assertTrue(
            self.store.transition_edit_proposal_status(
                "proposal-1",
                expected_status="applying",
                new_status="failed",
            )
        )

        proposal = self.store.load_edit_proposal("proposal-1")
        self.assertEqual(proposal["status"], "failed")

    def test_applied_proposal_cannot_be_reclaimed(self):
        self.assertTrue(
            self.store.transition_edit_proposal_status(
                "proposal-1",
                expected_status="proposed",
                new_status="applying",
            )
        )

        self.assertTrue(
            self.store.transition_edit_proposal_status(
                "proposal-1",
                expected_status="applying",
                new_status="applied",
            )
        )

        self.assertFalse(
            self.store.transition_edit_proposal_status(
                "proposal-1",
                expected_status="proposed",
                new_status="applying",
            )
        )


if __name__ == "__main__":
    unittest.main()