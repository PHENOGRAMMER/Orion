from pathlib import Path

from app.scanner.call_graph.builder import CallGraphBuilder


def main():
    project_root = Path("backend")

    python_files = list(project_root.rglob("*.py"))

    builder = CallGraphBuilder()
    calls = builder.build(python_files)

    print("=" * 80)
    print("CALL GRAPH")
    print("=" * 80)

    print(f"Python Files : {len(python_files)}")
    print(f"Calls Found  : {len(calls)}")
    print()

    for call in calls[:50]:
        print(
            f"{call.caller:35} -> {call.callee:25} ({call.file}:{call.line})"
        )


if __name__ == "__main__":
    main()