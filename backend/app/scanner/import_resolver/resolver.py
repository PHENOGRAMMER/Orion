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
                print(f"[WARN] No module found for: {file_path}")
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
        file_path: Path,
        index: ProjectIndex,
    ) -> ModuleInfo | None:
        """
        Convert a file path back into ModuleInfo.
        """

        # Normalize the incoming path.
        try:
            file_path = file_path.resolve(strict=False)
        except Exception:
            file_path = Path(file_path)

        for module in index.module_index.values():

            module_path = module.path

            try:
                module_path = module_path.resolve(strict=False)
            except Exception:
                pass

            if module_path == file_path:
                return module

            # Fallback for relative/absolute path mismatches.
            if module.path.as_posix().endswith(file_path.as_posix()):
                return module

        return None