"""Smoke test for the FastAPI application module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class AppImportTests(unittest.TestCase):

    def test_app_imports(self):
        from app.main import app

        self.assertEqual(app.title, "Orion")


if __name__ == "__main__":
    unittest.main(verbosity=2)
