from app.scanner.index_builder import ProjectIndexBuilder
from app.scanner.scanner import ProjectScanner

scanner = ProjectScanner()

scan_result, index = scanner.scan(
    r"C:\\Users\\cools\\OneDrive\\Desktop\\Orion"
)

builder = ProjectIndexBuilder()

index = builder.build(scan_result)

print("\nDependency Graph")

for file, node in scan_result.dependency_graph.nodes.items():
    print(f"\n{file}")

    for imp in node.imports:
        print(f"   -> {imp}")

print(scan_result.git_statistics)
print(scan_result.statistics)
print(scan_result.framework_statistics)
print(index.files_by_name.keys())
print(index.files_by_extension.keys())
print(index.directories)
print(index.config_files.keys())