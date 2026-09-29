from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core import graph_state

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health():
    """Lightweight liveness check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
async def readiness(request: Request):
    """Readiness check for serving Orion requests."""
    persistence = getattr(request.app.state, "persistence", None)

    if persistence is None:
        return JSONResponse(
            {
                "status": "not_ready",
                "reason": "persistence_unavailable",
            },
            status_code=503,
        )

    try:
        conn = persistence._connect()
        conn.execute("SELECT 1")
        conn.close()
    except Exception:
        return JSONResponse(
            {
                "status": "not_ready",
                "reason": "persistence_unavailable",
            },
            status_code=503,
        )

    graph = graph_state.current(request.app.state)
    if graph is None:
        return JSONResponse(
            {
                "status": "not_ready",
                "reason": "graph_unavailable",
            },
            status_code=503,
        )

    return {
        "status": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }