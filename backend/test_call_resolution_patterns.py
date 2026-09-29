from __future__ import annotations

import io
import tempfile
import textwrap
from pathlib import Path
from contextlib import redirect_stdout

from app.scanner.call_graph.builder import CallGraphBuilder
from app.scanner.call_graph.resolver import CallResolver
from app.scanner.scanner import ProjectScanner


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


def _resolved_symbols(project_root: Path) -> set[str]:
    scanner = ProjectScanner()
    sink = io.StringIO()

    with redirect_stdout(sink):
        scan_result, index = scanner.scan(project_root)

        builder = CallGraphBuilder()
        raw_calls = builder.build(index.module_index)

        resolver = CallResolver(index.symbol_index, scan_result)
        resolved_calls = resolver.resolve(raw_calls)

    return {edge.callee_symbol for edge in resolved_calls}


def _unresolved_report() -> str:
    return Path("unresolved_calls.txt").read_text(encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)

        _write(
            root / "pkg" / "__init__.py",
            """
            from .symbols import SymbolIndex, SymbolIndexBuilder
            from .factories import create_index
            """,
        )
        _write(
            root / "pkg" / "symbols.py",
            """
            class SymbolIndex:
                def lookup(self):
                    return 1


            class SymbolIndexBuilder:
                def __init__(self):
                    self.index = SymbolIndex()

                def build(self):
                    return self.index
            """,
        )
        _write(
            root / "pkg" / "factories.py",
            """
            from .symbols import SymbolIndex


            def create_index():
                return SymbolIndex()
            """,
        )
        _write(
            root / "pkg" / "use_cases.py",
            """
            from .factories import create_index
            from .symbols import SymbolIndex, SymbolIndexBuilder
            import pkg.symbols as symbols


            class Wrapper:
                def __init__(self):
                    self.index = SymbolIndex()
                    self.builder = SymbolIndexBuilder()

                def run(self):
                    index = SymbolIndex()
                    index.lookup()

                    created = create_index()
                    created.lookup()

                    builder = SymbolIndexBuilder()
                    builder.build()

                    self.index.lookup()
                    self.builder.index.lookup()

                    unknown = create_parser()
                    unknown.parse()

                    print("builtins are ignored")
                    len([1, 2, 3])
                    sorted([3, 1, 2])

                    symbols.SymbolIndex()
                    SymbolIndex()
            """,
        )

        resolved_symbols = _resolved_symbols(root)

        expected = {
            "symbols.SymbolIndex",
            "symbols.SymbolIndex.lookup",
            "symbols.SymbolIndexBuilder",
            "symbols.SymbolIndexBuilder.build",
            "factories.create_index",
        }

        for symbol in expected:
            assert symbol in resolved_symbols, f"Missing resolved symbol: {symbol}"

        report = _unresolved_report()

        assert "print" not in report
        assert "len" not in report
        assert "sorted" not in report
        assert "created.lookup" not in report
        assert "self.builder.index.lookup" not in report
        assert "unknown.parse" in report
        assert "RECEIVER : unknown" in report


if __name__ == "__main__":
    main()