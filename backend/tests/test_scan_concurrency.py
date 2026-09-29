from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.api import graph


class ScanConcurrencyTests(unittest.TestCase):
    def setUp(self):
        # Reset the module-level scan guard before every test so tests
        # are fully independent of each other's final state.
        graph._scan_active = False

    def test_second_scan_is_rejected_while_first_scan_is_running(self):
        async def run_test():
            app = SimpleNamespace(
                state=SimpleNamespace(
                    graph_state=None,
                    persistence=None,
                )
            )

            request = SimpleNamespace(app=app)

            with patch("app.api.graph.safe_directory") as safe_directory, \
                 patch("app.api.graph.asyncio.get_running_loop") as get_loop:

                safe_directory.side_effect = lambda path, roots: path

                class FakeLoop:
                    def run_in_executor(self, *args):
                        return None

                get_loop.return_value = FakeLoop()

                body_a = graph.ScanRequest(path="/project-a")
                body_b = graph.ScanRequest(path="/project-b")

                first = await graph.start_scan(
                    body_a,
                    request=request,
                    _user=None,
                )

                self.assertEqual(first.status, "pending")

                with self.assertRaises(HTTPException) as ctx:
                    await graph.start_scan(
                        body_b,
                        request=request,
                        _user=None,
                    )

                self.assertEqual(ctx.exception.status_code, 409)

        asyncio.run(run_test())

    def test_new_scan_is_allowed_after_previous_scan_finishes(self):
        async def run_test():
            app = SimpleNamespace(
                state=SimpleNamespace(
                    graph_state=None,
                    persistence=None,
                )
            )

            request = SimpleNamespace(app=app)

            with patch("app.api.graph.safe_directory") as safe_directory, \
                 patch("app.api.graph.asyncio.get_running_loop") as get_loop:

                safe_directory.side_effect = lambda path, roots: path

                class FakeFuture:
                    pass

                class FakeLoop:
                    def run_in_executor(self, *args):
                        return FakeFuture()

                get_loop.return_value = FakeLoop()

                body_a = graph.ScanRequest(path="/project-a")
                body_b = graph.ScanRequest(path="/project-b")

                first = await graph.start_scan(
                    body_a,
                    request=request,
                    _user=None,
                )

                self.assertEqual(first.status, "pending")

                # Simulate completion of the first scan.
                graph._scan_active = False

                second = await graph.start_scan(
                    body_b,
                    request=request,
                    _user=None,
                )

                self.assertEqual(second.status, "pending")

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()