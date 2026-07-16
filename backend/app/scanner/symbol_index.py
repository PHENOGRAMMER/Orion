"""
Project Symbol Index.

Provides fast lookup of every symbol defined inside a project.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class SymbolInfo(BaseModel):
    """
    Represents one symbol defined in the project.
    """

    # Simple name
    #
    # Example:
    # ProjectScanner
    #
    name: str

    # Fully-qualified name
    #
    # Example:
    # app.scanner.scanner.ProjectScanner
    #
    qualified_name: str

    # File containing the definition
    path: Path

    # Module containing the definition
    module: str

    # Line number where the definition starts
    line: int

    # One of:
    # class
    # function
    # method
    # variable
    symbol_type: str


class SymbolIndex(BaseModel):
    """
    Fast lookup of project symbols.
    """

    #
    # Symbol name
    #
    # Example:
    #
    # ProjectScanner
    #
    # ->
    #
    # [
    #     SymbolInfo(...),
    #     SymbolInfo(...)
    # ]
    #

    symbols: dict[str, list[SymbolInfo]] = Field(
        default_factory=dict
    )

    #
    # Fully-qualified lookup.
    #
    # Example:
    #
    # app.scanner.scanner.ProjectScanner
    #
    qualified_symbols: dict[str, SymbolInfo] = Field(
        default_factory=dict
    )

    def add(
        self,
        symbol: SymbolInfo,
    ) -> None:
        """
        Add a symbol to the index.
        """

        self.symbols.setdefault(
            symbol.name,
            [],
        ).append(symbol)

        self.qualified_symbols[
            symbol.qualified_name
        ] = symbol

    def lookup(
        self,
        name: str,
    ) -> list[SymbolInfo]:
        """
        Lookup by simple symbol name.
        """

        return self.symbols.get(
            name,
            [],
        )

    def lookup_qualified(
        self,
        qualified_name: str,
    ) -> SymbolInfo | None:
        """
        Lookup by fully-qualified name.
        """

        return self.qualified_symbols.get(
            qualified_name,
        )