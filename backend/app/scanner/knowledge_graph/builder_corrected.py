"""
Knowledge Graph Builder.

Builds a project knowledge graph from a ProjectScanResult.
"""

from __future__ import annotations

from app.scanner.knowledge_graph import graph
from pathlib import Path

from app.scanner.index import ProjectIndex
from app.scanner.models import ProjectScanResult

from .graph import KnowledgeGraph
from .models import (
    EdgeType,
    GraphEdge,
    GraphNode,
    NodeType,
)


class KnowledgeGraphBuilder:
    """
    Converts scanner output into a KnowledgeGraph.
    """

    def build(
        self,
        result: ProjectScanResult,
        index: ProjectIndex,
    ) -> KnowledgeGraph:

        graph = KnowledgeGraph()

        #
        # File -> Module lookup
        #

        module_lookup = {
            module.path.resolve(): module
            for module in index.module_index.values()
        }

        #
        # Files
        #

        for file in result.files:

            node = GraphNode(
                id=f"file:{file.path}",
                type=NodeType.FILE,
                name=Path(file.path).name,
                path=Path(file.path),
            )

            graph.add_node(node)

        #
        # Modules
        #

        for module in index.module_index.values():

            module_node = GraphNode(
                id=f"module:{module.name}",
                type=NodeType.MODULE,
                name=module.name,
                qualified_name=module.name,
                path=module.path,
            )

            graph.add_node(module_node)

            #
            # File -> Module
            #

            relative_path = module.path.relative_to(
                Path(result.root_path).resolve()
            )

            file_id = f"file:{relative_path.as_posix()}"

            if graph.has_node(file_id):

                graph.add_edge(
                    GraphEdge(
                        source=file_id,
                        target=module_node.id,
                        type=EdgeType.DECLARES,
                    )
                )

        #
        # Symbols
        #

        symbol_type_map = {
            "class": NodeType.CLASS,
            "function": NodeType.FUNCTION,
            "method": NodeType.METHOD,
            "variable": NodeType.VARIABLE,
        }

        for symbol in index.symbol_index.qualified_symbols.values():

            #
            # Skip unknown symbols.
            #

            node_type = symbol_type_map.get(
                symbol.symbol_type.lower()
            )

            if node_type is None:
                continue

            symbol_node = GraphNode(
                id=f"symbol:{symbol.qualified_name}",
                type=node_type,
                name=symbol.name,
                qualified_name=symbol.qualified_name,
                path=symbol.path,
                line=symbol.line,
            )

            graph.add_node(symbol_node)

            module_id = f"module:{symbol.module}"

            if graph.has_node(module_id):

                graph.add_edge(
                    GraphEdge(
                        source=module_id,
                        target=symbol_node.id,
                        type=EdgeType.DECLARES,
                    )
                )

        #
        # Imports
        #

        for file_path, file_symbols in result.symbol_graph.files.items():

            source_file = f"file:{file_path}"

            if not graph.has_node(source_file):
                continue

            for imp in file_symbols.imports:

                if imp.resolved_file is None:
                    continue

                target = f"file:{imp.resolved_file}"

                if not graph.has_node(target):
                    continue

                graph.add_edge(
                    GraphEdge(
                        source=source_file,
                        target=target,
                        type=EdgeType.IMPORTS,
                    )
                )

        #
        # Module imports
        #

        for file_symbols in result.symbol_graph.files.values():

            source_module = module_lookup.get(
                Path(file_symbols.path).resolve()
            )

            if source_module is None:
                continue

            source_id = f"module:{source_module.name}"

            for imp in file_symbols.imports:

                resolved_module = getattr(
                    imp,
                    "resolved_module",
                    None,
                )

                if resolved_module is None:
                    continue

                target_id = f"module:{resolved_module}"

                if not graph.has_node(target_id):
                    continue

                graph.add_edge(
                    GraphEdge(
                        source=source_id,
                        target=target_id,
                        type=EdgeType.IMPORTS,
                    )
                )

        count = sum(
            1
            for edge in graph.edges
            if edge.type == EdgeType.IMPORTS
        )

        print(f"IMPORT EDGES: {count}")

        return graph