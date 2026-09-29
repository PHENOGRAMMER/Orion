from pathlib import Path
import io
import sys
from contextlib import redirect_stdout

from app.scanner.scanner import ProjectScanner
from app.scanner.call_graph.builder import CallGraphBuilder
from app.scanner.call_graph.resolver import CallResolver


def main():

    if len(sys.argv) != 2:
        print("Usage:")
        print("python backend/test_call_resolver.py <project_path>")
        return

    project = Path(sys.argv[1]).resolve()
    Path("unresolved_calls.txt").write_text("", encoding="utf-8")

    scanner = ProjectScanner()

    sink = io.StringIO()

    with redirect_stdout(sink):
        scan_result, index = scanner.scan(project)

        builder = CallGraphBuilder()

        raw_calls = builder.build(index.module_index)

        resolver = CallResolver(index.symbol_index, scan_result)

        resolved_calls = resolver.resolve(raw_calls)

    print(f"Raw Calls      : {len(raw_calls)}")
    print(f"Resolved Calls : {len(resolved_calls)}")
    print(f"Unresolved Object Calls: {resolver.unresolved_calls}")
    print(f"foo()          : {resolver.simple_calls}")
    print(f"self.foo()     : {resolver.self_calls}")
    print(f"obj.foo()      : {resolver.attribute_calls}")


if __name__ == "__main__":
    main()