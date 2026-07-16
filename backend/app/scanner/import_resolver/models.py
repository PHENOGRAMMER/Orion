"""
Models used by the Import Resolver.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class ModuleInfo(BaseModel):
    """
    Represents a Python module discovered in the project.
    """

    # Full import path
    #
    # Example:
    # app.scanner.models
    #
    name: str

    # Package containing the module.
    #
    # Examples:
    #
    # app.scanner
    # app.scanner.source_detector
    #
    package: str

    # Absolute/relative filesystem path.
    path: Path

    # True if represented by __init__.py
    is_package: bool = False


class ModuleResolution(BaseModel):
    """
    Result of resolving an imported module.
    """

    module: str

    resolved: bool = False

    file: Path | None = None

    resolved_module: ModuleInfo | None = None


class SymbolResolution(BaseModel):
    """
    Result of resolving an imported symbol.
    """

    module: str

    symbol: str

    resolved: bool = False

    file: Path | None = None

    symbol_type: str | None = None

    line: int | None = None

    module_info: ModuleInfo | None = None


class ResolutionStatistics(BaseModel):
    """
    Statistics for one resolution pass.
    """

    total_imports: int = 0

    resolved_modules: int = 0

    resolved_symbols: int = 0