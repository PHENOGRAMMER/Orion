"""
Knowledge Graph Builder.

Builds a project knowledge graph from a ProjectScanResult.
"""


from __future__ import annotations

from pathlib import Path

from app.scanner.index import ProjectIndex
from app.scanner.models import ProjectScanResult
from app.scanner.call_graph.models import ResolvedCall

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
        resolved_calls: list[ResolvedCall] | None = None,
    ) -> KnowledgeGraph:

        graph = KnowledgeGraph()

        #
        # File -> Module lookup
        #

        module_lookup = {
            module.path.resolve(): module
            for module in index.module_index.values()
        }

        root_path = Path(result.root_path).resolve()

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
                module=module.name,
                path=module.path,
            )

            graph.add_node(module_node)

            #
            # File -> Module edge
            #

            try:
                relative_path = module.path.relative_to(root_path)
                file_id = f"file:{relative_path.as_posix()}"

                if graph.has_node(file_id):
                    graph.add_edge(
                        GraphEdge(
                            source=file_id,
                            target=module_node.id,
                            type=EdgeType.DECLARES,
                        )
                    )
            except ValueError:
                pass

        #
        # Symbols
        #

        symbol_type_map = {
            "class":    NodeType.CLASS,
            "function": NodeType.FUNCTION,
            "method":   NodeType.METHOD,
            "variable": NodeType.VARIABLE,
        }

        for symbol in index.symbol_index.qualified_symbols.values():

            node_type = symbol_type_map.get(symbol.symbol_type.lower())

            if node_type is None:
                continue

            symbol_node = GraphNode(
                id=f"symbol:{symbol.qualified_name}",
                type=node_type,
                name=symbol.name,
                qualified_name=symbol.qualified_name,
                module=symbol.module,
                path=symbol.path,
                line=symbol.line,
                end_line=symbol.end_line
            )

            graph.add_node(symbol_node)

            #
            # Module -> Symbol edge
            #

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
        # File-level import edges
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
        # Module-level import edges
        #

        for file_symbols in result.symbol_graph.files.values():

            source_module = module_lookup.get(
                Path(file_symbols.path).resolve()
            )

            if source_module is None:
                continue

            source_id = f"module:{source_module.name}"

            for imp in file_symbols.imports:

                #
                # Prefer the resolver's answer, then fall back to the raw
                # import name — that still connects a plain "import a.b.c"
                # of a first-party module the resolver did not annotate.
                #
                # Whichever lands first wins; the old version of this loop
                # fell through to a "module:None" lookup that could never
                # match, so the fallback was effectively dead code.
                #
                for candidate in (getattr(imp, "resolved_module", None), imp.module):

                    if not candidate:
                        continue

                    target_id = f"module:{candidate}"

                    if graph.has_node(target_id):
                        graph.add_edge(
                            GraphEdge(
                                source=source_id,
                                target=target_id,
                                type=EdgeType.IMPORTS,
                            )
                        )
                        break

        #
        # Call edges
        #
        # Each ResolvedCall carries a caller_symbol and callee_symbol that are
        # fully-qualified project symbol names, e.g.:
        #
        #   app.scanner.scanner.ProjectScanner.scan
        #   app.scanner.symbol_index_builder.SymbolIndexBuilder.build
        #

        for call in (resolved_calls or []):

            source_id = f"symbol:{call.caller_symbol}"
            target_id = f"symbol:{call.callee_symbol}"

            if graph.has_node(source_id) and graph.has_node(target_id):
                graph.add_edge(
                    GraphEdge(
                        source=source_id,
                        target=target_id,
                        type=EdgeType.CALLS,
                        metadata={
                            "file": str(call.file),
                            "line": str(call.line),
                        },
                    )
                )

        return graph
