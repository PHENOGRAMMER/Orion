"""
Utilities for converting Python source files
into importable module information.
"""

from __future__ import annotations

from pathlib import Path

from app.scanner.import_resolver.models import ModuleInfo
from app.scanner.source_detector.models import SourceRoot
from app.scanner.index import ProjectIndex


class ModuleNameBuilder:
    """
    Converts source files into ModuleInfo objects.

    Examples
    --------

    backend/app/scanner/models.py

        ->
        ModuleInfo(
            name="app.scanner.models",
            package="app.scanner",
            is_package=False,
        )

    backend/app/scanner/source_detector/__init__.py

        ->
        ModuleInfo(
            name="app.scanner.source_detector",
            package="app.scanner.source_detector",
            is_package=True,
        )
    """

    def build(
        self,
        file_path: Path,
        source_roots: list[SourceRoot],
    ) -> ModuleInfo | None:

        chosen_root: Path | None = None

        #
        # Find the source root that owns this file.
        #

        for root in source_roots:

            try:

                file_path.relative_to(root.path)

                chosen_root = root.path

                break

            except ValueError:

                continue

        if chosen_root is None:
            return None

        #
        # Relative path from source root.
        #

        relative = file_path.relative_to(chosen_root)

        relative = relative.with_suffix("")

        parts = list(relative.parts)

        #
        # Detect packages (__init__.py)
        #

        is_package = False

        if parts and parts[-1] == "__init__":

            is_package = True

            parts.pop()

        #
        # Full module name.
        #

        module_name = ".".join(parts)

        #
        # Package name.
        #

        if is_package:

            #
            # __init__.py represents the package itself.
            #

            package_name = module_name

        else:

            if "." in module_name:

                package_name = module_name.rsplit(".", 1)[0]

            else:

                package_name = ""

        return ModuleInfo(
            name=module_name,
            package=package_name,
            path=file_path,
            is_package=is_package,
        )


def normalize_import_path(
    path: Path,
    index: ProjectIndex,
) -> str:
    """
    Normalizes an absolute path to the project-relative path
    used for imports and graph references.
    """
    
    file_name = path.name

    for file_info in index.files_by_name.get(file_name, []):

        if path.as_posix().endswith(file_info.path):

            return file_info.path

    return path.as_posix()
