"""
Models used by the Source Root Detector.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class SourceRoot(BaseModel):
    """
    Represents a detected source root.

    A source root is a directory from which modules should
    be resolved and indexed.
    """

    # Absolute path of the source root
    path: Path

    # Heuristic score
    score: int

    # Dominant language
    language: str | None = None

    # Complete language histogram
    language_counts: dict[str, int] = Field(
        default_factory=dict
    )

    # Human-readable confidence
    confidence: str = "Low"

    # Why this directory was selected
    reasons: list[str] = Field(
        default_factory=list
    )

    @property
    def source_file_count(self) -> int:
        """
        Total number of detected source files.
        """

        return sum(self.language_counts.values())