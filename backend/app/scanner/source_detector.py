"""
Project source root detector.

Detects probable source roots for software projects using
language-agnostic heuristics.
"""

from __future__ import annotations

from pathlib import Path

from app.scanner.source_detector.models import SourceRoot


class SourceRootDetector:
    """
    Detect likely source roots.
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
        "coverage",
        ".idea",
        ".vscode",
        ".cache",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
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
        "api",
        "pkg",
        "lib",
        "libs",
    }

    PROJECT_FILES = {
        "requirements.txt",
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        "composer.json",
        "CMakeLists.txt",
        "Makefile",
    }

    EXTENSION_LANGUAGE = {
        ".py": "Python",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".java": "Java",
        ".kt": "Kotlin",
        ".go": "Go",
        ".rs": "Rust",
        ".cpp": "C/C++",
        ".cc": "C/C++",
        ".c": "C/C++",
        ".hpp": "C/C++",
        ".h": "C/C++",
        ".cs": "C#",
        ".swift": "Swift",
        ".php": "PHP",
        ".rb": "Ruby",
    }

    def detect(
        self,
        project_root: Path,
    ) -> list[SourceRoot]:

        project_root = project_root.resolve()

        candidates: list[SourceRoot] = []

        #
        # Always evaluate the project root
        #

        directories = [project_root]

        directories.extend(
            d
            for d in project_root.rglob("*")
            if d.is_dir()
        )

        for directory in directories:

            if self._should_ignore(directory):
                continue

            root = self._evaluate(directory)

            if root.score >= 30:
                candidates.append(root)

        #
        # Highest score first
        #

        candidates.sort(
            key=lambda x: (-x.score, len(x.path.parts))
        )

        #
        # Remove nested duplicates
        #

        filtered: list[SourceRoot] = []

        for candidate in candidates:

            if any(
                candidate.path.is_relative_to(existing.path)
                for existing in filtered
            ):
                continue

            filtered.append(candidate)

        if not filtered:

            return [
                SourceRoot(
                    path=project_root,
                    score=1,
                    language=None,
                    reason=["fallback"],
                )
            ]

        return filtered

    def _evaluate(
        self,
        directory: Path,
    ) -> SourceRoot:

        score = 0

        reasons: set[str] = set()

        #
        # Directory name
        #

        if directory.name.lower() in self.COMMON_SOURCE_NAMES:

            score += 30

            reasons.add(
                f"directory named '{directory.name}'"
            )

        #
        # Direct children only
        #

        source_files, languages = self._count_source_files(
            directory,
        )

        for child in directory.iterdir():

            if child.is_dir():

                if child.name in self.IGNORE_DIRS:
                    continue

                continue

            #
            # Project files
            #

            if child.name in self.PROJECT_FILES:

                score += 40

                reasons.add(
                    f"contains {child.name}"
                )

        #
        # Source files
        #

        if source_files:

            score += min(
                source_files * 3,
                30,
            )

            if source_files == 1:

                reasons.add(
                    "contains 1 source file"
                )

            else:

                reasons.add(
                    f"contains {source_files} source files"
                )

        #
        # Common project structure
        #

        subdirs = {
            d.name.lower()
            for d in directory.iterdir()
            if d.is_dir()
        }

        important = {
            "models",
            "routes",
            "controllers",
            "services",
            "views",
            "tests",
        }

        shared = subdirs & important

        if shared:

            score += min(
                len(shared) * 5,
                20,
            )

            reasons.add(
                "contains common source directories"
            )

        #
        # Dominant language
        #

        dominant_language = None

        if languages:

            dominant_language = max(
                languages,
                key=languages.get,
            )

        return SourceRoot(
            path=directory,
            score=score,
            language=dominant_language,
            language_counts=languages,
            reasons=sorted(reasons),
        )

    def _should_ignore(
        self,
        directory: Path,
    ) -> bool:

        return any(
            part in self.IGNORE_DIRS
            for part in directory.parts
        )

    def _count_source_files(
        self,
        directory: Path,
    ) -> tuple[int, dict[str, int]]:

        count = 0

        languages: dict[str, int] = {}

        for file in directory.rglob("*"):

            if any(
                part in self.IGNORE_DIRS
                for part in file.parts
            ):
                continue

            if not file.is_file():
                continue

            suffix = file.suffix.lower()

            language = self.EXTENSION_LANGUAGE.get(suffix)

            if not language:
                continue

            count += 1

            languages[language] = languages.get(language, 0) + 1

        return count, languages
