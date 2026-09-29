"""
Orion application entrypoint.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.agent import router as agent_router
from app.api.auth import router as auth_router
from app.api.graph import router as graph_router
from app.api.health import router as health_router
from app.api.graph_exporter import router as export_router
from app.api.orion_llm_router import router as llm_router
from app.core import graph_state
from app.core.config import settings
from app.core.logging import RequestIDMiddleware, configure_logging, get_logger
from app.core.persistence import OrionPersistence

configure_logging(debug=settings.DEBUG)
_log = get_logger("main")


def _resolve_project_root() -> Path:
    """
    Directory the startup scan should analyse.

    PROJECT_ROOT (env or backend/.env) wins. With nothing configured we
    analyse Orion's own backend package, so a fresh checkout is immediately
    explorable and the app effectively demonstrates itself.
    """
    configured = settings.PROJECT_ROOT

    if configured and configured.strip():
        return Path(configured).expanduser().resolve()

    return Path(__file__).resolve().parent


def _bootstrap_admin_key(store: OrionPersistence) -> None:
    """
    If ``ADMIN_API_KEY`` is configured, ensure it is registered as an active
    admin key in the persistence store so the operator can always get in.
    """
    from app.core.auth import _KEY_PREFIX, hash_key, key_id_from_hash

    if not settings.ADMIN_API_KEY:
        return

    raw = settings.ADMIN_API_KEY.strip()
    if not raw.startswith(_KEY_PREFIX):
        raw = f"{_KEY_PREFIX}{raw}"

    try:
        hashed = hash_key(raw)
        kid = key_id_from_hash(hashed)
        existing = store.list_api_keys()
        already_exists = any(key.get("key_id") == kid for key in existing)

        if not already_exists:
            store.create_api_key(kid, name="bootstrap-admin", key_hash=hashed, role="admin")
            _log.info("Bootstrap admin key created", extra={"key_id": kid})
    except Exception as exc:
        _log.error("Failed to bootstrap admin key", extra={"error": str(exc), "error_type": type(exc).__name__})


def _startup_scan(app_state) -> None:
    """
    Build the initial knowledge graph.

    Every failure here is logged and swallowed.  An unreadable or broken
    PROJECT_ROOT used to raise out of the startup hook and take the whole
    server down; now the API comes up, reports 503 from the graph endpoints,
    and the user can point Orion somewhere else via POST /graph/scan.
    """
    project_root = _resolve_project_root()

    if not project_root.exists():
        _log.warning("PROJECT_ROOT does not exist, skipping startup scan", extra={"path": str(project_root)})
        return

    store: OrionPersistence | None = getattr(app_state, "persistence", None)

    if store is not None:
        try:
            persisted = store.load_graph_state(str(project_root))
        except Exception as exc:
            _log.error("Failed to load persisted graph", extra={"error": str(exc), "error_type": type(exc).__name__})
            persisted = None
        if persisted is not None:
            graph_state.publish(app_state, persisted)
            stats = persisted.stats()
            _log.info(
                "Loaded persisted graph",
                extra={"nodes": stats["nodes"], "edges": stats["edges"], "project": stats["project_path"]},
            )
            return

    _log.info("Startup scan starting", extra={"project": str(project_root)})

    try:
        state = graph_state.scan_project(project_root)
    except Exception as exc:
        _log.error(
            "Startup scan failed",
            extra={"error": str(exc), "error_type": type(exc).__name__},
        )
        _log.info("Server is up; POST /graph/scan to analyse a project.")
        return

    if store is not None:
        try:
            store.save_graph_state(state)
        except Exception as exc:
            _log.error(
                "Failed to persist startup snapshot",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            _log.warning("Startup graph was not published.")
            return

    graph_state.publish(app_state, state)

    stats = state.stats()
    _log.info(
        "Graph built",
        extra={
            "nodes": stats["nodes"],
            "edges": stats["edges"],
            "calls": stats["by_edge_type"].get("calls", 0),
            "symbols_indexed": stats["symbols_indexed"],
        },
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Replaces the deprecated @app.on_event("startup") hook.
    """
    app.state.persistence = OrionPersistence(settings.persistence_db_path)
    recovered = app.state.persistence.recover_incomplete_scan_jobs()
    if recovered:
        _log.warning(
            "Recovered interrupted scan jobs",
            extra={"count": recovered},
        )
    _bootstrap_admin_key(app.state.persistence)
    _startup_scan(app.state)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="AI Software Engineer Backend",
    lifespan=lifespan,
)

#
# The bundled frontend is served same-origin from /app, so it needs no CORS
# entry at all. This list exists for a separate dev server, and is an explicit
# allowlist rather than "*" because /graph/browse and /graph/scan read the
# local filesystem — with a wildcard, any page in the user's browser could
# reach in and enumerate their disk. See ALLOW_ORIGINS in core/config.py.
#
if RequestIDMiddleware is not None:
    app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router, prefix="/auth")
app.include_router(graph_router, prefix="/graph")
app.include_router(export_router)
app.include_router(llm_router, prefix="/llm")
app.include_router(agent_router, prefix="/agent")

_frontend = Path(__file__).resolve().parent.parent.parent / "frontend"
if _frontend.exists():
    app.mount("/app", StaticFiles(directory=str(_frontend), html=True), name="frontend")


@app.get("/")
async def root():
    return {
        "application": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "explorer": "/app",
        "docs": "/docs",
    }
