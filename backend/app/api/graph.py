"""
Knowledge Graph API endpoints.

All routes read the live :class:`GraphState` snapshot published on
``app.state`` by the startup scan or ``POST /graph/scan``.

Route order matters in this module — see the note above the /symbol routes.
"""

from __future__ import annotations

import asyncio
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.core import graph_state
from app.core.auth import CurrentUser, ROLE_MEMBER, require_role
from app.core.config import settings
from app.core.persistence import OrionPersistence
from app.core.paths import PathNotAllowed, safe_directory
from app.core.logging import get_logger

router = APIRouter(tags=["Graph"])

#
# Scan job registry. Bounded because it is keyed by a fresh UUID per scan and
# would otherwise grow for the lifetime of the process.
#
_jobs: "OrderedDict[str, dict]" = OrderedDict()
_MAX_JOBS = 50
_scan_lock = asyncio.Lock()
_scan_active = False
_log = get_logger("graph")


# ------------------------------------------------------------------
# Response models
# ------------------------------------------------------------------

class NodeOut(BaseModel):
    id: str
    type: str
    name: str
    qualified_name: str | None
    module: str | None = None
    file: str | None
    line: int | None


class SymbolResponse(BaseModel):
    symbol: NodeOut | None
    callers: list[NodeOut]
    callees: list[NodeOut]


class ImpactResponse(BaseModel):
    symbol: NodeOut | None
    direct_callers: list[NodeOut]
    all_callers: list[NodeOut]
    affected_modules: list[str]
    affected_files: list[str]
    direct_count: int
    total_count: int


class PathResponse(BaseModel):
    from_symbol: str
    to_symbol: str
    path: list[str] | None
    reachable: bool


class TopSymbol(BaseModel):
    qualified_name: str
    type: str
    count: int


class StatsResponse(BaseModel):
    nodes: int
    edges: int
    by_node_type: dict[str, int]
    by_edge_type: dict[str, int]
    top_called: list[TopSymbol]
    top_callers: list[TopSymbol]
    project_path: str | None = None
    symbols_indexed: int = 0


class SearchResult(BaseModel):
    qualified_name: str
    name: str
    type: str
    module: str | None = None
    file: str | None = None
    line: int | None = None


class SearchResponse(BaseModel):
    query: str
    count: int
    results: list[SearchResult]


class ScanRequest(BaseModel):
    path: str


class ScanStatus(BaseModel):
    job_id: str
    status: Literal["pending", "running", "done", "error"]
    message: str
    stats: StatsResponse | None = None


class BrowseEntry(BaseModel):
    name: str
    path: str
    is_dir: bool


class BrowseResponse(BaseModel):
    current: str
    parent: str | None
    entries: list[BrowseEntry]
    allowed_roots: list[str] = []


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _node_out(node) -> NodeOut | None:
    if node is None:
        return None

    return NodeOut(
        id=node.id,
        type=node.type.value,
        name=node.name,
        qualified_name=node.qualified_name,
        module=node.module,
        file=str(node.path) if node.path else None,
        line=node.line,
    )


def _owner_id(user: CurrentUser | None) -> str:
    return getattr(user, "user_id", None) or "__legacy__"


def _get_state(
    request: Request,
    user: CurrentUser | None = None,
) -> graph_state.GraphState:
    """
    The live graph snapshot, or 503 when nothing has been analysed yet.
    """
    owner_id = _owner_id(user)
    state = graph_state.current(request.app.state, owner_id=owner_id)

    if state is None:
        store = _get_store(request.app.state)
        if store is not None:
            history = store.list_scan_history(owner_id, limit=1)
            if history and history[0].get("status") == "done":
                project_path = history[0].get("project_path")
                if project_path:
                    state = store.load_graph_state(project_path, owner_id=owner_id)
                    if state is not None:
                        graph_state.publish(request.app.state, state, owner_id=owner_id)

    if state is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "No knowledge graph available. Set PROJECT_ROOT in backend/.env "
                "and restart, or POST /graph/scan with a project path."
            ),
        )

    return state


def _record_job(job_id: str, payload: dict) -> None:
    """
    Store a job result, evicting the oldest entries past _MAX_JOBS.
    """
    _jobs[job_id] = payload
    _jobs.move_to_end(job_id)

    while len(_jobs) > _MAX_JOBS:
        _jobs.popitem(last=False)


def _get_store(app_state) -> OrionPersistence | None:
    return getattr(app_state, "persistence", None)


def _audit_scan(
    app_state,
    *,
    actor: CurrentUser | None,
    action: str,
    job_id: str,
    project_path: str,
    status: str,
    details: dict | None = None,
) -> None:
    """Best-effort durable audit logging for the scan lifecycle."""
    store = _get_store(app_state)
    if store is None:
        return

    try:
        store.record_audit_event(
            event_id=uuid.uuid4().hex,
            timestamp=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            actor_key_id=getattr(actor, "key_id", None),
            actor_name=getattr(actor, "name", None),
            actor_role=getattr(actor, "role", None),
            action=action,
            resource_type="scan_job",
            resource_id=job_id,
            project_path=project_path,
            status=status,
            details=details,
        )
    except Exception as exc:
        # Audit persistence must never break a scan.
        print(f"[Orion] Audit logging failed: {type(exc).__name__}: {exc}")


def _save_job(app_state, job_id: str, payload: dict) -> None:
    _record_job(job_id, payload)

    store = _get_store(app_state)
    if store is not None:
        try:
            store.save_scan_job(job_id, payload)
        except Exception:
            #
            # The in-memory fallback still keeps the request flow working if
            # persistence has a transient issue.
            #
            pass


# ------------------------------------------------------------------
# Stats
# ------------------------------------------------------------------

@router.get("/stats", response_model=StatsResponse)
async def graph_stats(request: Request, _user: CurrentUser):
    """
    Summary statistics for the knowledge graph, plus the project it came from.
    """
    return _get_state(request, _user).stats()


# ------------------------------------------------------------------
# Search
# ------------------------------------------------------------------

@router.get("/search", response_model=SearchResponse)
async def search_symbols(
    request: Request,
    _user: CurrentUser,
    q: str = Query(..., min_length=1, description="Search text"),
    limit: int = Query(20, ge=1, le=200),
    types: str | None = Query(
        None,
        description="Comma-separated node types to include, e.g. 'function,method'",
    ),
):
    """
    Ranked fuzzy search across every symbol in the graph.

    Matching is tiered — exact name, then prefix, then camelCase acronym, then
    substring, then subsequence — so short queries stay useful on large
    projects. See app.scanner.knowledge_graph.search for the ranking rules.

        GET /graph/search?q=resolve
        GET /graph/search?q=cgb                    -> CallGraphBuilder
        GET /graph/search?q=scan&types=method
    """
    state = _get_state(request, _user)

    wanted = None
    if types:
        wanted = {part.strip() for part in types.split(",") if part.strip()}

    hits = state.search.search(q, limit=limit, types=wanted)

    results: list[SearchResult] = []

    for node_id, qualified_name, node_type in hits:
        node = state.graph.get_node(node_id)

        if node is None:
            continue

        results.append(
            SearchResult(
                qualified_name=qualified_name,
                name=node.name,
                type=node_type,
                module=node.module,
                file=str(node.path) if node.path else None,
                line=node.line,
            )
        )

    return SearchResponse(query=q, count=len(results), results=results)


# ------------------------------------------------------------------
# Scan
# ------------------------------------------------------------------

@router.get("/history")
async def scan_history(
    request: Request,
    _user: CurrentUser,
    limit: int = Query(100, ge=1, le=500),
):
    """Return only the authenticated account's durable scan history."""
    store = _get_store(request.app.state)
    if store is None:
        return {"count": 0, "scans": []}
    scans = store.list_scan_history(_owner_id(_user), limit=limit)
    return {
        "scans": scans,
        "count": len(scans),
    }


@router.post("/history/{job_id}/activate", response_model=StatsResponse)
async def activate_scan_history(job_id: str, request: Request, _user: CurrentUser):
    """Load one of the authenticated user's persisted graphs as the active view."""
    store = _get_store(request.app.state)
    if store is None:
        raise HTTPException(status_code=503, detail="Persistence is unavailable.")

    job = store.load_scan_job(job_id, owner_id=_owner_id(_user))
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown scan: {job_id}")
    if job.get("status") != "done":
        raise HTTPException(status_code=409, detail="Only completed scans can be activated.")

    state = store.load_graph_state(job["project_path"], owner_id=_owner_id(_user))
    if state is None:
        raise HTTPException(status_code=404, detail="The graph snapshot for this scan is unavailable.")

    graph_state.publish(request.app.state, state, owner_id=_owner_id(_user))
    return state.stats()

def _do_scan(
    app_state,
    path_str: str,
    job_id: str,
    actor: CurrentUser | None = None,
    owner_id: str = "__legacy__",
) -> None:
    """
    Blocking scan, run in a worker thread via run_in_executor.

    The new snapshot is published in a single assignment once it is fully
    built, so requests arriving mid-scan keep seeing the previous graph
    rather than a partially populated one.

    ``_scan_active`` is cleared in the outermost ``finally`` so the
    concurrency guard is held for the entire background execution lifetime.
    """
    global _scan_active

    def progress(message: str, percent: int) -> None:
        _save_job(
            app_state,
            job_id,
            {
                "status": "running",
                "message": f"{message} ({percent}%)",
                "stats": None,
                "project_path": path_str,
                "owner_id": owner_id,
            },
        )
        _log.info(
            "Scan progress",
            extra={
                "job_id": job_id,
                "project_path": path_str,
                "progress_percent": percent,
                "stage": message,
            },
        )

    _save_job(
        app_state,
        job_id,
        {
            "status": "running",
            "message": f"Scanning {path_str}…",
            "stats": None,
            "project_path": path_str,
            "owner_id": owner_id,
        },
    )
    _log.info(
        "Scan started",
        extra={"job_id": job_id, "project_path": path_str, "status_code": 202},
    )
    _audit_scan(
        app_state,
        actor=actor,
        action="scan.started",
        job_id=job_id,
        project_path=path_str,
        status="started",
    )

    try:
        state = graph_state.scan_project(Path(path_str), progress_callback=progress)

        store = _get_store(app_state)
        if store is not None:
            store.save_graph_state(state, owner_id=owner_id)

        graph_state.publish(app_state, state, owner_id=owner_id)
        stats = state.stats()

        _save_job(app_state, job_id, {
            "status": "done",
            "message": f"Scanned {stats['nodes']} nodes, {stats['edges']} edges.",
            "stats": stats,
            "project_path": path_str,
            "owner_id": owner_id,
        })
        _log.info(
            "Scan completed",
            extra={
                "job_id": job_id,
                "project_path": path_str,
                "nodes": stats.get("nodes"),
                "edges": stats.get("edges"),
                "status_code": 200,
            },
        )
        _audit_scan(
            app_state,
            actor=actor,
            action="scan.completed",
            job_id=job_id,
            project_path=path_str,
            status="success",
            details={
                "nodes": stats.get("nodes"),
                "edges": stats.get("edges"),
            },
        )

    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        _save_job(app_state, job_id, {
            "status": "error",
            "message": message,
            "stats": None,
            "project_path": path_str,
            "owner_id": owner_id,
        })
        _log.error(
            "Scan failed",
            extra={
                "job_id": job_id,
                "project_path": path_str,
                "error_type": type(exc).__name__,
                "status_code": 500,
            },
        )
        _audit_scan(
            app_state,
            actor=actor,
            action="scan.failed",
            job_id=job_id,
            project_path=path_str,
            status="failed",
            details={
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )

    finally:
        store = _get_store(app_state)

        if store is not None:
            try:
                store.release_scan_lease(path_str, job_id)
            except Exception as exc:
                print(
                    f"[Orion] Failed to release scan lease: "
                    f"{type(exc).__name__}: {exc}"
                )

        _scan_active = False


@router.post(
    "/scan",
    response_model=ScanStatus,
    status_code=202,
    dependencies=[Depends(require_role(ROLE_MEMBER))],
)
async def start_scan(body: ScanRequest, request: Request, _user: CurrentUser):
    """
    Start an async scan of a local directory, returning a job_id to poll.

    At most one scan may be running at a time. A second request while one is
    already active receives a 409. The path must resolve inside ALLOWED_ROOTS.

        POST /graph/scan  {"path": "/home/user/myproject"}
    """
    global _scan_active

    try:
        if settings.ALLOW_UNSAFE_SCAN_PATHS:
            target = Path(body.path).expanduser().resolve()
            if not target.exists():
                raise HTTPException(status_code=400, detail=f"Path does not exist: {target}")
            if not target.is_dir():
                raise HTTPException(status_code=400, detail=f"Path is not a directory: {target}")
            _log.warning(
                "Unsafe scan path accepted because ALLOW_UNSAFE_SCAN_PATHS is enabled",
                extra={"project_path": str(target)},
            )
        else:
            target = safe_directory(body.path, settings.allowed_roots)
    except PathNotAllowed as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    store = _get_store(request.app.state)

    async with _scan_lock:
        if _scan_active:
            raise HTTPException(
                status_code=409,
                detail="A graph scan is already running.",
            )

        job_id = uuid.uuid4().hex[:8]

        if store is not None:
            try:
                acquired = store.acquire_scan_lease(str(target), job_id)
            except Exception as exc:
                raise HTTPException(
                    status_code=503,
                    detail="Unable to acquire scan coordination lease.",
                ) from exc

            if not acquired:
                raise HTTPException(
                    status_code=409,
                    detail="A graph scan is already running for this project.",
                )

        _scan_active = True

    try:
        _save_job(
            job_id=job_id,
            app_state=request.app.state,
            payload={
                "status": "pending",
                "message": "Queued",
                "stats": None,
                "project_path": str(target),
                "owner_id": _owner_id(_user),
            },
        )

        asyncio.get_running_loop().run_in_executor(
            None,
            _do_scan,
            request.app.state,
            str(target),
            job_id,
            _user,
            _owner_id(_user),
        )
    except Exception:
        if store is not None:
            try:
                store.release_scan_lease(str(target), job_id)
            except Exception:
                pass
        _scan_active = False
        raise

    return ScanStatus(
        job_id=job_id,
        status="pending",
        message="Scan queued",
        stats=None,
    )


@router.get("/scan/{job_id}", response_model=ScanStatus)
async def scan_status(job_id: str, request: Request, _user: CurrentUser):
    """
    Poll a background scan. When status is 'done', 'stats' holds the new graph stats.
    """
    store = _get_store(request.app.state)
    job = None

    if store is not None:
        try:
            job = store.load_scan_job(job_id, owner_id=_owner_id(_user))
        except Exception:
            job = None

    if job is None:
        job = _jobs.get(job_id)

    if job is not None and job.get("owner_id", "__legacy__") != _owner_id(_user):
        job = None

    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown job: {job_id}")

    return ScanStatus(
        job_id=job_id,
        status=job["status"],
        message=job["message"],
        stats=job["stats"],
    )


@router.get("/browse", response_model=BrowseResponse)
async def browse_dirs(
    _user: CurrentUser,
    path: str = "",
):
    """
    List the immediate children of a directory, for the frontend's picker.

    Restricted to ALLOWED_ROOTS. An empty path returns the first configured
    root rather than the user's home, so the picker always opens somewhere
    it is actually permitted to read.
    """
    roots = settings.allowed_roots

    if not roots:
        raise HTTPException(
            status_code=400,
            detail="No readable roots are configured. Set ALLOWED_ROOTS in backend/.env.",
        )

    try:
        target = safe_directory(path or str(roots[0]), roots)
    except PathNotAllowed as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        children = sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
    except (PermissionError, OSError):
        children = []

    entries: list[BrowseEntry] = []

    for child in children:
        try:
            entries.append(
                BrowseEntry(name=child.name, path=str(child), is_dir=child.is_dir())
            )
        except OSError:
            continue

    #
    # Only offer a parent link while it stays inside the allowlist, so the
    # picker cannot walk the user out of bounds and into a 400.
    #
    parent: str | None = None
    if target.parent != target:
        try:
            safe_directory(str(target.parent), roots)
            parent = str(target.parent)
        except PathNotAllowed:
            parent = None

    return BrowseResponse(
        current=str(target),
        parent=parent,
        entries=entries,
        allowed_roots=[str(root) for root in roots],
    )


# ------------------------------------------------------------------
# Path finding
# ------------------------------------------------------------------

@router.get("/path")
async def call_path(
    request: Request,
    _user: CurrentUser,
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
    from_symbol: str | None = Query(None),
    to_symbol: str | None = Query(None),
    max_depth: int = Query(15, ge=1, le=100),
):
    """
    Shortest call path between two symbols.

        GET /graph/path?from=a.b.Scanner.scan&to=a.c.Index.lookup
        GET /graph/path?from_symbol=a.b.Scanner.scan&to_symbol=a.c.Index.lookup
    """
    state = _get_state(request, _user)

    source = from_ or from_symbol
    target = to or to_symbol

    if not source or not target:
        raise HTTPException(status_code=400, detail="Both 'from' and 'to' query params are required.")

    path = state.query.path_between(source, target, max_depth=max_depth)
    return {
        "path": path or [],
        "hops": len(path) - 1 if path else 0,
    }


# ------------------------------------------------------------------
# Symbol routes
# ------------------------------------------------------------------
#
# ORDER IS LOAD-BEARING. {qualified_name:path} compiles to (?P<...>.*), which
# happily swallows slashes, so the bare /symbol/{qn} route matches
# "/symbol/a.b.c/impact" with qualified_name="a.b.c/impact". When it was
# registered first, /impact was unreachable and every impact request 404'd.
# The specific route must stay above the catch-all.
#

@router.get("/symbol/{qualified_name:path}/impact", response_model=ImpactResponse)
async def symbol_impact(
    qualified_name: str,
    request: Request,
    _user: CurrentUser,
    max_depth: int = Query(10, ge=1, le=100),
):
    """
    Impact analysis: if this symbol changes, what is transitively affected?

        GET /graph/symbol/app.scanner.symbol_index.SymbolIndex.lookup/impact
    """
    state = _get_state(request, _user)

    if state.query.get_symbol(qualified_name) is None:
        raise HTTPException(status_code=404, detail=f"Symbol not found: {qualified_name}")

    result = state.query.impact_of(qualified_name, max_depth=max_depth)

    return ImpactResponse(
        symbol=_node_out(result["symbol"]),
        direct_callers=[_node_out(node) for node in result["direct_callers"]],
        all_callers=[_node_out(node) for node in result["all_callers"]],
        affected_modules=result["affected_modules"],
        affected_files=result["affected_files"],
        direct_count=result["direct_count"],
        total_count=result["total_count"],
    )


@router.get("/symbol/{qualified_name:path}", response_model=SymbolResponse)
async def symbol_info(qualified_name: str, request: Request, _user: CurrentUser):
    """
    A symbol with its direct callers and callees.

        GET /graph/symbol/app.scanner.scanner.ProjectScanner.scan
    """
    state = _get_state(request, _user)

    symbol = state.query.get_symbol(qualified_name)

    if symbol is None:
        raise HTTPException(status_code=404, detail=f"Symbol not found: {qualified_name}")

    return SymbolResponse(
        symbol=_node_out(symbol),
        callers=[_node_out(node) for node in state.query.callers_of(qualified_name)],
        callees=[_node_out(node) for node in state.query.callees_of(qualified_name)],
    )
