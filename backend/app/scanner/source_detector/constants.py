"""
Constants used by the Source Root Detector.
"""

from __future__ import annotations

#
# Scoring Weights
#

DIRECTORY_NAME_SCORE = 30

PROJECT_FILE_SCORE = 40

COMMON_SUBDIRECTORY_SCORE = 5

MAX_STRUCTURE_SCORE = 20

SOURCE_FILE_WEIGHT = 3

MAX_SOURCE_FILE_SCORE = 30

MIN_ROOT_SCORE = 30

#
# Confidence Thresholds
#

VERY_HIGH_CONFIDENCE = 90

HIGH_CONFIDENCE = 70

MEDIUM_CONFIDENCE = 40

#
# Directories never considered source roots
#

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

#
# Common source root names
#

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

#
# Files that strongly indicate a project root
#

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
    "settings.gradle.kts",
    "composer.json",
    "CMakeLists.txt",
    "Makefile",
}

#
# Directory names that commonly appear inside source roots
#

COMMON_SOURCE_SUBDIRECTORIES = {
    "controllers",
    "models",
    "routes",
    "services",
    "views",
    "tests",
    "utils",
    "helpers",
    "middleware",
    "components",
}

#
# Extension → Language
#

EXTENSION_LANGUAGE = {
    ".py": "Python",
    ".ipynb": "Python",

    ".js": "JavaScript",
    ".jsx": "JavaScript",

    ".ts": "TypeScript",
    ".tsx": "TypeScript",

    ".java": "Java",

    ".kt": "Kotlin",
    ".kts": "Kotlin",

    ".go": "Go",

    ".rs": "Rust",

    ".c": "C",
    ".h": "C",

    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",

    ".cs": "C#",

    ".swift": "Swift",

    ".php": "PHP",

    ".rb": "Ruby",
}