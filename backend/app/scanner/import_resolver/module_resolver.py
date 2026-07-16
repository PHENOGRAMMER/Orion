"""
Module Resolver.

Resolves ImportSymbol.module to a project file.
"""

from __future__ import annotations

from pathlib import Path

from app.scanner.index import ProjectIndex
from app.scanner.models import ImportSymbol

from .models import ModuleResolution
from .utils import (
    lookup_module,
    module_exists,
    resolve_relative_module,
)


class ModuleResolver:
    """
    Resolves imported modules using the project module index.
    """

    def resolve(
        self,
        *,
        current_module: str,
        import_symbol: ImportSymbol,
        index: ProjectIndex,
    ) -> ModuleResolution:
        """
        Resolve a single import.

        Parameters
        ----------
        current_module:
            Module containing the import.

        import_symbol:
            Parsed ImportSymbol.

        index:
            Project module index.

        Returns
        -------
        ModuleResolution
        """

        #
        # Convert relative imports to absolute imports.
        #

        module = resolve_relative_module(
            current_module=current_module,
            imported=import_symbol,
        )

        #
        # Module not present in project.
        #

        if not module_exists(
            module,
            index,
        ):

            return ModuleResolution(
                module=module,
                resolved=False,
            )

        #
        # Lookup module.
        #

        resolved_module = lookup_module(
            module,
            index,
        )

        #
        # Update ImportSymbol.
        #

        if resolved_module is not None:

            import_symbol.resolved_file = (
                resolved_module.path.as_posix()
            )

        return ModuleResolution(
            module=module,
            resolved=resolved_module is not None,
            file=resolved_module.path if resolved_module else None,
            resolved_module=resolved_module,
        )