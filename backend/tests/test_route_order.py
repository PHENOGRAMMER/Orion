"""
Regression guard for route registration order in app/api/graph.py.

Starlette compiles ``{name:path}`` to ``(?P<name>.*)``, which matches slashes.
That makes ``/symbol/{qualified_name:path}`` a catch-all that will happily
swallow ``/symbol/a.b.c/impact`` with qualified_name="a.b.c/impact" — so if the
catch-all is registered first, the impact endpoint becomes unreachable and every
impact request 404s. That was a live bug; this test stops it coming back.

The routes are read from the source with ``ast`` rather than by importing the
module, so this runs without FastAPI installed.

    python -m unittest discover -s tests -v
"""

import ast
import re
import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

GRAPH_API = BACKEND / "app" / "api" / "graph.py"


def declared_routes(source: str) -> list[tuple[str, str, str]]:
    """
    Every @router.<method>("<path>") in source order, as (method, path, func).
    """
    tree = ast.parse(source)
    routes: list[tuple[str, str, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue

            func = decorator.func
            if not isinstance(func, ast.Attribute):
                continue
            if not isinstance(func.value, ast.Name) or func.value.id != "router":
                continue
            if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
                continue

            routes.append((func.attr, decorator.args[0].value, node.name))

    routes.sort(key=lambda item: source.index(f'"{item[1]}"'))
    return routes


def compile_route(path: str) -> re.Pattern:
    """
    Reproduce Starlette's path-to-regex conversion closely enough to test
    matching precedence: ``{x:path}`` becomes ``.*``, ``{x}`` becomes ``[^/]+``.
    """
    out, index = "", 0

    for match in re.finditer(r"\{([a-zA-Z_][a-zA-Z0-9_]*)(:path)?\}", path):
        out += re.escape(path[index:match.start()])
        out += f"(?P<{match.group(1)}>" + (".*" if match.group(2) else "[^/]+") + ")"
        index = match.end()

    return re.compile("^" + out + re.escape(path[index:]) + "$")


class TestSymbolRouteOrder(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.source = GRAPH_API.read_text(encoding="utf-8")
        cls.routes = declared_routes(cls.source)

    def test_routes_were_discovered(self):
        self.assertGreater(len(self.routes), 5, "expected several routes")

    def test_impact_route_precedes_the_catch_all(self):
        paths = [path for _method, path, _func in self.routes]
        self.assertIn("/symbol/{qualified_name:path}/impact", paths)
        self.assertIn("/symbol/{qualified_name:path}", paths)
        self.assertLess(
            paths.index("/symbol/{qualified_name:path}/impact"),
            paths.index("/symbol/{qualified_name:path}"),
            "the /impact route must be registered before the catch-all, "
            "otherwise the catch-all swallows it and impact analysis 404s",
        )

    def test_impact_url_resolves_to_the_impact_handler(self):
        url = "/symbol/app.scanner.symbol_index.SymbolIndex.lookup/impact"

        for _method, path, func in self.routes:
            match = compile_route(path).match(url)
            if match:
                self.assertEqual(func, "symbol_impact")
                self.assertEqual(
                    match.group("qualified_name"),
                    "app.scanner.symbol_index.SymbolIndex.lookup",
                    "the trailing /impact must not leak into the symbol name",
                )
                return

        self.fail("no route matched the impact URL")

    def test_plain_symbol_url_resolves_to_the_symbol_handler(self):
        url = "/symbol/app.scanner.scanner.ProjectScanner.scan"

        for _method, path, func in self.routes:
            if compile_route(path).match(url):
                self.assertEqual(func, "symbol_info")
                return

        self.fail("no route matched the symbol URL")

    def test_catch_all_is_declared_last(self):
        """
        Anything registered after the catch-all is dead. Keep it last so new
        routes cannot be silently shadowed.
        """
        paths = [path for _method, path, _func in self.routes]
        self.assertEqual(paths[-1], "/symbol/{qualified_name:path}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
