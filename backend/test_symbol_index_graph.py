from app.scanner.scanner import ProjectScanner

scanner = ProjectScanner()

_, index = scanner.scan(".")

print("\nIndexed Symbols\n")

for symbol in index.symbol_index.qualified_symbols.values():

    print(
        f"{symbol.symbol_type:10}"
        f"{symbol.qualified_name}"
    )