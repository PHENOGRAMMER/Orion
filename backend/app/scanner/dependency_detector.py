"""
Dependency detector.

Builds the project's dependency graph.
"""

from __future__ import annotations

from pathlib import Path

from app.scanner.dependency_parser import DependencyParser
from app.scanner.index import ProjectIndex
from app.scanner.models import (
    DependencyGraph,
    DependencyModel,
    ProjectScanResult,
)


class DependencyDetector:
    """
    Builds a dependency graph for Python projects.
    """

    def __init__(self):

        self.parser = DependencyParser()

    def analyze(
        self,
        result: ProjectScanResult,
        index: ProjectIndex,
    ) -> ProjectScanResult:

        graph = DependencyGraph()

        python_files = index.files_by_extension.get(
            ".py",
            [],
        )

        for file in python_files:

            full_path = (
                Path(result.root_path)
                / file.path
            )

            imports = self.parser.parse(
                full_path
            )

            graph.nodes[file.path] = DependencyModel(
                file=file.path,
                imports=imports,
            )

        result.dependency_graph = graph

        return result