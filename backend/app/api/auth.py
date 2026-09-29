"""
API key management endpoints.

All endpoints here require the ``admin`` role.  They are mounted under
``/auth`` in ``main.py``.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.auth import (
    CurrentUser,
    ROLE_ADMIN,
    generate_api_key,
    hash_key,
    key_id_from_hash,
    require_role,
)
from app.core.persistence import OrionPersistence

router = APIRouter(tags=["Auth"])


# ── Request / response models ─────────────────────────────────────────────────

class CreateKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Human-readable label")
    role: str = Field(
        "viewer",
        description="Permission level: 'admin' or 'viewer'",
    )


class CreateKeyResponse(BaseModel):
    key_id: str
    name: str
    role: str
    api_key: str  # Only shown once at creation time.
    created_at: str


class KeyRecord(BaseModel):
    key_id: str
    name: str
    role: str
    revoked: bool
    created_at: str
    last_used_at: str | None


class ListKeysResponse(BaseModel):
    count: int
    keys: list[KeyRecord]


class RevokeKeyResponse(BaseModel):
    key_id: str
    revoked: bool
    detail: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_store(request) -> OrionPersistence:
    store: OrionPersistence | None = getattr(request.app.state, "persistence", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Persistence store unavailable.")
    return store


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "/keys",
    response_model=CreateKeyResponse,
    status_code=201,
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def create_key(
    body: CreateKeyRequest,
    request: Request,
    _user: CurrentUser,
):
    """
    Generate a new API key and return it exactly once.

    The plaintext key is **never stored** — only its SHA-256 hash is
    persisted.  Copy the ``api_key`` value from the response now; it
    cannot be retrieved later.
    """
    from app.core.auth import ALL_ROLES

    if body.role not in ALL_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role '{body.role}'. Allowed: {sorted(ALL_ROLES)}",
        )

    store = _get_store(request)
    raw_key = generate_api_key()
    hashed = hash_key(raw_key)
    kid = key_id_from_hash(hashed)

    record = store.create_api_key(
        key_id=kid,
        name=body.name,
        key_hash=hashed,
        role=body.role,
    )

    store.record_audit_event(
        event_id=uuid.uuid4().hex,
        action="auth.key_created",
        status="success",
        actor_key_id=_user.key_id,
        actor_name=_user.name,
        actor_role=_user.role,
        resource_type="api_key",
        resource_id=record["key_id"],
        details={
            "name": record["name"],
            "role": record["role"],
        },
    )

    return CreateKeyResponse(
        key_id=record["key_id"],
        name=record["name"],
        role=record["role"],
        api_key=raw_key,
        created_at=record["created_at"],
    )


@router.get(
    "/keys",
    response_model=ListKeysResponse,
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def list_keys(request: Request):
    """
    List all registered API keys (revoked keys are included).
    """
    store = _get_store(request)
    keys = store.list_api_keys()
    return ListKeysResponse(count=len(keys), keys=keys)


@router.delete(
    "/keys/{key_id}",
    response_model=RevokeKeyResponse,
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def revoke_key(
    key_id: str,
    request: Request,
    _user: CurrentUser,
):
    """
    Revoke an API key.  The key cannot be used after revocation.
    """
    if key_id == _user.key_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot revoke the API key used for the current request.",
        )

    store = _get_store(request)
    existed = store.revoke_api_key(key_id)

    if not existed:
        raise HTTPException(status_code=404, detail=f"Unknown key: {key_id}")

    store.record_audit_event(
        event_id=uuid.uuid4().hex,
        action="auth.key_revoked",
        status="success",
        actor_key_id=_user.key_id,
        actor_name=_user.name,
        actor_role=_user.role,
        resource_type="api_key",
        resource_id=key_id,
    )

    return RevokeKeyResponse(
        key_id=key_id,
        revoked=True,
        detail="Key has been revoked.",
    )
