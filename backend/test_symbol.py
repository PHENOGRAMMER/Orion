from pathlib import Path

from app.scanner.scanner import ProjectScanner

scanner = ProjectScanner()

repo_root = Path(__file__).resolve().parents[1]

scan_result, _ = scanner.scan(repo_root)

for file, symbols in scan_result.symbol_graph.files.items():

    print(f"\n{'=' * 70}")
    print(file)

    if symbols.imports:
        print("\nImports:")
        for imp in symbols.imports:
            if imp.name:
                print(
                    f"  • from {'.' * imp.relative_level}{imp.module} "
                    f"import {imp.name}"
                    + (
                        f" as {imp.alias}"
                        if imp.alias
                        else ""
                    )
                )

            else:
                print(
                    f"  • import {imp.module}"
                    + (
                        f" as {imp.alias}"
                        if imp.alias
                        else ""
                    )
                )

    if symbols.classes:
        print("\nClasses:")
        for cls in symbols.classes:
            print(f"  • {cls.name}")

            if cls.methods:
                print("    Methods:")
                for method in cls.methods:
                    print(f"      - {method.name}")

    if symbols.functions:
        print("\nFunctions:")
        for func in symbols.functions:
            print(f"  • {func.name}")

    if symbols.variables:
        print("\nVariables:")
        for var in symbols.variables:
            print(f"  • {var.name}")