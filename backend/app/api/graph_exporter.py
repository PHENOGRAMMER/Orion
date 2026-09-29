"""
graph_exporter.py — Add this to your Orion FastAPI app
=======================================================
Adds a /export endpoint to dump the in-memory graph to the JSON format
that generate_dataset.py expects.
"""

import json
from pathlib import Path
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.core.auth import CurrentUser
from app.core.config import settings
from app.core import graph_state

router = APIRouter()


def _get_graph_state(app_state, owner_id: str = "__legacy__") -> dict:
    """
    Adapt the live Orion GraphState into the export JSON format.
    """
    snapshot = graph_state.current(app_state, owner_id=owner_id)

    if snapshot is None:
        return {"nodes": {}, "edges": []}

    graph = snapshot.graph

    nodes = {}
    for node_id, node in graph.nodes.items():
        node_type = (
            node.get("type", "unknown")
            if isinstance(node, dict)
            else getattr(node, "type", "unknown")
        )
        node_type = getattr(node_type, "value", node_type)

        node_path = (
            node.get("file")
            if isinstance(node, dict)
            else getattr(node, "path", None)
        )

        nodes[node_id] = {
            "type": str(node_type),
            "file": str(node_path) if node_path else "unknown",
        }

    edges = []
    for edge in graph.edges:
        source = (
            edge.get("src", edge.get("source"))
            if isinstance(edge, dict)
            else edge.source
        )
        target = (
            edge.get("dst", edge.get("target"))
            if isinstance(edge, dict)
            else edge.target
        )
        edge_type = (
            edge.get("type", "unknown")
            if isinstance(edge, dict)
            else edge.type
        )

        edges.append({
            "src": source,
            "dst": target,
            "type": str(getattr(edge_type, "value", edge_type)),
        })

    return {"nodes": nodes, "edges": edges}


@router.get("/export")
async def export_graph(
    request: Request,
    _user: CurrentUser = None,
    download: bool = Query(False, description="Return JSON inline rather than saving to disk"),
    output: str  = Query("graph_export.json", description="Filename to save locally"),
):
    """
    Export the in-memory Orion knowledge graph to JSON.
    Compatible with generate_dataset.py.
    """
    owner_id = getattr(_user, "user_id", None) or "__legacy__"
    data = _get_graph_state(request.app.state, owner_id=owner_id)

    if not data["nodes"]:
        return JSONResponse(
            {"error": "No graph found in app.state or it is empty. Perform a scan first."},
            status_code=400,
        )

    if download:
        return JSONResponse(data)

    # Exports are restricted to Orion's dedicated export directory.
    # The query parameter may contain only a filename.
    out_name = Path(output)

    if (
        out_name.name != output
        or out_name.name in {"", ".", ".."}
        or out_name.is_absolute()
    ):
        return JSONResponse(
            {"error": "output must be a filename, not a path"},
            status_code=400,
        )

    export_dir = Path(settings.PROJECT_ROOT or ".") / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    out_path = export_dir / out_name.name

    # Never follow an existing symlink supplied as the output filename.
    if out_path.is_symlink():
        return JSONResponse(
            {"error": "output file cannot be a symlink"},
            status_code=400,
        )

    out_path.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )

    return {
        "saved_to": str(out_path.resolve()),
        "nodes": len(data["nodes"]),
        "edges": len(data["edges"]),
    }




# ── Standalone export script (no FastAPI needed) ──────────────────────────────
def export_graph_direct(graph_obj, output_path: str = "graph_export.json"):
    """
    Direct export — call this from a script without starting FastAPI.
    graph_obj needs .nodes (dict) and .edges (list) attributes.
    """
    nodes = {}
    for node_id, node in graph_obj.nodes.items():
        node_type = node.get("type", "unknown") if isinstance(node, dict) else getattr(node, "type", "unknown")
        node_type = getattr(node_type, "value", node_type)
        node_path = node.get("file") if isinstance(node, dict) else getattr(node, "path", None)
        nodes[node_id] = {
            "type": str(node_type),
            "file": str(node_path) if node_path else "unknown",
        }

    edges = []
    for edge in graph_obj.edges:
        source = edge.get("src", edge.get("source")) if isinstance(edge, dict) else edge.source
        target = edge.get("dst", edge.get("target")) if isinstance(edge, dict) else edge.target
        edge_type = edge.get("type", "unknown") if isinstance(edge, dict) else edge.type
        edges.append({
            "src": source,
            "dst": target,
            "type": str(getattr(edge_type, "value", edge_type)),
        })
        
    data = {
        "nodes": nodes,
        "edges": edges,
    }
    out = Path(output_path)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Exported {len(data['nodes'])} nodes, {len(data['edges'])} edges -> {out.resolve()}")
    return out
