from pathlib import Path

from app.scanner.filesystem import FileSystemScanner
from app.scanner.index_builder import ProjectIndexBuilder
from app.scanner.language_detector import LanguageDetector
from app.scanner.models import ProjectScanResult
from app.scanner.framework_detector import FrameworkDetector
from app.scanner.git_detector import GitDetector
from app.scanner.dependency_detector import DependencyDetector
from app.scanner.symbol_detector import SymbolDetector
from app.scanner.import_resolver.resolver import ImportResolver


class ProjectScanner:

    def __init__(self):

        self.filesystem = FileSystemScanner()

        self.index_builder = ProjectIndexBuilder()

        self.language_detector = LanguageDetector()

        self.framework_detector = FrameworkDetector()

        self.git_detector = GitDetector()

        self.dependency_detector = DependencyDetector()

        self.symbol_detector = SymbolDetector()

        self.import_resolver = ImportResolver()

    def scan(
            self,
            path: str | Path,
            include_files: bool = True,
            time_zone: str = "GMT",
        ) -> ProjectScanResult:

        result = self.filesystem.scan(
            str(path),
            include_files=include_files,
            time_zone=time_zone,
        )

        index = self.index_builder.build(result)

        result = self.language_detector.analyze(result)
        result = self.framework_detector.analyze(result, index)
        result = self.git_detector.analyze(result)
        result = self.dependency_detector.analyze(result, index)
        result = self.symbol_detector.analyze(result, index)
        result = self.import_resolver.resolve(result, index)

        # FrameworkDetector(index)
        # GitDetector(index)
        # DependencyDetector(index)

        return result, index