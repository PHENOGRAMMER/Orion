from pathlib import Path

from app.scanner.scanner import ProjectScanner


def main() -> None:
    scanner = ProjectScanner()
    result, _index = scanner.scan(
        Path(__file__).resolve().parent.parent,
        time_zone="GMT",
    )

    print(result.model_dump_json(indent=4))


if __name__ == "__main__":
    main()
