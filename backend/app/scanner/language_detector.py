"""
Language detector.

Determines project languages based on extension statistics.
"""

from app.scanner.models import ProjectScanResult


EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".xml": "XML",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".md": "Markdown",
    ".txt": "Text",
}


class LanguageDetector:
    """
    Converts extension statistics into language statistics.
    """

    def analyze(
        self,
        result: ProjectScanResult,
    ) -> ProjectScanResult:

        languages = {}

        for extension, count in result.statistics.extensions.items():

            language = EXTENSION_LANGUAGE_MAP.get(extension)

            if language is None:
                continue

            languages[language] = (
                languages.get(language, 0)
                + count
            )

        result.language_statistics.languages = languages

        return result