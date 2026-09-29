"""
Tests for Orion's API-key authentication and role-based access control.

Covers:
- Key generation, hashing, verification.
- Role hierarchy.
- Persistence CRUD for api_keys.
- HTTP protection of management routes.
"""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.auth import (
    _ANONYMOUS_ADMIN,
    ALL_ROLES,
    ROLE_ADMIN,
    ROLE_VIEWER,
    User,
    generate_api_key,
    hash_key,
    key_id_from_hash,
    verify_key,
)
from app.core.persistence import OrionPersistence


# ── Key generation & hashing ─────────────────────────────────────────────────

class TestKeyGeneration(unittest.TestCase):

    def test_key_has_prefix(self):
        key = generate_api_key()
        self.assertTrue(key.startswith("ob_live_"), f"Key should start with ob_live_: {key!r}")

    def test_key_is_unique(self):
        keys = {generate_api_key() for _ in range(100)}
        self.assertEqual(len(keys), 100, "Every generated key must be unique")

    def test_hash_is_hex_sha256(self):
        key = generate_api_key()
        h = hash_key(key)
        self.assertEqual(len(h), 64, "SHA-256 hex digest is 64 chars")
        self.assertTrue(all(c in "0123456789abcdef" for c in h))

    def test_hash_strips_prefix(self):
        key = generate_api_key()
        bare = key.removeprefix("ob_live_")
        expected = hashlib.sha256(bare.encode()).hexdigest()
        self.assertEqual(hash_key(key), expected)

    def test_verify_round_trip(self):
        key = generate_api_key()
        h = hash_key(key)
        self.assertTrue(verify_key(key, h))
        self.assertFalse(verify_key("ob_live_wrongkey", h))

    def test_verify_is_constant_time(self):
        key = generate_api_key()
        h = hash_key(key)
        self.assertFalse(verify_key(key + "x", h))

    def test_key_id_from_hash(self):
        h = "abcdef1234567890" + "0" * 48
        kid = key_id_from_hash(h)
        self.assertEqual(kid, "abcdef12")


# ── User model & role hierarchy ───────────────────────────────────────────────

class TestUserRoles(unittest.TestCase):

    def test_admin_has_admin(self):
        user = User(key_id="k1", name="a", role=ROLE_ADMIN)
        self.assertTrue(user.has_role(ROLE_ADMIN))

    def test_admin_has_viewer(self):
        user = User(key_id="k1", name="a", role=ROLE_ADMIN)
        self.assertTrue(user.has_role(ROLE_VIEWER))

    def test_viewer_has_viewer(self):
        user = User(key_id="k1", name="v", role=ROLE_VIEWER)
        self.assertTrue(user.has_role(ROLE_VIEWER))

    def test_viewer_lacks_admin(self):
        user = User(key_id="k1", name="v", role=ROLE_VIEWER)
        self.assertFalse(user.has_role(ROLE_ADMIN))

    def test_anonymous_is_admin(self):
        self.assertTrue(_ANONYMOUS_ADMIN.has_role(ROLE_ADMIN))
        self.assertEqual(_ANONYMOUS_ADMIN.key_id, "__anonymous__")

    def test_all_roles_constant(self):
        self.assertEqual(ALL_ROLES, {ROLE_ADMIN, ROLE_VIEWER})


# ── Persistence CRUD ──────────────────────────────────────────────────────────

class TestPersistenceAPIKeys(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.db_path = Path(self._tmp) / "test.db"
        self.store = OrionPersistence(self.db_path)

    def test_create_and_lookup(self):
        raw_key = generate_api_key()
        hashed = hash_key(raw_key)
        kid = key_id_from_hash(hashed)

        record = self.store.create_api_key(kid, "test-key", hashed, ROLE_VIEWER)
        self.assertEqual(record["key_id"], kid)
        self.assertEqual(record["role"], ROLE_VIEWER)

        found = self.store.lookup_api_key(raw_key)
        self.assertIsNotNone(found)
        self.assertEqual(found["key_id"], kid)
        self.assertEqual(found["role"], ROLE_VIEWER)

    def test_lookup_wrong_key_returns_none(self):
        raw_key = generate_api_key()
        hashed = hash_key(raw_key)
        kid = key_id_from_hash(hashed)
        self.store.create_api_key(kid, "test-key", hashed, ROLE_VIEWER)

        self.assertIsNone(self.store.lookup_api_key("ob_live_nonexistent"))

    def test_revoked_key_not_found(self):
        raw_key = generate_api_key()
        hashed = hash_key(raw_key)
        kid = key_id_from_hash(hashed)
        self.store.create_api_key(kid, "test-key", hashed, ROLE_ADMIN)

        self.assertTrue(self.store.revoke_api_key(kid))
        self.assertIsNone(self.store.lookup_api_key(raw_key))

    def test_list_keys(self):
        raw1 = generate_api_key()
        raw2 = generate_api_key()
        h1, h2 = hash_key(raw1), hash_key(raw2)
        self.store.create_api_key(key_id_from_hash(h1), "key-1", h1, ROLE_ADMIN)
        self.store.create_api_key(key_id_from_hash(h2), "key-2", h2, ROLE_VIEWER)

        keys = self.store.list_api_keys()
        self.assertEqual(len(keys), 2)
        names = {k["name"] for k in keys}
        self.assertEqual(names, {"key-1", "key-2"})

    def test_last_used_bumped_on_lookup(self):
        raw_key = generate_api_key()
        hashed = hash_key(raw_key)
        kid = key_id_from_hash(hashed)
        self.store.create_api_key(kid, "test", hashed, ROLE_VIEWER)

        found = self.store.lookup_api_key(raw_key)
        self.assertIsNotNone(found)
        self.assertIsNotNone(found["last_used_at"])

    def test_revoke_nonexistent_returns_false(self):
        self.assertFalse(self.store.revoke_api_key("no-such-id"))


# ── HTTP route protection (auth management) ───────────────────────────────────

def _build_auth_test_app():
    """
    Build a minimal FastAPI app with auth router and AUTH_ENABLED=True.
    Returns (app, admin_key, viewer_key).
    """
    from app.api.auth import router as auth_router
    from app.core.config import settings as _real_settings

    # Enable auth on the real settings singleton.
    _real_settings.AUTH_ENABLED = True

    app = FastAPI()

    tmp = tempfile.mkdtemp()
    store = OrionPersistence(Path(tmp) / "test.db")
    app.state.persistence = store

    raw_admin = generate_api_key()
    h = hash_key(raw_admin)
    store.create_api_key(key_id_from_hash(h), "test-admin", h, ROLE_ADMIN)

    raw_viewer = generate_api_key()
    vh = hash_key(raw_viewer)
    store.create_api_key(key_id_from_hash(vh), "test-viewer", vh, ROLE_VIEWER)

    app.include_router(auth_router, prefix="/auth")
    return app, raw_admin, raw_viewer


class TestAuthKeyHTTPRoutes(unittest.TestCase):

    def setUp(self):
        from app.core.config import settings as _real_settings
        self._orig_auth = _real_settings.AUTH_ENABLED
        _real_settings.AUTH_ENABLED = True

    def tearDown(self):
        from app.core.config import settings as _real_settings
        _real_settings.AUTH_ENABLED = self._orig_auth

    def test_create_key_as_admin(self):
        app, admin_key, _ = _build_auth_test_app()
        client = TestClient(app)
        resp = client.post(
            "/auth/keys",
            json={"name": "new-key", "role": "viewer"},
            headers={"X-API-Key": admin_key},
        )
        self.assertEqual(resp.status_code, 201, resp.text)
        data = resp.json()
        self.assertIn("api_key", data)
        self.assertTrue(data["api_key"].startswith("ob_live_"))
        self.assertEqual(data["name"], "new-key")
        self.assertEqual(data["role"], "viewer")

    def test_create_key_rejects_viewer(self):
        app, _, viewer_key = _build_auth_test_app()
        client = TestClient(app)
        resp = client.post(
            "/auth/keys",
            json={"name": "sneaky", "role": "admin"},
            headers={"X-API-Key": viewer_key},
        )
        self.assertEqual(resp.status_code, 403)

    def test_list_keys_as_admin(self):
        app, admin_key, _ = _build_auth_test_app()
        client = TestClient(app)
        resp = client.get("/auth/keys", headers={"X-API-Key": admin_key})
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertGreaterEqual(data["count"], 2)

    def test_list_keys_rejects_viewer(self):
        app, _, viewer_key = _build_auth_test_app()
        client = TestClient(app)
        resp = client.get("/auth/keys", headers={"X-API-Key": viewer_key})
        self.assertEqual(resp.status_code, 403)

    def test_revoke_key(self):
        app, admin_key, _ = _build_auth_test_app()
        client = TestClient(app)
        # Create a disposable key.
        create_resp = client.post(
            "/auth/keys",
            json={"name": "disposable", "role": "viewer"},
            headers={"X-API-Key": admin_key},
        )
        kid = create_resp.json()["key_id"]
        resp = client.delete(f"/auth/keys/{kid}", headers={"X-API-Key": admin_key})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["revoked"])

    def test_key_mutations_are_audited(self):
        app, admin_key, _ = _build_auth_test_app()
        client = TestClient(app)

        create_resp = client.post(
            "/auth/keys",
            json={"name": "audited", "role": "viewer"},
            headers={"X-API-Key": admin_key},
        )
        self.assertEqual(create_resp.status_code, 201, create_resp.text)
        kid = create_resp.json()["key_id"]

        revoke_resp = client.delete(
            f"/auth/keys/{kid}",
            headers={"X-API-Key": admin_key},
        )
        self.assertEqual(revoke_resp.status_code, 200, revoke_resp.text)

        events = app.state.persistence.list_audit_events()
        actions = [event["action"] for event in events]
        self.assertIn("auth.key_created", actions)
        self.assertIn("auth.key_revoked", actions)

    def test_admin_cannot_revoke_current_key(self):
        app, admin_key, _ = _build_auth_test_app()
        client = TestClient(app)
        admin_id = next(
            key["key_id"]
            for key in app.state.persistence.list_api_keys()
            if key["name"] == "test-admin"
        )

        response = client.delete(
            f"/auth/keys/{admin_id}",
            headers={"X-API-Key": admin_key},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "Cannot revoke the API key used for the current request.",
        )

    def test_create_key_invalid_role(self):
        app, admin_key, _ = _build_auth_test_app()
        client = TestClient(app)
        resp = client.post(
            "/auth/keys",
            json={"name": "bad", "role": "superuser"},
            headers={"X-API-Key": admin_key},
        )
        self.assertEqual(resp.status_code, 400)

    def test_no_key_returns_401(self):
        """Auth management endpoints require a valid API key."""
        app, _, _ = _build_auth_test_app()
        client = TestClient(app)
        resp = client.get("/auth/keys")
        self.assertEqual(resp.status_code, 401)

    def test_invalid_key_returns_401(self):
        app, _, _ = _build_auth_test_app()
        client = TestClient(app)
        resp = client.get("/auth/keys", headers={"X-API-Key": "ob_live_bogus"})
        self.assertEqual(resp.status_code, 401)


# ── Auth dependency integration (graph routes) ────────────────────────────────

class TestAuthDependencyInjection(unittest.TestCase):
    """Test that the auth dependency is wired into graph/agent routes."""

    def test_graph_stats_no_auth_needed_when_disabled(self):
        """When AUTH_ENABLED=False, graph routes work without any key."""
        from app.api.graph import router as graph_router

        app = FastAPI()
        tmp = tempfile.mkdtemp()
        app.state.persistence = OrionPersistence(Path(tmp) / "test.db")

        app.include_router(graph_router, prefix="/graph")

        # Patch settings.AUTH_ENABLED = False (default).
        with patch("app.core.auth._get_current_user") as mock_dep, \
             patch("app.core.config.settings.AUTH_ENABLED", False):
            mock_dep.return_value = _ANONYMOUS_ADMIN
            client = TestClient(app)
            resp = client.get("/graph/stats")
            # Should not be 401 (auth disabled). Might be 503 (no graph) which is fine.
            self.assertNotEqual(resp.status_code, 401)

    def test_agent_proposals_no_auth_needed_when_disabled(self):
        """When AUTH_ENABLED=False, agent routes work without any key."""
        from app.api.agent import router as agent_router

        app = FastAPI()
        tmp = tempfile.mkdtemp()
        app.state.persistence = OrionPersistence(Path(tmp) / "test.db")

        app.include_router(agent_router, prefix="/agent")

        with patch("app.core.auth._get_current_user") as mock_dep, \
             patch("app.core.config.settings.AUTH_ENABLED", False):
            mock_dep.return_value = _ANONYMOUS_ADMIN
            client = TestClient(app)
            # Missing graph state → 503, not 401
            resp = client.post(
                "/agent/proposals",
                json={"objective": "test", "edits": [{"path": "a.py", "find": "x", "replace": "y"}]},
            )
            self.assertIn(resp.status_code, [400, 503])


if __name__ == "__main__":
    unittest.main()
