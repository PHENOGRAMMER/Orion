"""
Module Resolver.

Resolves imported modules.
"""

from __future__ import annotations

from app.scanner.index import ProjectIndex
from app.scanner.models import ImportSymbol

from .models import ModuleInfo, ModuleResolution
from .utils import (
    lookup_module,
    module_exists,
    resolve_relative_module,
)
from .module_utils import normalize_import_path


class ModuleResolver:
    """
    Resolves imported modules.
    """

    def resolve(
        self,
        current_module: ModuleInfo,
        import_symbol: ImportSymbol,
        index: ProjectIndex,
    ) -> ModuleResolution:

        module = resolve_relative_module(
            current_module=current_module,
            imported=import_symbol,
        )

        if not module_exists(module, index):
            return ModuleResolution(
                module=module,
                resolved=False,
            )

        resolved_module = lookup_module(
            module,
            index,
        )

        if resolved_module is None:
            return ModuleResolution(
                module=module,
                resolved=False,
            )

        import_symbol.resolved_module = resolved_module.name
        
        # Normalize the absolute path to a project-relative path
        import_symbol.resolved_file = normalize_import_path(
            resolved_module.path,
            index,
        )

        return ModuleResolution(
            module=module,
            resolved=True,
            file=resolved_module.path,
            resolved_module=resolved_module,
        )