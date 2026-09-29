"""
Durable persistence for Orion's graph snapshot, scan jobs, and project metadata.

The production v1 goal is to survive restarts without forcing a rescan and to
keep scan progress/queryable state outside process memory. SQLite is a good fit
for this stage because it is local, dependable, and requires no extra service.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.graph_state import GraphState
from app.scanner.knowledge_graph.graph import KnowledgeGraph
from app.scanner.knowledge_graph.models import GraphEdge, GraphNode
from app.scanner.knowledge_graph.query import KnowledgeGraphQuery
from app.scanner.knowledge_graph.search import SymbolSearchIndex


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _json_loads(payload: str | None) -> Any:
    if not payload:
        return None
    return json.loads(payload)


LEGACY_OWNER_ID = "__legacy__"


def _snapshot_key(project_path: str, owner_id: str = LEGACY_OWNER_ID) -> str:
    """Namespace persisted snapshots by account without changing old tables."""
    return project_path if owner_id == LEGACY_OWNER_ID else f"{owner_id}::{project_path}"


def _graph_to_snapshot(graph) -> dict[str, Any]:
    return {
        "nodes": {
            node_id: node.model_dump(mode="json")
            for node_id, node in graph.nodes.items()
        },
        "edges": [
            edge.model_dump(mode="json")
            for edge in graph.edges
        ],
    }


def _graph_from_snapshot(snapshot: dict[str, Any]) -> KnowledgeGraph:
    graph = KnowledgeGraph()

    for node_id, node_data in snapshot.get("nodes", {}).items():
        node = GraphNode.model_validate(node_data)
        if not node.id:
            node.id = node_id
        graph.add_node(node)

    for edge_data in snapshot.get("edges", []):
        edge = GraphEdge.model_validate(edge_data)
        graph.add_edge(edge)

    return graph


class OrionPersistence:
    """
    Small SQLite-backed store for graph snapshots and scan metadata.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        conn = self._connect()
        try:
            with self._lock:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS graph_snapshots (
                        project_path TEXT PRIMARY KEY,
                        snapshot_json TEXT NOT NULL,
                        stats_json TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS project_metadata (
                        project_path TEXT PRIMARY KEY,
                        metadata_json TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                CREATE TABLE IF NOT EXISTS scan_jobs (
                    job_id TEXT PRIMARY KEY,
                    project_path TEXT,
                    owner_id TEXT NOT NULL DEFAULT '__legacy__',
                    status TEXT NOT NULL,
                    message TEXT NOT NULL,
                        stats_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS edit_proposals (
                    proposal_id TEXT PRIMARY KEY,
                    project_path TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    status TEXT NOT NULL,
                    proposal_json TEXT NOT NULL,
                    validation_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    key_hash TEXT NOT NULL UNIQUE,
                    role TEXT NOT NULL DEFAULT 'viewer',
                    revoked INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    last_used_at TEXT
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    actor_key_id TEXT,
                    actor_name TEXT,
                    actor_role TEXT,
                    action TEXT NOT NULL,
                    resource_type TEXT,
                    resource_id TEXT,
                    project_path TEXT,
                    status TEXT NOT NULL,
                    details_json TEXT
                );

                CREATE TABLE IF NOT EXISTS scan_leases (
                    project_path TEXT PRIMARY KEY,
                    job_id       TEXT NOT NULL,
                    acquired_at  TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_accounts (
                    user_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    email TEXT,
                    name TEXT,
                    picture TEXT,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                );
                """
            )
                columns = {
                    row["name"]
                    for row in conn.execute("PRAGMA table_info(scan_jobs)").fetchall()
                }
                if "owner_id" not in columns:
                    conn.execute(
                        "ALTER TABLE scan_jobs ADD COLUMN owner_id TEXT NOT NULL DEFAULT '__legacy__'"
                    )
                conn.commit()
        finally:
            conn.close()

    def save_graph_state(
        self,
        state,
        metadata: dict[str, Any] | None = None,
        owner_id: str = LEGACY_OWNER_ID,
    ) -> None:
        snapshot = _graph_to_snapshot(state.graph)
        stats = state.stats()
        now = _utc_now()
        meta = metadata or stats
        owner_id = owner_id or getattr(state, "owner_id", LEGACY_OWNER_ID)
        storage_key = _snapshot_key(state.project_path, owner_id)

        conn = self._connect()
        try:
            with self._lock:
                conn.execute(
                    """
                    INSERT INTO graph_snapshots (project_path, snapshot_json, stats_json, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(project_path) DO UPDATE SET
                        snapshot_json=excluded.snapshot_json,
                        stats_json=excluded.stats_json,
                        updated_at=excluded.updated_at
                    """,
                    (
                        storage_key,
                        _json_dumps(snapshot),
                        _json_dumps(stats),
                        now,
                    ),
                )

                conn.execute(
                    """
                    INSERT INTO project_metadata (project_path, metadata_json, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(project_path) DO UPDATE SET
                        metadata_json=excluded.metadata_json,
                        updated_at=excluded.updated_at
                    """,
                    (
                        storage_key,
                        _json_dumps(meta),
                        now,
                    ),
                )
                conn.commit()
        finally:
            conn.close()

    def load_graph_state(
        self,
        project_path: str,
        owner_id: str = LEGACY_OWNER_ID,
    ) -> GraphState | None:
        conn = self._connect()
        try:
            with self._lock:
                row = conn.execute(
                    """
                    SELECT snapshot_json
                    FROM graph_snapshots
                    WHERE project_path = ?
                    """,
                    (_snapshot_key(project_path, owner_id),),
                ).fetchone()
        finally:
            conn.close()

        if row is None:
            return None

        snapshot = _json_loads(row["snapshot_json"]) or {}
        graph = _graph_from_snapshot(snapshot)

        return GraphState(
            graph=graph,
            query=KnowledgeGraphQuery(graph),
            search=SymbolSearchIndex.from_graph(graph),
            project_path=project_path,
            owner_id=owner_id,
        )

    def load_project_metadata(self, project_path: str) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            with self._lock:
                row = conn.execute(
                    """
                    SELECT metadata_json
                    FROM project_metadata
                    WHERE project_path = ?
                    """,
                    (project_path,),
                ).fetchone()
        finally:
            conn.close()

        if row is None:
            return None

        return _json_loads(row["metadata_json"]) or {}

    def save_scan_job(
        self,
        job_id: str,
        payload: dict[str, Any],
        owner_id: str = LEGACY_OWNER_ID,
    ) -> None:
        now = _utc_now()
        stats = payload.get("stats")
        project_path = payload.get("project_path")
        owner_id = payload.get("owner_id", owner_id) or LEGACY_OWNER_ID

        conn = self._connect()
        try:
            with self._lock:
                existing = conn.execute(
                    """
                    SELECT created_at
                    FROM scan_jobs
                    WHERE job_id = ?
                    """,
                    (job_id,),
                ).fetchone()

                created_at = existing["created_at"] if existing else now

                conn.execute(
                    """
                    INSERT INTO scan_jobs (
                        job_id, project_path, owner_id, status, message, stats_json, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(job_id) DO UPDATE SET
                        project_path=excluded.project_path,
                        owner_id=excluded.owner_id,
                        status=excluded.status,
                        message=excluded.message,
                        stats_json=excluded.stats_json,
                        updated_at=excluded.updated_at
                    """,
                    (
                        job_id,
                        project_path,
                        owner_id,
                        payload.get("status", "pending"),
                        payload.get("message", ""),
                        _json_dumps(stats) if stats is not None else None,
                        created_at,
                        now,
                    ),
                )
                conn.commit()
        finally:
            conn.close()

    def load_scan_job(
        self,
        job_id: str,
        owner_id: str | None = None,
    ) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            with self._lock:
                query = """
                    SELECT job_id, project_path, owner_id, status, message, stats_json, created_at, updated_at
                    FROM scan_jobs
                    WHERE job_id = ?
                """
                params: tuple[Any, ...] = (job_id,)
                if owner_id is not None:
                    query += " AND owner_id = ?"
                    params += (owner_id,)
                row = conn.execute(query, params).fetchone()
        finally:
            conn.close()

        if row is None:
            return None

        return {
            "job_id": row["job_id"],
            "project_path": row["project_path"],
            "owner_id": row["owner_id"],
            "status": row["status"],
            "message": row["message"],
            "stats": _json_loads(row["stats_json"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def upsert_user(
        self,
        *,
        user_id: str,
        provider: str,
        email: str | None,
        name: str | None,
        picture: str | None,
    ) -> None:
        """Create or refresh the durable account record."""
        now = _utc_now()
        conn = self._connect()
        try:
            with self._lock:
                conn.execute(
                    """
                    INSERT INTO user_accounts
                        (user_id, provider, email, name, picture, created_at, last_seen_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        provider=excluded.provider,
                        email=excluded.email,
                        name=excluded.name,
                        picture=excluded.picture,
                        last_seen_at=excluded.last_seen_at
                    """,
                    (user_id, provider, email, name, picture, now, now),
                )
                conn.commit()
        finally:
            conn.close()

    def list_scan_history(self, owner_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """Return scans owned by one account, newest first."""
        limit = max(1, min(limit, 500))
        conn = self._connect()
        try:
            with self._lock:
                rows = conn.execute(
                    """
                    SELECT job_id, project_path, owner_id, status, message, stats_json, created_at, updated_at
                    FROM scan_jobs
                    WHERE owner_id = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (owner_id, limit),
                ).fetchall()
        finally:
            conn.close()

        return [
            {
                "job_id": row["job_id"],
                "project_path": row["project_path"],
                "owner_id": row["owner_id"],
                "status": row["status"],
                "message": row["message"],
                "stats": _json_loads(row["stats_json"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def recover_incomplete_scan_jobs(self) -> int:

        now = _utc_now()
        conn = self._connect()
        try:
            with self._lock:
                rows = conn.execute(
                    """
                    SELECT job_id
                    FROM scan_jobs
                    WHERE status IN ('pending', 'running')
                    """
                ).fetchall()

                if not rows:
                    return 0

                job_ids = [row["job_id"] for row in rows]
                placeholders = ",".join("?" for _ in job_ids)

                cursor = conn.execute(
                    f"""
                    UPDATE scan_jobs
                    SET status = 'error',
                        message = ?,
                        updated_at = ?
                    WHERE job_id IN ({placeholders})
                    """,
                    (
                        "Scan interrupted by server restart; resubmit the scan.",
                        now,
                        *job_ids,
                    ),
                )

                conn.execute(
                    f"""
                    DELETE FROM scan_leases
                    WHERE job_id IN ({placeholders})
                    """,
                    job_ids,
                )

                conn.commit()
                return cursor.rowcount
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Scan-lease coordination
    # ------------------------------------------------------------------

    def acquire_scan_lease(self, project_path: str, job_id: str) -> bool:
        """
        Atomically claim the scan slot for *project_path*.

        Returns ``True`` if *this* worker now holds the lease (either it
        was vacant or it was already held by the same *job_id*).  Returns
        ``False`` if another job already owns the lease.

        SQLite serialises every write; ``INSERT OR IGNORE`` therefore
        acts as a test-and-set: if the row is already present the insert
        silently does nothing and the subsequent read tells us who holds
        the lease.
        """
        now = _utc_now()
        conn = self._connect()
        try:
            with self._lock:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO scan_leases (project_path, job_id, acquired_at)
                    VALUES (?, ?, ?)
                    """,
                    (project_path, job_id, now),
                )
                conn.commit()

                row = conn.execute(
                    "SELECT job_id FROM scan_leases WHERE project_path = ?",
                    (project_path,),
                ).fetchone()
        finally:
            conn.close()

        # We hold the lease iff the stored job_id matches ours.
        return row is not None and row["job_id"] == job_id

    def release_scan_lease(self, project_path: str, job_id: str) -> bool:
        """
        Release the lease for *project_path*, but **only** if it is still
        held by *job_id*.

        Returns ``True`` if the lease was released, ``False`` if it did
        not exist or was owned by a different job.
        """
        conn = self._connect()
        try:
            with self._lock:
                cursor = conn.execute(
                    """
                    DELETE FROM scan_leases
                    WHERE project_path = ? AND job_id = ?
                    """,
                    (project_path, job_id),
                )
                conn.commit()
                return cursor.rowcount > 0
        finally:
            conn.close()

    def save_edit_proposal(self, proposal: dict[str, Any]) -> None:
        now = _utc_now()
        proposal_id = proposal["proposal_id"]

        conn = self._connect()
        try:
            with self._lock:
                existing = conn.execute(
                    """
                    SELECT created_at
                    FROM edit_proposals
                    WHERE proposal_id = ?
                    """,
                    (proposal_id,),
                ).fetchone()

                created_at = existing["created_at"] if existing else now

                conn.execute(
                    """
                    INSERT INTO edit_proposals (
                        proposal_id, project_path, objective, status,
                        proposal_json, validation_json, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(proposal_id) DO UPDATE SET
                        project_path=excluded.project_path,
                        objective=excluded.objective,
                        status=excluded.status,
                        proposal_json=excluded.proposal_json,
                        validation_json=excluded.validation_json,
                        updated_at=excluded.updated_at
                    """,
                    (
                        proposal_id,
                        proposal["project_path"],
                        proposal["objective"],
                        proposal["status"],
                        _json_dumps(proposal),
                        _json_dumps(proposal.get("validation")) if proposal.get("validation") else None,
                        created_at,
                        now,
                    ),
                )
                conn.commit()
        finally:
            conn.close()

    def load_edit_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            with self._lock:
                row = conn.execute(
                    """
                    SELECT proposal_json
                    FROM edit_proposals
                    WHERE proposal_id = ?
                    """,
                    (proposal_id,),
                ).fetchone()
        finally:
            conn.close()

        if row is None:
            return None

        return _json_loads(row["proposal_json"])

    def list_edit_proposals(
        self,
        *,
        status: str | None = None,
        project_path: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Return proposals ordered newest first.

        Both ``status`` and ``project_path`` are optional filters.
        ``limit`` is clamped to [1, 200].
        """
        limit = max(1, min(limit, 200))
        conditions: list[str] = []
        params: list[Any] = []

        if status is not None:
            conditions.append("status = ?")
            params.append(status)

        if project_path is not None:
            conditions.append("project_path = ?")
            params.append(project_path)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(limit)

        conn = self._connect()
        try:
            with self._lock:
                rows = conn.execute(
                    f"""
                    SELECT proposal_json
                    FROM edit_proposals
                    {where}
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    params,
                ).fetchall()
        finally:
            conn.close()

        return [
            _json_loads(row["proposal_json"])
            for row in rows
            if row["proposal_json"]
        ]



    def transition_edit_proposal_status(
        self,
        proposal_id: str,
        *,
        expected_status: str,
        new_status: str,
    ) -> bool:
        """
        Atomically transition an edit proposal between statuses.

        Returns True only when the proposal was in expected_status and the
        transition succeeded. This prevents two independent workers from
        both claiming the same proposal.
        """
        now = _utc_now()

        conn = self._connect()
        try:
            with self._lock:
                cursor = conn.execute(
                    """
                    UPDATE edit_proposals
                    SET status = ?,
                        proposal_json = json_set(
                            proposal_json,
                            '$.status',
                            ?
                        ),
                        updated_at = ?
                    WHERE proposal_id = ?
                      AND status = ?
                    """,
                    (
                        new_status,
                        new_status,
                        now,
                        proposal_id,
                        expected_status,
                    ),
                )
                conn.commit()
                return cursor.rowcount > 0
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # API keys
    # ------------------------------------------------------------------

    def create_api_key(self, key_id: str, name: str, key_hash: str, role: str) -> dict[str, Any]:
        """
        Persist a new API key record.  Returns the created row.
        """
        now = _utc_now()
        conn = self._connect()
        try:
            with self._lock:
                conn.execute(
                    """
                    INSERT INTO api_keys (key_id, name, key_hash, role, revoked, created_at)
                    VALUES (?, ?, ?, ?, 0, ?)
                    """,
                    (key_id, name, key_hash, role, now),
                )
                conn.commit()
        finally:
            conn.close()

        return {
            "key_id": key_id,
            "name": name,
            "role": role,
            "revoked": False,
            "created_at": now,
            "last_used_at": None,
        }

    def lookup_api_key(self, raw_key: str) -> dict[str, Any] | None:
        """
        Validate *raw_key* against every non-revoked stored hash.

        Returns the key record on success or ``None`` on failure.
        The ``last_used_at`` timestamp is bumped on every successful lookup.
        """
        from app.core.auth import verify_key

        conn = self._connect()
        try:
            with self._lock:
                rows = conn.execute(
                    """
                    SELECT key_id, name, key_hash, role, created_at
                    FROM api_keys
                    WHERE revoked = 0
                    """
                ).fetchall()
        finally:
            conn.close()

        now = _utc_now()

        for row in rows:
            if verify_key(raw_key, row["key_hash"]):
                # Bump last_used_at (best-effort).
                conn2 = self._connect()
                try:
                    with self._lock:
                        conn2.execute(
                            "UPDATE api_keys SET last_used_at = ? WHERE key_id = ?",
                            (now, row["key_id"]),
                        )
                        conn2.commit()
                finally:
                    conn2.close()

                return {
                    "key_id": row["key_id"],
                    "name": row["name"],
                    "role": row["role"],
                    "created_at": row["created_at"],
                    "last_used_at": now,
                }

        return None

    def list_api_keys(self) -> list[dict[str, Any]]:
        """
        Return all key records (revoked included), newest first.
        """
        conn = self._connect()
        try:
            with self._lock:
                rows = conn.execute(
                    """
                    SELECT key_id, name, role, revoked, created_at, last_used_at
                    FROM api_keys
                    ORDER BY created_at DESC
                    """
                ).fetchall()
        finally:
            conn.close()

        return [
            {
                "key_id": r["key_id"],
                "name": r["name"],
                "role": r["role"],
                "revoked": bool(r["revoked"]),
                "created_at": r["created_at"],
                "last_used_at": r["last_used_at"],
            }
            for r in rows
        ]

    def revoke_api_key(self, key_id: str) -> bool:
        """
        Mark a key as revoked.  Returns ``True`` if the key existed.
        """
        now = _utc_now()
        conn = self._connect()
        try:
            with self._lock:
                cursor = conn.execute(
                    "UPDATE api_keys SET revoked = 1, last_used_at = ? WHERE key_id = ?",
                    (now, key_id),
                )
                conn.commit()
                return cursor.rowcount > 0
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Audit events
    # ------------------------------------------------------------------

    def record_audit_event(
        self,
        *,
        event_id: str,
        action: str,
        status: str,
        timestamp: str | None = None,
        actor_key_id: str | None = None,
        actor_name: str | None = None,
        actor_role: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        project_path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Persist one security/operational audit event."""
        now = timestamp or _utc_now()

        conn = self._connect()
        try:
            with self._lock:
                conn.execute(
                    """
                    INSERT INTO audit_events (
                        event_id,
                        timestamp,
                        actor_key_id,
                        actor_name,
                        actor_role,
                        action,
                        resource_type,
                        resource_id,
                        project_path,
                        status,
                        details_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        now,
                        actor_key_id,
                        actor_name,
                        actor_role,
                        action,
                        resource_type,
                        resource_id,
                        project_path,
                        status,
                        _json_dumps(details) if details is not None else None,
                    ),
                )
                conn.commit()
        finally:
            conn.close()

    def list_audit_events(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return recent audit events, newest first."""
        limit = max(1, min(limit, 1000))

        conn = self._connect()
        try:
            with self._lock:
                rows = conn.execute(
                    """
                    SELECT
                        event_id,
                        timestamp,
                        actor_key_id,
                        actor_name,
                        actor_role,
                        action,
                        resource_type,
                        resource_id,
                        project_path,
                        status,
                        details_json
                    FROM audit_events
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        finally:
            conn.close()

        return [
            {
                "event_id": row["event_id"],
                "timestamp": row["timestamp"],
                "actor_key_id": row["actor_key_id"],
                "actor_name": row["actor_name"],
                "actor_role": row["actor_role"],
                "action": row["action"],
                "resource_type": row["resource_type"],
                "resource_id": row["resource_id"],
                "project_path": row["project_path"],
                "status": row["status"],
                "details": _json_loads(row["details_json"]),
            }
            for row in rows
        ]
