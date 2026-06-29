"""
Import resolver.

Coordinates all import resolution passes.
"""

from __future__ import annotations

from app.scanner.index import ProjectIndex
from app.scanner.models import ProjectScanResult

from .module_resolver import ModuleResolver
from .symbol_resolver import SymbolResolver


class ImportResolver:
    """
    Runs all import resolution stages.
    """

    def __init__(self):

        self.module_resolver = ModuleResolver()

        self.symbol_resolver = SymbolResolver()

    def resolve(
        self,
        result: ProjectScanResult,
        index: ProjectIndex,
    ) -> ProjectScanResult:

        result = self.module_resolver.resolve(
            result,
            index,
        )

        result = self.symbol_resolver.resolve(
            result,
        )

        return result