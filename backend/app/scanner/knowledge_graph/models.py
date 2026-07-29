"""
Models for the project knowledge graph.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """
    Types of nodes stored in the knowledge graph.
    """

    PROJECT = "project"

    DIRECTORY = "directory"

    FILE = "file"

    MODULE = "module"

    CLASS = "class"

    FUNCTION = "function"

    METHOD = "method"

    VARIABLE = "variable"


class EdgeType(str, Enum):
    """
    Relationships between nodes.
    """

    CONTAINS = "contains"

    DECLARES = "declares"

    IMPORTS = "imports"

    CALLS = "calls"

    INHERITS = "inherits"

    REFERENCES = "references"

    USES = "uses"


class GraphNode(BaseModel):
    """
    A node inside the knowledge graph.
    """

    id: str

    type: NodeType

    name: str

    path: Path | None = None

    qualified_name: str | None = None

    line: int | None = None

    metadata: dict[str, str] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """
    A directed relationship between two nodes.
    """

    source: str

    target: str

    type: EdgeType

    metadata: dict[str, str] = Field(default_factory=dict)