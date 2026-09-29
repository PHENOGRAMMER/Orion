"""
Shared knowledge-graph state.

The startup scan and ``POST /graph/scan`` need to do exactly the same work:
scan a directory, then publish the graph, its query layer and its search index
as one consistent set. Centralising that here is what stops the search index
from silently going stale after a rescan — the bug you get the moment those two
code paths drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class GraphState:
    """
    One immutable snapshot of an analysed project.

    Frozen on purpose. Scans run in a worker thread while requests are being
    served, so the graph, query layer and search index must never be swapped
    independently — a request that read a new graph alongside a stale search
    index would return node IDs that no longer exist. Publishing a single
    frozen object makes that impossible: readers either see the whole old
    snapshot or the whole new one.
    """

    graph: Any
    query: Any
    search: Any
    project_path: str
    owner_id: str = "__legacy__"

    def stats(self) -> dict:
        """
        Graph statistics, annotated with the project this snapshot came from.
        """
        data = self.query.stats()
        data["project_path"] = self.project_path
        data["symbols_indexed"] = len(self.search)
        return data


def scan_project(
    project_root: Path,
    progress_callback: Callable[[str, int], None] | None = None,
) -> GraphState:
    """
    Scan ``project_root`` and return a complete :class:`GraphState`.

    Imports are deferred to call time because the scanner package pulls in the
    whole analysis pipeline; keeping it out of module import means a failure in
    there surfaces as a scan error rather than preventing the app from starting.
    """
    from app.scanner.knowledge_graph.query import KnowledgeGraphQuery
    from app.scanner.knowledge_graph.search import SymbolSearchIndex
    from app.scanner.scanner import ProjectScanner

    scanner = ProjectScanner()
    _result, index = scanner.scan(project_root, progress_callback=progress_callback)

    knowledge_graph = index.knowledge_graph

    return GraphState(
        graph=knowledge_graph,
        query=KnowledgeGraphQuery(knowledge_graph),
        search=SymbolSearchIndex.from_graph(knowledge_graph),
        project_path=str(project_root),
    )


def publish(app_state, state: GraphState, owner_id: str | None = None) -> None:
    """
    Install ``state`` as the live snapshot on ``app.state``.

    The individual ``graph`` / ``query`` / ``project_path`` attributes are
    mirrored alongside it so the standalone scripts under ``backend/`` that
    reach for ``app.state.query`` keep working. New code should read
    ``app.state.graph_state`` instead and get all three consistently.
    """
    resolved_owner = owner_id or state.owner_id
    if resolved_owner != state.owner_id:
        state = GraphState(
            graph=state.graph,
            query=state.query,
            search=state.search,
            project_path=state.project_path,
            owner_id=resolved_owner,
        )

    graph_states = getattr(app_state, "graph_states", None)
    if graph_states is None:
        graph_states = {}
        app_state.graph_states = graph_states
    graph_states[resolved_owner] = state

    app_state.graph_state = state

    app_state.graph = state.graph
    app_state.query = state.query
    app_state.project_path = state.project_path


def current(app_state, owner_id: str | None = None) -> GraphState | None:
    """
    The live snapshot, or None when no project has been analysed yet.
    """
    if owner_id is not None:
        return getattr(app_state, "graph_states", {}).get(owner_id)
    return getattr(app_state, "graph_state", None)
