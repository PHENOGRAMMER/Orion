"""
Dependency parser.

Parses Python source files and extracts import statements.
"""

from __future__ import annotations

import ast
from pathlib import Path


class DependencyParser:
    """
    Parses Python files and extracts imported modules.
    """

    def parse(self, file_path: Path) -> list[str]:
        """
        Return a sorted list of imported modules.

        Example:
            import os
            import pathlib

            from app.core import config

        Returns:
            [
                "os",
                "pathlib",
                "app.core"
            ]
        """

        if not file_path.exists():
            return []

        try:
            source = file_path.read_text(
                encoding="utf-8",
            )
        except UnicodeDecodeError:
            source = file_path.read_text(
                encoding="utf-8-sig",
            )

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        imports: set[str] = set()

        for node in ast.walk(tree):

            #
            # import xxx
            #
            if isinstance(node, ast.Import):

                for alias in node.names:
                    imports.add(alias.name)

            #
            # from xxx import yyy
            #
            elif isinstance(node, ast.ImportFrom):

                if node.module:
                    imports.add(node.module)

        return sorted(imports)