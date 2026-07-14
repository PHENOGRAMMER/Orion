"""
Source Root Detector.

Discovers probable source roots inside a project.
"""

from __future__ import annotations

from pathlib import Path

from .constants import MIN_ROOT_SCORE
from .models import SourceRoot
from .scoring import SourceRootScorer
from .utils import should_ignore, safe_rglob


class SourceRootDetector:
    """
    Detect probable source roots within a project.
    """

    def __init__(self) -> None:

        self.scorer = SourceRootScorer()

    def detect(
        self,
        project_root: Path,
    ) -> list[SourceRoot]:
        """
        Detect source roots inside a project.

        Parameters
        ----------
        project_root:
            Root directory of the project.

        Returns
        -------
        list[SourceRoot]
            Ranked source root candidates.
        """

        project_root = project_root.resolve()

        candidates: list[SourceRoot] = []

        #
        # Always evaluate project root.
        #

        candidates.append(
            self.scorer.evaluate(project_root)
        )

        #
        # Evaluate every subdirectory.
        #

        for path in safe_rglob(project_root):

            if not path.is_dir():
                continue

            if should_ignore(path):
                continue

            root = self.scorer.evaluate(path)

            if root.score >= MIN_ROOT_SCORE:
                candidates.append(root)

        #
        # Highest score first.
        #

        candidates.sort(
            key=lambda root: (
                -root.score,
                len(root.path.parts),
            )
        )

        #
        # Remove redundant nested roots.
        #

        filtered: list[SourceRoot] = []

        for candidate in candidates:

            duplicate = False

            for existing in filtered:

                try:

                    candidate.path.relative_to(
                        existing.path
                    )

                    #
                    # Nested directory with same language.
                    #

                    if (
                        candidate.language
                        == existing.language
                    ):

                        duplicate = True
                        break

                except ValueError:

                    continue

            if not duplicate:

                filtered.append(candidate)

        #
        # Fallback.
        #

        if not filtered:

            return [
                SourceRoot(
                    path=project_root,
                    score=1,
                    confidence="Low",
                    reasons=["fallback"],
                )
            ]

        return filtered