"""
Symbol Resolver.

Resolves imported symbols using the project's SymbolIndex.
"""

from __future__ import annotations

from app.scanner.models import ImportSymbol
from app.scanner.symbol_index import SymbolIndex

from .models import SymbolResolution


class SymbolResolver:
    """
    Resolves imported symbols after module resolution.
    """

    def resolve(
        self,
        *,
        import_symbol: ImportSymbol,
        symbol_index: SymbolIndex,
    ) -> SymbolResolution:
        """
        Resolve a single imported symbol.
        """

        #
        # Only "from x import y" imports have symbols.
        #

        if import_symbol.name is None:

            return SymbolResolution(
                module=import_symbol.module,
                symbol="",
                resolved=False,
            )

        #
        # Prefer the module resolved by ModuleResolver.
        #

        module_name = import_symbol.module

        if getattr(import_symbol, "resolved_module", None):

            resolved = import_symbol.resolved_module

            if hasattr(resolved, "name"):

                module_name = resolved.name

            else:

                module_name = str(resolved)

        if module_name is None:

            return SymbolResolution(
                module="",
                symbol=import_symbol.name,
                resolved=False,
            )

        qualified_name = f"{module_name}.{import_symbol.name}"

        symbol = symbol_index.lookup_qualified(
            qualified_name,
        )

        if symbol is None:

            return SymbolResolution(
                module=module_name,
                symbol=import_symbol.name,
                resolved=False,
            )

        #
        # Populate ImportSymbol.
        #

        import_symbol.resolved_file = symbol.path.as_posix()

        import_symbol.resolved_symbol = symbol.name

        import_symbol.resolved_symbol_type = symbol.symbol_type

        #
        # Return resolution.
        #

        return SymbolResolution(
            module=module_name,
            symbol=symbol.name,
            resolved=True,
            file=symbol.path,
            symbol_type=symbol.symbol_type,
            line=symbol.line,
        )