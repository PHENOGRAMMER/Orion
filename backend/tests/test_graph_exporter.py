import json
import os
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.graph_exporter import router
from app.core.config import settings
from unittest.mock import patch

class TestGraphExporter(unittest.TestCase):
    def setUp(self):
        self.auth_patcher = patch("app.core.config.settings.AUTH_ENABLED", False)
        self.auth_patcher.start()
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)
        
        # We need a dummy graph state in app.state to make the endpoint work
        class DummyGraph:
            nodes = {"n1": {"type": "file", "file": "foo.py"}}
            edges = [{"src": "n1", "dst": "n1", "type": "calls"}]
        
        class DummyState:
            graph = DummyGraph()

        self.app.state.graph_state = DummyState()
        
        # Override project root to a temporary directory so exports don't pollute the real workspace
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_project_root = settings.PROJECT_ROOT
        settings.PROJECT_ROOT = self.temp_dir.name
        
    def tearDown(self):
        self.auth_patcher.stop()
        settings.PROJECT_ROOT = self.original_project_root
        self.temp_dir.cleanup()

    def test_export_download_true_returns_inline(self):
        response = self.client.get("/export?download=true")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("nodes", data)
        self.assertIn("edges", data)

    def test_export_rejects_parent_traversal(self):
        response = self.client.get("/export?output=../../outside.json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("output must be a filename, not a path", response.json()["error"])

    def test_export_rejects_subdirectory(self):
        response = self.client.get("/export?output=subdir/file.json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("output must be a filename, not a path", response.json()["error"])

    def test_export_rejects_absolute_path_unix(self):
        response = self.client.get("/export?output=/tmp/file.json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("output must be a filename, not a path", response.json()["error"])

    def test_export_rejects_absolute_path_windows(self):
        response = self.client.get("/export?output=C:\\temp\\file.json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("output must be a filename, not a path", response.json()["error"])

    def test_export_rejects_symlink(self):
        export_dir = Path(settings.PROJECT_ROOT) / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        symlink_path = export_dir / "link.json"
        target_path = export_dir / "target.json"
        target_path.write_text("{}")
        
        try:
            os.symlink(target_path, symlink_path)
        except OSError:
            # Symlinks might require admin privileges on Windows. Skip if we can't create one.
            self.skipTest("Cannot create symlinks on this OS/user")
            
        response = self.client.get("/export?output=link.json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("output file cannot be a symlink", response.json()["error"])

    def test_export_succeeds_inside_exports(self):
        response = self.client.get("/export?output=graph.json")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("saved_to", data)
        self.assertIn("nodes", data)
        self.assertIn("edges", data)
        
        expected_path = Path(settings.PROJECT_ROOT) / "exports" / "graph.json"
        self.assertTrue(expected_path.exists())
        self.assertEqual(str(expected_path.resolve()), data["saved_to"])
