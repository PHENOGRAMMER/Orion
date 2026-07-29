"""
Knowledge Graph.

Stores nodes and edges and provides fast graph traversal.
"""

from __future__ import annotations

from collections import defaultdict

from .models import GraphEdge, GraphNode


class KnowledgeGraph:
    """
    In-memory directed graph representing the project.
    """

    def __init__(self) -> None:

        #
        # Node ID -> Node
        #
        self.nodes: dict[str, GraphNode] = {}

        #
        # All graph edges
        #
        self.edges: list[GraphEdge] = []

        #
        # Outgoing adjacency list
        #
        self._outgoing: dict[str, list[GraphEdge]] = defaultdict(list)

        #
        # Incoming adjacency list
        #
        self._incoming: dict[str, list[GraphEdge]] = defaultdict(list)

    def add_node(
        self,
        node: GraphNode,
    ) -> None:
        """
        Add or replace a node.
        """

        self.nodes[node.id] = node

    def add_edge(
        self,
        edge: GraphEdge,
    ) -> None:
        """
        Add a directed edge.
        """

        #
        # Ignore edges whose endpoints do not exist.
        #

        if edge.source not in self.nodes:
            return

        if edge.target not in self.nodes:
            return

        #
        # Prevent duplicate edges.
        #

        if self.has_edge(edge.source, edge.target):
            return

        self.edges.append(edge)

        self._outgoing[edge.source].append(edge)

        self._incoming[edge.target].append(edge)

    def get_node(
        self,
        node_id: str,
    ) -> GraphNode | None:
        """
        Lookup a node.
        """

        return self.nodes.get(node_id)

    def outgoing(
        self,
        node_id: str,
    ) -> list[GraphEdge]:
        """
        All outgoing edges.
        """

        return self._outgoing.get(node_id, [])

    def incoming(
        self,
        node_id: str,
    ) -> list[GraphEdge]:
        """
        All incoming edges.
        """

        return self._incoming.get(node_id, [])

    def neighbors(
        self,
        node_id: str,
    ) -> list[GraphNode]:
        """
        All directly connected destination nodes.
        """

        result: list[GraphNode] = []

        for edge in self.outgoing(node_id):

            node = self.get_node(edge.target)

            if node is not None:

                result.append(node)

        return result

    def has_node(
        self,
        node_id: str,
    ) -> bool:
        """
        Check whether a node exists.
        """

        return node_id in self.nodes

    def has_edge(
        self,
        source: str,
        target: str,
    ) -> bool:
        """
        Check whether an edge already exists.
        """

        return any(
            edge.target == target
            for edge in self._outgoing.get(source, [])
        )

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)