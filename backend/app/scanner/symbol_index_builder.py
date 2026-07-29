"""
Builds the project-wide SymbolIndex.
"""

from __future__ import annotations

from pathlib import Path

from app.scanner.import_resolver.models import ModuleInfo
from app.scanner.models import (
    ProjectScanResult,
)

from app.scanner.symbol_index import (
    SymbolIndex,
    SymbolInfo,
)


class SymbolIndexBuilder:
    """
    Builds a fast lookup index for all symbols in a project.
    """

    def build(
        self,
        scan_result: ProjectScanResult,
        module_index: dict[str, ModuleInfo],
    ) -> SymbolIndex:

        index = SymbolIndex()

        project_root = Path(scan_result.root_path).resolve()

        path_to_module = {
            module.path: module.name
            for module in module_index.values()
        }

        for file_path, file_symbols in scan_result.symbol_graph.files.items():

            abs_path = (project_root / file_path).resolve()
            
            module_name = path_to_module.get(abs_path)

            if module_name is None:
                continue

            #
            # Classes
            #

            for cls in file_symbols.classes:

                index.add(
                    SymbolInfo(
                        name=cls.name,
                        qualified_name=f"{module_name}.{cls.name}",
                        path=Path(file_path),
                        module=module_name,
                        line=cls.line,
                        symbol_type="class",
                    )
                )

            #
            # Functions
            #

            for fn in file_symbols.functions:

                index.add(
                    SymbolInfo(
                        name=fn.name,
                        qualified_name=f"{module_name}.{fn.name}",
                        path=Path(file_path),
                        module=module_name,
                        line=fn.line,
                        symbol_type="function",
                    )
                )

            #
            # Methods
            #

            for cls in file_symbols.classes:

                for method in cls.methods:

                    index.add(
                        SymbolInfo(
                            name=method.name,
                            qualified_name=f"{module_name}.{cls.name}.{method.name}",
                            path=Path(file_path),
                            module=module_name,
                            line=method.line,
                            symbol_type="method",
                        )
                    )

            #
            # Variables
            #

            for variable in file_symbols.variables:

                index.add(
                    SymbolInfo(
                        name=variable.name,
                        qualified_name=f"{module_name}.{variable.name}",
                        path=Path(file_path),
                        module=module_name,
                        line=variable.line,
                        symbol_type="variable",
                    )
                )

        return index