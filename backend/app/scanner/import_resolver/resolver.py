"""
Import Resolver.

Coordinates module and symbol resolution.
"""

from __future__ import annotations

from pathlib import Path

from app.scanner.index import ProjectIndex
from app.scanner.models import ProjectScanResult

from .models import ModuleInfo
from .module_resolver import ModuleResolver
from .symbol_resolver import SymbolResolver


class ImportResolver:
    """
    Resolves every import inside the project.
    """

    def __init__(self) -> None:

        self.module_resolver = ModuleResolver()

        self.symbol_resolver = SymbolResolver()

    def resolve(
        self,
        result: ProjectScanResult,
        index: ProjectIndex,
    ) -> ProjectScanResult:

        for file_path, file_symbols in result.symbol_graph.files.items():

            module = self._module_name(
                Path(file_path),
                index,
            )

            if module is None:
                continue

            #
            # Resolve Modules.
            #

            for import_symbol in file_symbols.imports:

                self.module_resolver.resolve(
                    current_module=module.name,
                    import_symbol=import_symbol,
                    index=index,
                )

                self.symbol_resolver.resolve(
                    import_symbol=import_symbol,
                    symbol_index=index.symbol_index,
                )

        return result

    def _module_name(
        self,
        file_path: Path,
        index: ProjectIndex,
    ) -> ModuleInfo | None:
        """
        Convert a file path back into a module info.
        """

        for module in index.module_index.values():

            if module.path == file_path:

                return module

        return None