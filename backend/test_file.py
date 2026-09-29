import ast
from pathlib import Path

from app.scanner.call_graph.visitor import CallVisitor


def main() -> None:
    source_path = Path(__file__).resolve().parent / "test_ast.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    visitor = CallVisitor(
        file_path=source_path,
        module="backend.test_ast",
    )

    visitor.visit(tree)

    print(visitor.local_variable_types)

    for call in visitor.calls:
        print(call)


if __name__ == "__main__":
    main()
