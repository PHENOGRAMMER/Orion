"""
Symbol detector.

Builds a symbol graph for the project by extracting
classes, functions, methods, variables, and imports
from Python source files.
"""

from __future__ import annotations

from pathlib import Path

from app.scanner.index import ProjectIndex
from app.scanner.models import (
    ProjectScanResult,
    SymbolGraph,
)
from app.scanner.symbol_parser import SymbolParser


class SymbolDetector:
    """
    Builds a symbol graph for Python projects.
    """

    def __init__(self) -> None:

        self.parser = SymbolParser()

    def analyze(
        self,
        result: ProjectScanResult,
        index: ProjectIndex,
    ) -> ProjectScanResult:
        """
        Extract symbols from every Python file in the project.
        """

        graph = SymbolGraph()

        python_files = index.files_by_extension.get(".py", [])

        for file in python_files:

            full_path = Path(result.root_path) / file.path

            symbols = self.parser.parse(full_path)

            # Metadata is injected by the detector,
            # not by the parser.
            symbols.path = file.path
            symbols.language = "Python"

            graph.files[file.path] = symbols

        result.symbol_graph = graph

        return result