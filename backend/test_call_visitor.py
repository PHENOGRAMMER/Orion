import ast
from pathlib import Path

from app.scanner.call_graph.visitor import CallVisitor


def main():
    file_path = Path("backend/test_ast.py")

    source = file_path.read_text(encoding="utf-8")

    tree = ast.parse(source)

    visitor = CallVisitor(
        file_path=file_path,
        module="backend.test_ast",
    )

    visitor.visit(tree)

    print("=" * 80)
    print("LOCAL VARIABLE TYPES")
    print("=" * 80)

    for k, v in visitor.local_variable_types.items():
        print(f"{k} -> {v}")

    print()

    print("=" * 80)
    print("CALL SITES")
    print("=" * 80)

    for call in visitor.calls:
        print(f"CALLER       : {call.caller}")
        print(f"CALLEE       : {call.callee}")
        print(f"RECEIVER     : {call.receiver}")
        print(f"RECEIVERTYPE : {call.receiver_type}")
        print(f"LINE         : {call.line}")
        print("-" * 80)


if __name__ == "__main__":
    main()