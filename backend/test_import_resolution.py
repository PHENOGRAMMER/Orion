from app.scanner.scanner import ProjectScanner

scanner = ProjectScanner()

scan_result, _ = scanner.scan(".")

for file_name, symbols in scan_result.symbol_graph.files.items():

    print("\n" + "=" * 70)
    print(file_name)

    for imp in symbols.imports:

        print()

        print("Import:")
        print("  module :", imp.module)
        print("  name   :", imp.name)
        print("  file   :", imp.resolved_file)
        print("  symbol :", imp.resolved_symbol)
        print("  type   :", imp.resolved_symbol_type)