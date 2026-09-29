"""
Knowledge Graph Query Layer.

Answers structural questions about a project using the KnowledgeGraph.
All public methods accept fully-qualified symbol names and return plain
data structures suitable for direct JSON serialisation.
"""

from __future__ import annotations

from collections import deque

from .graph import KnowledgeGraph
from .models import EdgeType, GraphNode


class KnowledgeGraphQuery:
    """
    Thin query layer over a KnowledgeGraph.

    Usage:
        query = KnowledgeGraphQuery(index.knowledge_graph)
        query.callers_of("app.scanner.scanner.ProjectScanner.scan")
        query.impact_of("app.scanner.symbol_index.SymbolIndex.lookup")
    """

    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph

    # ------------------------------------------------------------------
    # Symbol info
    # ------------------------------------------------------------------

    def get_symbol(self, qualified_name: str) -> GraphNode | None:
        """
        Return the node for a fully-qualified symbol, or None if not found.
        """
        return self.graph.get_node(f"symbol:{qualified_name}")

    # ------------------------------------------------------------------
    # Direct call relationships
    # ------------------------------------------------------------------

    def callers_of(self, qualified_name: str) -> list[GraphNode]:
        """
        Return every symbol that directly calls qualified_name.
        """
        node_id = f"symbol:{qualified_name}"
        return [
            node
            for edge in self.graph.incoming(node_id)
            if edge.type == EdgeType.CALLS
            for node in (self.graph.get_node(edge.source),)
            if node is not None
        ]

    def callees_of(self, qualified_name: str) -> list[GraphNode]:
        """
        Return every symbol that qualified_name directly calls.
        """
        node_id = f"symbol:{qualified_name}"
        return [
            node
            for edge in self.graph.outgoing(node_id)
            if edge.type == EdgeType.CALLS
            for node in (self.graph.get_node(edge.target),)
            if node is not None
        ]

    # ------------------------------------------------------------------
    # Transitive dependencies
    # ------------------------------------------------------------------

    def dependencies_of(
        self,
        qualified_name: str,
        *,
        max_depth: int = 10,
    ) -> list[GraphNode]:
        """
        Return all symbols reachable from qualified_name via CALLS edges
        (i.e. everything this symbol transitively depends on).

        Results are in breadth-first order. Cycles are handled safely.
        max_depth caps traversal to avoid runaway on very deep graphs.
        """
        start = f"symbol:{qualified_name}"
        visited: set[str] = {start}
        queue: deque[tuple[str, int]] = deque([(start, 0)])
        result: list[GraphNode] = []

        while queue:
            node_id, depth = queue.popleft()

            if depth >= max_depth:
                continue

            for edge in self.graph.outgoing(node_id):
                if edge.type != EdgeType.CALLS:
                    continue
                if edge.target in visited:
                    continue

                visited.add(edge.target)
                node = self.graph.get_node(edge.target)
                if node is not None:
                    result.append(node)
                    queue.append((edge.target, depth + 1))

        return result

    # ------------------------------------------------------------------
    # Impact analysis
    # ------------------------------------------------------------------

    def impact_of(self, qualified_name: str, *, max_depth: int = 10) -> dict:
        """
        If qualified_name changes, what is affected?

        Returns a dict with:
            symbol          — the symbol itself (or None)
            direct_callers  — list of GraphNode
            all_callers     — list of GraphNode (transitive, BFS)
            affected_modules — sorted list of module names
            affected_files   — sorted list of file paths
            direct_count    — int
            total_count     — int
        """
        start = f"symbol:{qualified_name}"
        symbol_node = self.graph.get_node(start)

        visited: set[str] = {start}
        queue: deque[tuple[str, int]] = deque([(start, 0)])
        all_callers: list[GraphNode] = []
        direct_callers: list[GraphNode] = []

        while queue:
            node_id, depth = queue.popleft()

            if depth >= max_depth:
                continue

            for edge in self.graph.incoming(node_id):
                if edge.type != EdgeType.CALLS:
                    continue
                if edge.source in visited:
                    continue

                visited.add(edge.source)
                node = self.graph.get_node(edge.source)
                if node is None:
                    continue

                all_callers.append(node)
                if depth == 0:
                    direct_callers.append(node)

                queue.append((edge.source, depth + 1))

        #
        # Read the module straight off the node.
        #
        # This used to be qualified_name.rsplit(".", 2)[0] guarded by
        # count(".") >= 2, which was wrong twice over: it dropped every
        # symbol with fewer than two dots, and for a top-level function
        # "a.b.c.func" it returned "a.b" instead of "a.b.c".
        #
        affected_modules = sorted({
            node.module
            for node in all_callers
            if node.module
        })

        affected_files = sorted({
            str(node.path)
            for node in all_callers
            if node.path is not None
        })

        return {
            "symbol":           symbol_node,
            "direct_callers":   direct_callers,
            "all_callers":      all_callers,
            "affected_modules": affected_modules,
            "affected_files":   affected_files,
            "direct_count":     len(direct_callers),
            "total_count":      len(all_callers),
        }

    # ------------------------------------------------------------------
    # Path finding
    # ------------------------------------------------------------------

    def _resolve_symbol_key(self, symbol: str) -> str | None:
        """Resolve a bare symbol name, or a symbol-prefixed node id, to a graph key."""
        if not symbol:
            return None

        if symbol in self.graph.nodes:
            return symbol

        if symbol.startswith("symbol:"):
            return symbol if symbol in self.graph.nodes else None

        candidates = [
            f"symbol:{symbol}",
            f"file:{symbol}",
        ]
        for candidate in candidates:
            if candidate in self.graph.nodes:
                return candidate

        tail = symbol.split(".")[-1]
        matches = [
            node_id
            for node_id in self.graph.nodes
            if node_id.endswith(f".{tail}") or node_id.endswith(f":{tail}")
        ]
        return matches[0] if len(matches) == 1 else None

    def path_between(
        self,
        from_symbol: str,
        to_symbol: str,
        *,
        max_depth: int = 15,
    ) -> list[str] | None:
        """
        Return the shortest call path from from_symbol to to_symbol as a
        list of qualified names, or None if no path exists.

        Example:
            ["app.scanner.scanner.ProjectScanner.scan",
             "app.scanner.symbol_index_builder.SymbolIndexBuilder.build",
             "app.scanner.symbol_index.SymbolIndex.add"]
        """
        start = self._resolve_symbol_key(from_symbol)
        goal = self._resolve_symbol_key(to_symbol)

        if start is None or goal is None:
            return None

        if start == goal:
            node = self.graph.get_node(start)
            qualified = node.qualified_name if node and node.qualified_name else start.removeprefix("symbol:")
            return [qualified] if qualified else None

        # BFS — track the path taken to each visited node
        visited: set[str] = {start}
        queue: deque[list[str]] = deque([[start]])

        while queue:
            path = queue.popleft()
            current = path[-1]

            if len(path) > max_depth:
                continue

            for edge in self.graph.outgoing(current):
                if edge.type != EdgeType.CALLS:
                    continue
                if edge.target in visited:
                    continue

                new_path = path + [edge.target]

                if edge.target == goal:
                    return [
                        (
                            node.qualified_name
                            if node and node.qualified_name
                            else node_id.removeprefix("symbol:")
                        )
                        for node_id, node in (
                            (nid, self.graph.get_node(nid)) for nid in new_path
                        )
                        if node is not None
                    ]

                visited.add(edge.target)
                queue.append(new_path)

        return None

    # ------------------------------------------------------------------
    # Module-level queries
    # ------------------------------------------------------------------

    def symbols_in_module(self, module_name: str) -> list[GraphNode]:
        """
        Return all symbol nodes declared by a module.
        """
        module_id = f"module:{module_name}"
        return [
            node
            for edge in self.graph.outgoing(module_id)
            if edge.type == EdgeType.DECLARES
            for node in (self.graph.get_node(edge.target),)
            if node is not None and edge.target.startswith("symbol:")
        ]

    def imports_of_module(self, module_name: str) -> list[GraphNode]:
        """
        Return all modules that module_name imports.
        """
        module_id = f"module:{module_name}"
        return [
            node
            for edge in self.graph.outgoing(module_id)
            if edge.type == EdgeType.IMPORTS
            for node in (self.graph.get_node(edge.target),)
            if node is not None
        ]

    def imported_by_module(self, module_name: str) -> list[GraphNode]:
        """
        Return all modules that import module_name.
        """
        module_id = f"module:{module_name}"
        return [
            node
            for edge in self.graph.incoming(module_id)
            if edge.type == EdgeType.IMPORTS
            for node in (self.graph.get_node(edge.source),)
            if node is not None
        ]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """
        Summary statistics for the graph.

        Returns node/edge counts by type, plus the top 5 most-called symbols
        (highest incoming call edges) and top 5 callers (highest outgoing).
        """
        from collections import Counter
        node_counts = Counter(node.type.value for node in self.graph.nodes.values())
        edge_counts  = Counter(edge.type.value for edge in self.graph.edges)

        call_in: Counter[str] = Counter()
        call_out: Counter[str] = Counter()
        for edge in self.graph.edges:
            if edge.type == EdgeType.CALLS:
                call_in[edge.target] += 1
                call_out[edge.source] += 1

        def _top(counter: Counter, n: int = 5) -> list[dict]:
            result = []
            for node_id, count in counter.most_common(n):
                node = self.graph.get_node(node_id)
                if node and node.qualified_name:
                    result.append({
                        "qualified_name": node.qualified_name,
                        "type": node.type.value,
                        "count": count,
                    })
            return result

        return {
            "nodes":        self.graph.node_count,
            "edges":        self.graph.edge_count,
            "by_node_type": dict(node_counts),
            "by_edge_type": dict(edge_counts),
            "top_called":   _top(call_in),
            "top_callers":  _top(call_out),
        }