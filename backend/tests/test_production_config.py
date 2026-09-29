from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.core.config import Settings


class ProductionConfigTests(unittest.TestCase):
    def test_auth_can_be_enabled_from_environment(self):
        with patch.dict(
            os.environ,
            {
                "AUTH_ENABLED": "true",
            },
            clear=False,
        ):
            settings = Settings()

        self.assertTrue(settings.AUTH_ENABLED)

    def test_auth_can_be_disabled_for_local_development(self):
        with patch.dict(
            os.environ,
            {
                "AUTH_ENABLED": "false",
            },
            clear=False,
        ):
            settings = Settings()

        self.assertFalse(settings.AUTH_ENABLED)

    def test_default_allowed_root_is_not_filesystem_root(self):
        settings = Settings()

        roots = settings.allowed_roots

        self.assertTrue(roots)

        for root in roots:
            self.assertNotEqual(
                root.anchor,
                root,
                msg=f"Unexpected filesystem-root permission: {root}",
            )

    def test_cors_is_explicit(self):
        settings = Settings()

        origins = settings.allow_origins

        self.assertIsInstance(origins, list)

        for origin in origins:
            self.assertNotEqual(origin, "*")

    def test_admin_api_key_is_not_logged_or_serialized(self):
        secret = "ob_live_test_secret_123"

        with patch.dict(
            os.environ,
            {
                "ADMIN_API_KEY": secret,
            },
            clear=False,
        ):
            settings = Settings()

        self.assertEqual(settings.ADMIN_API_KEY, secret)

        representation = repr(settings)

        self.assertNotIn(secret, representation)


if __name__ == "__main__":
    unittest.main()