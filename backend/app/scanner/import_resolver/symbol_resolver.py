"""
Symbol resolver.

Resolves imported names to project symbols.
"""

from __future__ import annotations

from app.scanner.models import (
    ImportSymbol,
    ProjectScanResult,
)


class SymbolResolver:
    """
    Resolve imported symbols after modules have been resolved.
    """

    def resolve(
        self,
        result: ProjectScanResult,
    ) -> ProjectScanResult:

        for file_symbols in result.symbol_graph.files.values():

            for import_symbol in file_symbols.imports:

                self._resolve_import(
                    import_symbol,
                    result,
                )

        return result

    def _resolve_import(
        self,
        import_symbol: ImportSymbol,
        result: ProjectScanResult,
    ) -> None:

        if (
            import_symbol.resolved_file is None
            or import_symbol.name is None
        ):
            return

        target = result.symbol_graph.files.get(
            import_symbol.resolved_file.as_posix()
        )

        if target is None:
            return

        #
        # Classes
        #

        for cls in target.classes:

            if cls.name == import_symbol.name:

                import_symbol.resolved_symbol = cls.name
                import_symbol.resolved_symbol_type = "class"
                return

        #
        # Functions
        #

        for fn in target.functions:

            if fn.name == import_symbol.name:

                import_symbol.resolved_symbol = fn.name
                import_symbol.resolved_symbol_type = "function"
                return

        #
        # Variables
        #

        for var in target.variables:

            if var.name == import_symbol.name:

                import_symbol.resolved_symbol = var.name
                import_symbol.resolved_symbol_type = "variable"
                return