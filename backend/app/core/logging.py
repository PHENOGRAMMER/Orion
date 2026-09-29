"""
Orion structured logging.

In production (DEBUG=False) every log record is emitted as a single JSON
object so it can be ingested by log aggregators without a parser.

In development (DEBUG=True, the default) a human-readable format is used.

A ``request_id`` context-var is available so every log line produced while
handling a request carries the same trace token.  Routers attach it via the
``RequestIDMiddleware`` defined here.

Usage
-----
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("scan started", extra={"project": "/home/me/repo"})
"""

from __future__ import annotations

import json
import logging
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# ── Request-ID context ────────────────────────────────────────────────────────

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def current_request_id() -> str:
    return _request_id.get()


def set_request_id(rid: str) -> None:
    _request_id.set(rid)


# ── JSON formatter ────────────────────────────────────────────────────────────

class _JsonFormatter(logging.Formatter):
    """Emit each record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": current_request_id(),
            "message": record.getMessage(),
        }

        # Merge any extra fields the caller supplied.
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "taskName",
            }:
                payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


# ── Setup ─────────────────────────────────────────────────────────────────────

def configure_logging(*, debug: bool = True) -> None:
    """
    Call once at application startup (``main.py`` lifespan).

    ``debug=True`` → human-readable, coloured-ish output.
    ``debug=False`` → JSON lines for log aggregators.
    """
    root = logging.getLogger()

    if root.handlers:
        # Already configured (e.g., during tests) — don't stack handlers.
        return

    handler = logging.StreamHandler()

    if debug:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | [%(request_id_ctx)s] %(message)s",
                defaults={"request_id_ctx": "-"},
            )
        )
    else:
        handler.setFormatter(_JsonFormatter())

    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Silence noisy third-party loggers.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named child of the ``orion`` logger."""
    return logging.getLogger(f"orion.{name}" if not name.startswith("orion") else name)


# ── FastAPI middleware ─────────────────────────────────────────────────────────

try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response

    class RequestIDMiddleware(BaseHTTPMiddleware):
        """
        Assign a unique request_id to every inbound HTTP request.

        The ID is taken from the ``X-Request-ID`` header if the caller
        supplies one, otherwise a fresh UUID4 hex is generated.  The same
        value is echoed back in the response so clients can correlate logs.
        """

        async def dispatch(self, request: Request, call_next) -> Response:
            rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
            set_request_id(rid)
            started = datetime.now(timezone.utc)
            try:
                response = await call_next(request)
            except Exception:
                logging.getLogger("orion.http").exception(
                    "HTTP request failed",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": 500,
                    },
                )
                raise
            elapsed_ms = (datetime.now(timezone.utc) - started).total_seconds() * 1000
            logging.getLogger("orion.http").info(
                "HTTP request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(elapsed_ms, 1),
                },
            )
            response.headers["X-Request-ID"] = rid
            return response

except ImportError:
    # Starlette not available (unit-test context without FastAPI).
    RequestIDMiddleware = None  # type: ignore[assignment,misc]


# ── Module-level convenience logger (backwards-compat) ────────────────────────

logger = get_logger("orion")
