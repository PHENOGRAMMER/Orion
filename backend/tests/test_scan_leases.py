"""
Unit tests for OrionPersistence scan-lease coordination.

Covers:
  - Successful first acquisition (vacant slot)
  - Collision: a second job cannot acquire while the first holds the lease
  - Idempotent re-acquisition by the same job returns True
  - Release by the owning job succeeds (returns True)
  - Release by a *different* job is a no-op (returns False)
  - After a valid release the slot is vacant again
"""

import tempfile
import threading
import unittest
from pathlib import Path

from app.core.persistence import OrionPersistence


class TestScanLeaseAcquire(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = OrionPersistence(Path(self._tmp.name) / "test.db")
        self.path = "/repo/my-project"

    def tearDown(self):
        self._tmp.cleanup()

    # ------------------------------------------------------------------
    # acquire
    # ------------------------------------------------------------------

    def test_first_acquire_succeeds(self):
        """Vacant slot: the first caller gets the lease."""
        self.assertTrue(self.db.acquire_scan_lease(self.path, "job-1"))

    def test_second_different_job_is_rejected(self):
        """While job-1 holds the lease, job-2 must be denied."""
        self.db.acquire_scan_lease(self.path, "job-1")
        self.assertFalse(self.db.acquire_scan_lease(self.path, "job-2"))

    def test_same_job_reacquire_is_idempotent(self):
        """Calling acquire with the *same* job_id is a no-op and returns True."""
        self.db.acquire_scan_lease(self.path, "job-1")
        self.assertTrue(self.db.acquire_scan_lease(self.path, "job-1"))

    def test_independent_paths_do_not_interfere(self):
        """Two different project paths each have their own independent lease."""
        self.assertTrue(self.db.acquire_scan_lease("/repo/alpha", "job-a"))
        self.assertTrue(self.db.acquire_scan_lease("/repo/beta", "job-b"))

    # ------------------------------------------------------------------
    # release
    # ------------------------------------------------------------------

    def test_release_by_owner_succeeds(self):
        self.db.acquire_scan_lease(self.path, "job-1")
        self.assertTrue(self.db.release_scan_lease(self.path, "job-1"))

    def test_release_by_non_owner_is_noop(self):
        """A different job_id must not be able to steal or drop the lease."""
        self.db.acquire_scan_lease(self.path, "job-1")
        self.assertFalse(self.db.release_scan_lease(self.path, "job-2"))

    def test_release_nonexistent_returns_false(self):
        """Releasing a lease that was never acquired returns False."""
        self.assertFalse(self.db.release_scan_lease(self.path, "job-99"))

    def test_slot_vacant_after_release(self):
        """After a valid release a new job can acquire the slot."""
        self.db.acquire_scan_lease(self.path, "job-1")
        self.db.release_scan_lease(self.path, "job-1")
        self.assertTrue(self.db.acquire_scan_lease(self.path, "job-2"))

    def test_slot_still_locked_after_wrong_release(self):
        """A failed release (wrong job_id) must not free the slot."""
        self.db.acquire_scan_lease(self.path, "job-1")
        self.db.release_scan_lease(self.path, "job-bad")
        # job-2 must still be blocked
        self.assertFalse(self.db.acquire_scan_lease(self.path, "job-2"))


class TestScanLeaseConcurrency(unittest.TestCase):
    """
    Smoke-test the atomic guarantee under concurrent threads.

    N threads all try to acquire the same lease simultaneously; exactly
    one must succeed.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = OrionPersistence(Path(self._tmp.name) / "test.db")

    def tearDown(self):
        self._tmp.cleanup()

    def test_exactly_one_winner_under_contention(self):
        path = "/repo/shared"
        n_threads = 20
        winners: list[int] = []
        lock = threading.Lock()

        def try_acquire(i: int) -> None:
            got = self.db.acquire_scan_lease(path, f"job-{i}")
            if got:
                with lock:
                    winners.append(i)

        threads = [threading.Thread(target=try_acquire, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(
            len(winners),
            1,
            f"Expected exactly 1 winner, got {len(winners)}: {winners}",
        )


if __name__ == "__main__":
    unittest.main()
