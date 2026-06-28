"""
Scanner constants.

This module defines ignore rules and supported file extensions used
throughout the project scanner.
"""

DEFAULT_IGNORE_DIRS = {
    ".git",
    ".github",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".pytest_cache",
    ".mypy_cache",
}

DEFAULT_IGNORE_FILES = {
    ".DS_Store",
    "Thumbs.db",
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".gitignore",
    ".coverage",
}

SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".cpp",
    ".c",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".rb",
    ".swift",
    ".kt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".xml",
    ".html",
    ".css",
    ".scss",
    ".md",
    ".txt",
}