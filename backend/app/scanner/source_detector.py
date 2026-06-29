"""
Project source root detector.

Detects probable source roots for any software project.

The detector is heuristic-based and language-agnostic.
"""

from __future__ import annotations

from pathlib import Path

from app.scanner.models import SourceRoot


class SourceRootDetector:
    """
    Detect likely source roots inside a repository.
    """

    IGNORE_DIRS = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        "target",
        "out",
        "coverage",
        ".idea",
        ".vscode",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".cache",
        ".next",
        ".nuxt",
        ".gradle",
    }

    PROJECT_FILES = {
        "pyproject.toml",
        "requirements.txt",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        "settings.gradle.kts",
        "composer.json",
        "CMakeLists.txt",
        "Makefile",
    }

    COMMON_SOURCE_NAMES = {
        "src",
        "app",
        "backend",
        "frontend",
        "server",
        "client",
        "core",
        "engine",
        "lib",
        "libs",
        "pkg",
        "packages",
        "services",
        "api",
    }

    EXTENSION_LANGUAGE = {
        ".py": "Python",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".java": "Java",
        ".kt": "Kotlin",
        ".kts": "Kotlin",
        ".go": "Go",
        ".rs": "Rust",
        ".cpp": "C/C++",
        ".cc": "C/C++",
        ".cxx": "C/C++",
        ".c": "C/C++",
        ".h": "C/C++",
        ".hpp": "C/C++",
        ".cs": "C#",
        ".swift": "Swift",
        ".php": "PHP",
        ".rb": "Ruby",
    }

    SOURCE_EXTENSIONS = set(EXTENSION_LANGUAGE.keys())

    def detect(
        self,
        project_root: Path,
    ) -> list[SourceRoot]:
        """
        Detect probable source roots.
        """

        project_root = project_root.resolve()

        candidates: list[SourceRoot] = []

        for directory in project_root.rglob("*"):

            if not directory.is_dir():
                continue

            if self._should_ignore(directory):
                continue

            score, reasons, language = self._score_directory(directory)

            if score >= 30:

                candidates.append(
                    SourceRoot(
                        path=directory,
                        score=score,
                        reason=reasons,
                        language=language,
                    )
                )

        #
        # Fallback
        #

        if not candidates:

            return [
                SourceRoot(
                    path=project_root,
                    score=1,
                    reason=["fallback"],
                    language=None,
                )
            ]

        #
        # Highest score first
        #

        candidates.sort(
            key=lambda root: (-root.score, len(root.path.parts))
        )

        #
        # Remove nested roots
        #

        filtered: list[SourceRoot] = []

        for candidate in candidates:

            if any(
                candidate.path.is_relative_to(existing.path)
                for existing in filtered
            ):
                continue

            filtered.append(candidate)

        return filtered

    def _score_directory(
        self,
        directory: Path,
    ) -> tuple[int, list[str], str | None]:

        score = 0
        reasons: list[str] = []

        language_counts: dict[str, int] = {}

        #
        # Common names
        #

        if directory.name.lower() in self.COMMON_SOURCE_NAMES:

            score += 30

            reasons.append(
                f"directory named '{directory.name}'"
            )

        source_files = 0

        scanned = 0
        max_scan = 500

        try:

            for child in directory.rglob("*"):

                if scanned >= max_scan:
                    break

                scanned += 1

                if child.is_dir():

                    if self._should_ignore(child):
                        continue

                    continue

                #
                # Project files
                #

                if child.name in self.PROJECT_FILES:

                    score += 50

                    reasons.append(
                        f"contains {child.name}"
                    )

                #
                # Source files
                #

                suffix = child.suffix.lower()

                if suffix not in self.SOURCE_EXTENSIONS:
                    continue

                source_files += 1

                language = self.EXTENSION_LANGUAGE[suffix]

                language_counts.setdefault(language, 0)

                language_counts[language] += 1

        except PermissionError:

            return 0, [], None

        #
        # Source file score
        #

        score += min(source_files * 2, 50)

        if source_files >= 10:

            score += 20

        if source_files:

            reasons.append(
                f"contains {source_files} source files"
            )

        dominant_language = None

        if language_counts:

            dominant_language = max(
                language_counts,
                key=language_counts.get,
            )

        return score, reasons, dominant_language

    def _should_ignore(
        self,
        directory: Path,
    ) -> bool:

        return any(
            part in self.IGNORE_DIRS
            for part in directory.parts
        )