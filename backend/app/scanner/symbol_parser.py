from __future__ import annotations

import ast
from pathlib import Path

from app.scanner.models import (
    ClassSymbol,
    FileSymbols,
    FunctionSymbol,
    MethodSymbol,
    VariableSymbol,
    ImportSymbol,
)


class SymbolParser:
    """
    Parses a Python source file and extracts symbols.
    """

    def parse(
        self,
        file_path: Path,
    ) -> FileSymbols:

        source = self._read_source(file_path)

        if not source:
            return FileSymbols()

        try:
            tree = ast.parse(
                source,
                filename=str(file_path),
            )

        except SyntaxError:
            return FileSymbols()

        symbols = FileSymbols()

        for node in tree.body:

            if isinstance(node, ast.Import):

                for alias in node.names:
                    symbols.imports.append(
                        ImportSymbol(
                            module=alias.name, 
                            alias=alias.asname 
                        )
                    )

            elif isinstance(node, ast.ImportFrom):

                module = node.module or ""
                for alias in node.names:
                    symbols.imports.append(
                        ImportSymbol(
                        module=module,
                        name=alias.name,
                        alias=alias.asname,
                        relative_level=node.level,
                        )
                    )

            elif isinstance(node, ast.ClassDef):

                symbols.classes.append(
                    ClassSymbol(
                        name=node.name,
                        line=node.lineno,
                        end_line=self._get_end_line(node),
                        decorators=[
                            ast.unparse(d)
                            for d in node.decorator_list
                        ],
                        base_classes=[
                            self._resolve_expression(base)
                            for base in node.bases
                        ],
                        docstring=ast.get_docstring(node),
                        methods=self._collect_methods(node),
                    )
                )

            elif isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):

                symbols.functions.append(
                    FunctionSymbol(
                        name=node.name,
                        line=node.lineno,
                        end_line=self._get_end_line(node),
                        decorators=[
                            ast.unparse(d)
                            for d in node.decorator_list
                        ],
                        async_function=isinstance(
                            node,
                            ast.AsyncFunctionDef,
                        ),
                        docstring=ast.get_docstring(node),
                    )
                )

            elif isinstance(node, ast.Assign):

                self._collect_assignment(
                    node.targets,
                    symbols,
                )

            elif isinstance(node, ast.AnnAssign):

                self._collect_assignment(
                    [node.target],
                    symbols,
                )

        return symbols

    def _collect_methods(
        self,
        class_node: ast.ClassDef,
    ) -> list[MethodSymbol]:

        methods: list[MethodSymbol] = []

        for node in class_node.body:

            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):

                methods.append(
                    MethodSymbol(
                        name=node.name,
                        line=node.lineno,
                        end_line=self._get_end_line(node),
                        async_method=isinstance(
                            node,
                            ast.AsyncFunctionDef,
                        ),
                        decorators=[
                            ast.unparse(d)
                            for d in node.decorator_list
                        ],
                        docstring=ast.get_docstring(node),
                    )
                )

        return methods

    def _collect_assignment(
        self,
        targets: list[ast.AST],
        symbols: FileSymbols,
    ) -> None:

        for target in targets:

            if isinstance(target, ast.Name):

                symbols.variables.append(
                    VariableSymbol(
                        name=target.id,
                        line=target.lineno,
                    )
                )

            elif isinstance(target, ast.Tuple):

                for element in target.elts:

                    if isinstance(element, ast.Name):

                        symbols.variables.append(
                            VariableSymbol(
                                name=element.id,
                                line=element.lineno,
                            )
                        )

    def _read_source(
        self,
        file_path: Path,
    ) -> str:

        encodings = (
            "utf-8",
            "utf-8-sig",
            "utf-16",
        )

        for encoding in encodings:

            try:
                return file_path.read_text(
                    encoding=encoding,
                )

            except UnicodeDecodeError:
                continue

            except OSError:
                return ""

        return ""

    def _get_end_line(
        self,
        node: ast.AST,
    ) -> int:

        return getattr(
            node,
            "end_lineno",
            node.lineno,
        )

    def _resolve_expression(
        self,
        node: ast.AST,
    ) -> str:

        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Attribute):

            value = self._resolve_expression(node.value)

            return (
                f"{value}.{node.attr}"
                if value
                else node.attr
            )

        if isinstance(node, ast.Subscript):

            value = self._resolve_expression(
                node.value
            )

            slice_value = self._resolve_expression(
                node.slice
            )

            return f"{value}[{slice_value}]"

        if isinstance(node, ast.Call):
            return self._resolve_expression(
                node.func
            )

        if isinstance(node, ast.Constant):
            return repr(node.value)

        if isinstance(node, ast.Tuple):

            return ", ".join(
                self._resolve_expression(x)
                for x in node.elts
            )

        try:
            return ast.unparse(node)
        except Exception:
            return ""