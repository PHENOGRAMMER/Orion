"""
Agent edit workflow API.

These endpoints implement production-v1's supervised write path:
create a proposal, review the diff, then apply it and run validation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.agent.workflow import AgentWorkflow, AgentWorkflowError, TextEdit
from app.core import graph_state
from app.core.auth import CurrentUser, ROLE_ADMIN, require_role
from app.core.persistence import OrionPersistence


router = APIRouter(tags=["Agent"])


class TextEditIn(BaseModel):
    path: str
    find: str = Field(..., min_length=1)
    replace: str


class ProposalRequest(BaseModel):
    objective: str = Field(..., min_length=1)
    edits: list[TextEditIn] = Field(..., min_length=1)
    validation: Literal["backend-tests", "pytest"] = "backend-tests"
    test_paths: list[str] | None = Field(
        None,
        description="Optional list of test file paths to run (only used when validation='pytest')",
    )


class ApplyRequest(BaseModel):
    approved: bool


def _get_project_root(request: Request) -> Path:
    state = graph_state.current(request.app.state)
    if state is None:
        raise HTTPException(
            status_code=503,
            detail="No active project graph. Scan a project before creating edit proposals.",
        )

    return Path(state.project_path).resolve()


def _workflow(request: Request) -> AgentWorkflow:
    store: OrionPersistence | None = getattr(request.app.state, "persistence", None)
    return AgentWorkflow(store)


@router.get(
    "/proposals",
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def list_proposals(
    request: Request,
    _user: CurrentUser,
    status: str | None = None,
    limit: int = 50,
):
    """
    List edit proposals, newest first.

    Optional query params:
    - ``status``: filter by status (``proposed``, ``applying``, ``applied``, ``failed``)
    - ``limit``: max results (1–200, default 50)
    """
    store: OrionPersistence | None = getattr(request.app.state, "persistence", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Persistence store unavailable.")

    proposals = store.list_edit_proposals(status=status, limit=limit)
    return {"count": len(proposals), "proposals": proposals}


@router.post(
    "/proposals",
    status_code=201,
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def create_proposal(body: ProposalRequest, request: Request, _user: CurrentUser):
    """
    Create a durable edit proposal and return its reviewable diff.
    """
    workflow = _workflow(request)
    edits = [
        TextEdit(path=edit.path, find=edit.find, replace=edit.replace)
        for edit in body.edits
    ]

    try:
        return workflow.create_proposal(
            project_root=_get_project_root(request),
            objective=body.objective,
            edits=edits,
            validation=body.validation,
            test_paths=body.test_paths,
            actor=_user,
        )
    except AgentWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/proposals/{proposal_id}",
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def get_proposal(proposal_id: str, request: Request, _user: CurrentUser):
    """
    Return a previously created proposal.
    """
    proposal = _workflow(request).load_proposal(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail=f"Unknown proposal: {proposal_id}")
    return proposal


@router.post(
    "/proposals/{proposal_id}/apply",
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def apply_proposal(proposal_id: str, body: ApplyRequest, request: Request, _user: CurrentUser):
    """
    Apply an approved proposal and run its validation command.
    """
    if not body.approved:
        raise HTTPException(status_code=400, detail="Proposal apply requires approved=true.")

    try:
        return _workflow(request).apply_proposal(
            proposal_id,
            actor=_user,
        )
    except AgentWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/audit",
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def list_audit_events(
    request: Request,
    _user: CurrentUser,
    limit: int = 100,
):
    """
    Return recent audit events (scan, proposal, auth actions), newest first.

    Admin-only. Capped at 1000 per call.
    """
    store: OrionPersistence | None = getattr(request.app.state, "persistence", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Persistence store unavailable.")

    events = store.list_audit_events(limit=limit)
    return {"count": len(events), "events": events}

