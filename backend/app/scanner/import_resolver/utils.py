"""
Utility functions for the Import Resolver.
"""

from __future__ import annotations

from pathlib import Path

from app.scanner.import_resolver.models import ModuleInfo

from app.scanner.index import ProjectIndex
from app.scanner.models import FileSymbols
from app.scanner.models import ImportSymbol
from app.scanner.models import SymbolGraph

from .constants import MODULE_SEPARATOR


def normalize_module_name(
    module: str,
) -> str:
    """
    Normalize a module name.

    Examples
    --------
    app.scanner.models.
        -> app.scanner.models

    app..scanner
        -> app.scanner
    """

    module = module.strip()

    while module.endswith(MODULE_SEPARATOR):
        module = module[:-1]

    while ".." in module:
        module = module.replace("..", ".")

    return module


def module_exists(
    module: str,
    index: ProjectIndex,
) -> bool:
    """
    Check whether a module exists in the module index.
    """

    module = normalize_module_name(module)

    return module in index.module_index


def lookup_module(
    module: str,
    index: ProjectIndex,
) -> ModuleInfo | None:
    """
    Resolve a module to its ModuleInfo.
    """

    module = normalize_module_name(module)

    return index.module_index.get(module)


def lookup_file_symbols(
    file_path: str | Path,
    symbol_graph: SymbolGraph,
) -> FileSymbols | None:
    """
    Retrieve symbols for a file.
    """

    if isinstance(file_path, Path):
        file_path = file_path.as_posix()

    return symbol_graph.files.get(
        file_path
    )


def lookup_symbol(
    file_symbols: FileSymbols,
    symbol_name: str,
):
    """
    Look for a symbol inside a file.

    Returns the symbol object if found.
    """

    #
    # Classes
    #

    for symbol in file_symbols.classes:

        if symbol.name == symbol_name:
            return symbol

    #
    # Functions
    #

    for symbol in file_symbols.functions:

        if symbol.name == symbol_name:
            return symbol

    #
    # Variables
    #

    for symbol in file_symbols.variables:

        if symbol.name == symbol_name:
            return symbol

    return None


def resolve_relative_module(
    current_module: ModuleInfo,
    imported: ImportSymbol,
) -> str:
    """
    Resolve a relative import into an absolute module name.
    """

    #
    # Absolute import
    #

    if imported.relative_level == 0:

        return imported.module

    #
    # Determine the base package.
    #

    if current_module.is_package:

        base = current_module.package

    else:

        base = current_module.package

    current_parts = base.split(".") if base else []

    #
    # '..' goes up one package.
    # '.' stays in the current package.
    #

    levels_up = imported.relative_level - 1

    if levels_up > 0:

        if levels_up <= len(current_parts):

            current_parts = current_parts[:-levels_up]

        else:

            current_parts = []

    #
    # Append imported module.
    #

    if imported.module:

        current_parts.extend(imported.module.split("."))

    return ".".join(current_parts)