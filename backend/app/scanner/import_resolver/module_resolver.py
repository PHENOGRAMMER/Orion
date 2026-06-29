"""
Module resolver.

Resolves imported Python modules to files inside the project.
"""

from __future__ import annotations

from pathlib import Path

from app.scanner.index import ProjectIndex
from app.scanner.models import (
    ImportSymbol,
    ProjectScanResult,
)


class ModuleResolver:
    """
    Resolves imported modules using the project's module index.

    Example
    -------
    app.scanner.models

        ↓

    backend/app/scanner/models.py
    """

    def resolve(
        self,
        result: ProjectScanResult,
        index: ProjectIndex,
    ) -> ProjectScanResult:

        for file_symbols in result.symbol_graph.files.values():

            for import_symbol in file_symbols.imports:

                self._resolve_import(
                    import_symbol,
                    index,
                )

        return result

    def _resolve_import(
        self,
        import_symbol: ImportSymbol,
        index: ProjectIndex,
    ) -> None:
        """
        Resolve a single import.
        """

        #
        # import pathlib
        #

        if import_symbol.module in index.module_index:

            import_symbol.resolved_file = (
                index.module_index[import_symbol.module]
            )

            return

        #
        # from app.scanner import models
        #
        # module = app.scanner
        # name   = models
        #

        if import_symbol.name:

            full_module = (
                f"{import_symbol.module}.{import_symbol.name}"
            )

            if full_module in index.module_index:

                import_symbol.resolved_file = (
                    index.module_index[full_module]
                )

                return

        #
        # Relative imports are handled later.
        #