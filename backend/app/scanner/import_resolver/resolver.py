"""
Import Resolver.

Coordinates module and symbol resolution.
"""

from __future__ import annotations

from pathlib import Path

from app.scanner.index import ProjectIndex
from app.scanner.models import ProjectScanResult

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

            absolute_file = (
                Path(result.root_path) / file_path
            ).resolve()

            module = self._module_name(
                absolute_file,
                index,
                result,
            )

            if module is None:
                continue

            for import_symbol in file_symbols.imports:

                self.module_resolver.resolve(
                    current_module=module,
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
        file_path,
        index,
        result,
    ):
        """
        Returns the ModuleInfo corresponding to a file path.
        """

        file_path = Path(file_path)

        # Fast path: ProjectIndexBuilder records this mapping while building
        # the module index. The old implementation scanned every module for
        # every file, which becomes prohibitively expensive on large repos.
        direct = index.module_by_path.get(str(file_path.resolve()).lower())
        if direct is not None:
            return direct

        for module_name, module in index.module_index.items():

            module_path = Path(module.path)

            file_resolved = file_path
            module_resolved = module_path

            # Exact match
            if module_resolved == file_resolved:
                return module

            # Relative suffix match
            if module_resolved.as_posix().endswith(
                file_resolved.as_posix()
            ):
                return module

            # Fallback substring match
            if file_resolved.as_posix() in module_resolved.as_posix():
                return module
        return None
