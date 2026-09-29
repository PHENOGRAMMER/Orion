"""
Test the ModuleResolver.

Shows how every import is resolved to a project module.
"""

from pathlib import Path

from app.scanner.import_resolver.module_resolver import ModuleResolver
from app.scanner.scanner import ProjectScanner


def main() -> None:
    scanner = ProjectScanner()

    scan_result, index = scanner.scan(".")

    resolver = ModuleResolver()

    print("\nModule Resolution\n")

    for file_path, file_symbols in scan_result.symbol_graph.files.items():

        #
        # Normalize the path coming from the SymbolGraph.
        #

        current_path = Path(file_path).resolve()

        current_module = None

        #
        # Find the ModuleInfo corresponding to this file.
        #

        for module_info in index.module_index.values():

            if module_info.path.resolve() == current_path:

                current_module = module_info

                break

        if current_module is None:

            print(f"Could not locate ModuleInfo for {file_path}")

            continue

        print(f"\n{current_module.name}")

        if not file_symbols.imports:

            print("  (no imports)")
            continue

        for import_symbol in file_symbols.imports:

            result = resolver.resolve(
                current_module=current_module,
                import_symbol=import_symbol,
                index=index,
            )

            if result.resolved and result.resolved_module:

                print(f"  OK {result.module}")
                print(f"      module   : {result.resolved_module.name}")
                print(f"      package  : {result.resolved_module.package}")
                print(f"      file     : {result.resolved_module.path}")
                print(f"      package? : {result.resolved_module.is_package}")

            else:

                print(f"  NO {result.module}")


if __name__ == "__main__":
    main()
