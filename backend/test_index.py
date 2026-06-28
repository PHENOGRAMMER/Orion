from app.scanner.index_builder import ProjectIndexBuilder
from app.scanner.scanner import ProjectScanner

scanner = ProjectScanner()

scan_result, index = scanner.scan(
    r"C:\\Users\\cools\\OneDrive\\Desktop\\Orion"
)

builder = ProjectIndexBuilder()

index = builder.build(scan_result)

print(scan_result.git_statistics)
print(scan_result.statistics)
print(scan_result.framework_statistics)
print(index.files_by_name.keys())
print(index.files_by_extension.keys())
print(index.directories)
print(index.config_files.keys())