from pathlib import Path

from app.scanner.filesystem import FileSystemScanner
from app.scanner.index_builder import ProjectIndexBuilder
from app.scanner.language_detector import LanguageDetector
from app.scanner.models import ProjectScanResult
from app.scanner.framework_detector import FrameworkDetector
from app.scanner.git_detector import GitDetector


class ProjectScanner:

    def __init__(self):

        self.filesystem = FileSystemScanner()

        self.index_builder = ProjectIndexBuilder()

        self.language_detector = LanguageDetector()

        self.framework_detector = FrameworkDetector()

        self.git_detector = GitDetector()

    def scan(
            self,
            path: str | Path,
            include_files: bool = True,
        ) -> ProjectScanResult:

        result = self.filesystem.scan(
            str(path),
            include_files=include_files,
        )

        index = self.index_builder.build(result)

        result = self.language_detector.analyze(result)
        result = self.framework_detector.analyze(result, index)
        result = self.git_detector.analyze(result)

        # FrameworkDetector(index)
        # GitDetector(index)
        # DependencyDetector(index)

        return result, index