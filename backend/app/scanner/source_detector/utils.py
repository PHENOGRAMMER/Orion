"""
Utility functions for Source Root Detection.
"""

from __future__ import annotations

from pathlib import Path

from .constants import (
    EXTENSION_LANGUAGE,
    HIGH_CONFIDENCE,
    IGNORE_DIRS,
    MEDIUM_CONFIDENCE,
    VERY_HIGH_CONFIDENCE,
)


def should_ignore(path: Path) -> bool:
    """
    Returns True if the path should be ignored.
    """

    return any(
        part in IGNORE_DIRS
        for part in path.parts
    )


def safe_iterdir(directory: Path) -> list[Path]:
    """
    Safely list the direct children of a directory.
    """

    try:
        return list(directory.iterdir())

    except (PermissionError, OSError):
        return []


def safe_rglob(directory: Path):
    """
    Safely recursively iterate over a directory.
    """

    try:
        yield from directory.rglob("*")

    except (PermissionError, OSError):
        return


def count_source_files(
    directory: Path,
) -> tuple[int, dict[str, int]]:
    """
    Count source files recursively and build a language histogram.

    Returns
    -------
    (source_file_count, language_counts)
    """

    count = 0

    languages: dict[str, int] = {}

    for file in safe_rglob(directory):

        if should_ignore(file):
            continue

        if not file.is_file():
            continue

        language = EXTENSION_LANGUAGE.get(
            file.suffix.lower()
        )

        if language is None:
            continue

        count += 1

        languages[language] = (
            languages.get(language, 0)
            + 1
        )

    return count, languages


def dominant_language(
    language_counts: dict[str, int],
) -> str | None:
    """
    Determine the dominant language.
    """

    if not language_counts:
        return None

    return max(
        language_counts,
        key=language_counts.get,
    )


def confidence_from_score(
    score: int,
) -> str:
    """
    Convert a numeric score into a confidence level.
    """

    if score >= VERY_HIGH_CONFIDENCE:
        return "Very High"

    if score >= HIGH_CONFIDENCE:
        return "High"

    if score >= MEDIUM_CONFIDENCE:
        return "Medium"

    return "Low"