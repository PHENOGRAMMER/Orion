from app.scanner.scanner import ProjectScanner

scanner = ProjectScanner()

result, index = scanner.scan(".")

print("\n========== IMPORT RESOLUTION ==========\n")

resolved = 0
unresolved = 0

for file_symbols in result.symbol_graph.files.values():

    print(f"\n{file_symbols.path}")

    for imp in file_symbols.imports:

        if imp.resolved_file is not None:
            resolved += 1
            status = "✓"
        else:
            unresolved += 1
            status = "✗"

        print(
            f"{status} "
            f"module={imp.module!r} "
            f"name={imp.name!r} "
            f"resolved_module={getattr(imp, 'resolved_module', None)!r} "
            f"resolved_file={imp.resolved_file!r}"
        )

print("\n====================================")
print(f"Resolved   : {resolved}")
print(f"Unresolved : {unresolved}")
print(f"Total      : {resolved + unresolved}")