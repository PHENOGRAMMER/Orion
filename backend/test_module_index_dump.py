from app.scanner.scanner import ProjectScanner

scanner = ProjectScanner()

_, index = scanner.scan(".")

print("\n========== MODULE INDEX ==========\n")

for key, value in index.module_index.items():
    print(
        f"KEY={key!r}"
        f"   NAME={value.name!r}"
        f"   PACKAGE={value.package!r}"
        f"   PATH={value.path}"
    )

print("\nTotal:", len(index.module_index))