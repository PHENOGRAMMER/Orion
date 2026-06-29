from app.scanner.scanner import ProjectScanner

scanner = ProjectScanner()

result, index = scanner.scan(
    r"C:\\Users\\cools\\OneDrive\\Desktop\\Orion",
    time_zone="GMT",
)

print(result.model_dump_json(indent=4))