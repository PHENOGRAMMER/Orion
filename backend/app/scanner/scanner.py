from pathlib import Path

from app.scanner.filesystem import FileSystemScanner
from app.scanner.language_detector import LanguageDetector
from app.scanner.models import ProjectScanResult


class ProjectScanner:

    def __init__(self):

        self.filesystem = FileSystemScanner()

        self.language_detector = LanguageDetector()

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
        result = self.language_detector.analyze(result)

        return result