"""
Authentication and authorization for Orion.

Provides API-key based auth with role-based access control.

Roles
-----
- ``admin``  – full access: scans, agent edits, key management.
- ``viewer`` – read-only: graph queries, LLM inference.

When ``AUTH_ENABLED`` is ``False`` (the default for local dev), every request
is treated as an authenticated admin.  This keeps the single-developer workflow
zero-config while the production path is fully wired.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request

# ── Role constants ────────────────────────────────────────────────────────────

ROLE_ADMIN = "admin"
ROLE_VIEWER = "viewer"
ROLE_MEMBER = "member"

ALL_ROLES = {ROLE_ADMIN, ROLE_VIEWER}

# Role hierarchy: admin implies viewer.
_ROLE_HIERARCHY: dict[str, set[str]] = {
    ROLE_ADMIN: {ROLE_ADMIN, ROLE_MEMBER, ROLE_VIEWER},
    ROLE_MEMBER: {ROLE_MEMBER, ROLE_VIEWER},
    ROLE_VIEWER: {ROLE_VIEWER},
}


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class User:
    """Minimal identity carried through the request lifecycle."""

    key_id: str
    name: str
    role: str
    user_id: str | None = None
    email: str | None = None
    provider: str | None = None
    picture: str | None = None

    def has_role(self, required: str) -> bool:
        """Check whether this user's role grants the *required* permission."""
        implied = _ROLE_HIERARCHY.get(self.role, set())
        return required in implied


# Sentinel for "auth is off, treat as admin".
_ANONYMOUS_ADMIN = User(key_id="__anonymous__", name="anonymous", role=ROLE_ADMIN)


# ── API key helpers ───────────────────────────────────────────────────────────

# Keys look like  ``ob_live_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX``
_KEY_PREFIX = "ob_live_"
_KEY_BYTES = 32  # 256 bits of entropy


def generate_api_key() -> str:
    """Return a new, cryptographically random API key string."""
    return _KEY_PREFIX + secrets.token_urlsafe(_KEY_BYTES)


def hash_key(raw_key: str) -> str:
    """
    One-way hash for storage.

    Only Orion-generated API keys are accepted. The plaintext key is
    never persisted.
    """
    import hashlib

    if not raw_key.startswith(_KEY_PREFIX):
        raise ValueError("Invalid API key format.")

    bare = raw_key[len(_KEY_PREFIX):]

    if not bare:
        raise ValueError("Invalid API key format.")

    return hashlib.sha256(bare.encode("utf-8")).hexdigest()


def verify_key(raw_key: str, stored_hash: str) -> bool:
    """Constant-time comparison of a raw key against a stored hash."""
    if not raw_key.startswith(_KEY_PREFIX):
        return False

    try:
        candidate_hash = hash_key(raw_key)
    except ValueError:
        return False

    return secrets.compare_digest(candidate_hash, stored_hash)


def key_id_from_hash(hashed: str) -> str:
    """Derive a short, stable key id from the stored hash (first 8 hex chars)."""
    return hashed[:8]


# ── FastAPI dependency ────────────────────────────────────────────────────────

async def _get_current_user(request: Request) -> User:
    """
    Extract and validate the ``X-API-Key`` header.

    When ``AUTH_ENABLED`` is ``False``, returns the anonymous admin user
    without checking anything.
    """
    from app.core.config import settings
    from app.core.logging import get_logger

    log = get_logger("auth")

    if not settings.AUTH_ENABLED and not settings.AUTH0_ENABLED:
        return _ANONYMOUS_ADMIN

    if settings.AUTH0_ENABLED:
        bridge_user = _user_from_identity_bridge(request)
        if bridge_user is not None:
            store = getattr(request.app.state, "persistence", None)
            if store is not None:
                try:
                    store.upsert_user(
                        user_id=bridge_user.user_id or bridge_user.key_id,
                        provider=bridge_user.provider or "auth0",
                        email=bridge_user.email,
                        name=bridge_user.name,
                        picture=bridge_user.picture,
                    )
                except Exception as exc:
                    log.warning("Failed to persist Auth0 user profile", extra={"error": str(exc)})
            return bridge_user

        if not settings.AUTH_ENABLED:
            raise HTTPException(status_code=401, detail="Missing or invalid Auth0 identity.")

    raw_key = request.headers.get("x-api-key")
    if not raw_key:
        log.warning("Authentication failed: Missing X-API-Key header", extra={"path": request.url.path})
        raise HTTPException(
            status_code=401,
            detail="Missing X-API-Key header.",
        )

    store = getattr(request.app.state, "persistence", None)
    if store is None:
        log.error("Authentication error: Auth store unavailable", extra={"path": request.url.path})
        raise HTTPException(
            status_code=503,
            detail="Auth store unavailable.",
        )

    # Allow keys with or without ob_live_ prefix
    candidate = raw_key if raw_key.startswith(_KEY_PREFIX) else f"{_KEY_PREFIX}{raw_key}"
    row = store.lookup_api_key(candidate)
    if row is None and candidate != raw_key:
        row = store.lookup_api_key(raw_key)

    if row is None:
        log.warning(
            "Authentication failed: Invalid or revoked API key",
            extra={"path": request.url.path, "key_prefix": raw_key[:10]},
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid or revoked API key.",
        )

    return User(
        key_id=row["key_id"],
        name=row["name"],
        role=row["role"],
    )


def _user_from_identity_bridge(request: Request) -> User | None:
    """Validate the signed identity assertion emitted by the Streamlit BFF."""
    from app.core.config import settings

    secret = (settings.ORION_IDENTITY_BRIDGE_SECRET or "").strip()
    encoded = request.headers.get("x-orion-identity", "")
    supplied_signature = request.headers.get("x-orion-identity-signature", "")
    if not secret or not encoded or not supplied_signature:
        return None

    try:
        raw = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        expected = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, supplied_signature):
            return None
        identity = json.loads(raw.decode("utf-8"))
        issued_at = float(identity.get("iat", 0))
        if abs(time.time() - issued_at) > settings.ORION_IDENTITY_BRIDGE_MAX_AGE_SECONDS:
            return None
        user_id = str(identity.get("sub", "")).strip()
        if not user_id or len(user_id) > 512:
            return None
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    provider = user_id.split("|", 1)[0] if "|" in user_id else "auth0"
    return User(
        key_id=user_id,
        user_id=user_id,
        name=str(identity.get("name") or identity.get("email") or user_id),
        email=str(identity.get("email")) if identity.get("email") else None,
        provider=provider,
        picture=str(identity.get("picture")) if identity.get("picture") else None,
        role=ROLE_MEMBER,
    )


# Type alias used in route signatures.
CurrentUser = Annotated[User, Depends(_get_current_user)]


def require_role(role: str):
    """
    Return a dependency that asserts the caller has *role*.

    Usage::

        @router.post("/scan", dependencies=[Depends(require_role(ROLE_ADMIN))])
        async def start_scan(...):
            ...
    """
    async def _check(user: CurrentUser) -> User:
        if not user.has_role(role):
            raise HTTPException(
                status_code=403,
                detail=f"Required role: {role}. Your role: {user.role}.",
            )
        return user

    return _check


# Pre-built dependency for the common admin-only guard.
# Usage:  async def my_route(_user: CurrentUser = Depends(require_admin)): ...
require_admin = require_role(ROLE_ADMIN)
