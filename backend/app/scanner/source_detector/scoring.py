"""
Scoring engine for Source Root Detection.
"""

from __future__ import annotations

from pathlib import Path

from .constants import (
    COMMON_SOURCE_NAMES,
    COMMON_SOURCE_SUBDIRECTORIES,
    COMMON_SUBDIRECTORY_SCORE,
    DIRECTORY_NAME_SCORE,
    MAX_SOURCE_FILE_SCORE,
    MAX_STRUCTURE_SCORE,
    PROJECT_FILE_SCORE,
    PROJECT_FILES,
    SOURCE_FILE_WEIGHT,
)
from .models import SourceRoot
from .utils import (
    confidence_from_score,
    count_source_files,
    dominant_language,
    safe_iterdir,
)


class SourceRootScorer:
    """
    Evaluates a directory and assigns a SourceRoot score.
    """

    def evaluate(
        self,
        directory: Path,
    ) -> SourceRoot:

        score = 0

        reasons: set[str] = set()

        #
        # Directory name
        #

        score += self._score_directory_name(
            directory,
            reasons,
        )

        #
        # Project files
        #

        score += self._score_project_files(
            directory,
            reasons,
        )

        #
        # Source files
        #

        source_files, language_counts = count_source_files(
            directory,
        )

        score += self._score_source_files(
            source_files,
            reasons,
        )

        #
        # Project structure
        #

        score += self._score_structure(
            directory,
            reasons,
        )

        return SourceRoot(
            path=directory,
            score=score,
            language=dominant_language(
                language_counts,
            ),
            language_counts=language_counts,
            confidence=confidence_from_score(
                score,
            ),
            reasons=sorted(reasons),
        )

    #
    # Individual heuristics
    #

    def _score_directory_name(
        self,
        directory: Path,
        reasons: set[str],
    ) -> int:

        if directory.name.lower() not in COMMON_SOURCE_NAMES:
            return 0

        reasons.add(
            f"directory named '{directory.name}'"
        )

        return DIRECTORY_NAME_SCORE

    def _score_project_files(
        self,
        directory: Path,
        reasons: set[str],
    ) -> int:

        score = 0

        for child in safe_iterdir(directory):

            if not child.is_file():
                continue

            if child.name not in PROJECT_FILES:
                continue

            reasons.add(
                f"contains {child.name}"
            )

            score += PROJECT_FILE_SCORE

        return score

    def _score_source_files(
        self,
        source_files: int,
        reasons: set[str],
    ) -> int:

        if source_files <= 0:
            return 0

        if source_files == 1:

            reasons.add(
                "contains 1 source file"
            )

        else:

            reasons.add(
                f"contains {source_files} source files"
            )

        return min(
            source_files * SOURCE_FILE_WEIGHT,
            MAX_SOURCE_FILE_SCORE,
        )

    def _score_structure(
        self,
        directory: Path,
        reasons: set[str],
    ) -> int:

        score = 0

        for child in safe_iterdir(directory):

            if not child.is_dir():
                continue

            if (
                child.name.lower()
                not in COMMON_SOURCE_SUBDIRECTORIES
            ):
                continue

            score += COMMON_SUBDIRECTORY_SCORE

        if score > 0:

            reasons.add(
                "contains common source directories"
            )

        return min(
            score,
            MAX_STRUCTURE_SCORE,
        )