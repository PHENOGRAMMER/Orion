from app.scanner.scanner import ProjectScanner

scanner = ProjectScanner()

_, index = scanner.scan(".")

print("Source Roots")
print(index.source_roots)

print()

print("Module Index")
print(index.module_index)