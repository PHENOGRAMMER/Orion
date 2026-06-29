"""
Utilities for converting Python source files
into importable module names.
"""

from pathlib import Path
from app.scanner.source_detector.models import SourceRoot

class ModuleNameBuilder:
    """
    Converts

        backend/app/scanner/models.py

    into

        app.scanner.models
    """

    def build(
        self,
        file_path: Path,
        source_roots: list[SourceRoot],
    ) -> str:

        chosen_root = None

        #
        # Find the source root that owns this file
        #

        for root in source_roots:

            try:

                file_path.relative_to(root.path)

                chosen_root = root.path

                break

            except ValueError:

                continue

        if chosen_root is None:
            return ""

        relative = file_path.relative_to(chosen_root)

        relative = relative.with_suffix("")

        parts = list(relative.parts)

        #
        # package/__init__.py
        #
        # becomes
        #
        # package
        #

        if parts and parts[-1] == "__init__":

            parts.pop()

        return ".".join(parts)