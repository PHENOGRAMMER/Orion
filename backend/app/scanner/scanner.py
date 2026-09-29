from pathlib import Path
from typing import Callable

from app.scanner.filesystem import FileSystemScanner
from app.scanner.index_builder import ProjectIndexBuilder
from app.scanner.language_detector import LanguageDetector
from app.scanner.models import ProjectScanResult
from app.scanner.framework_detector import FrameworkDetector
from app.scanner.git_detector import GitDetector
from app.scanner.dependency_detector import DependencyDetector
from app.scanner.symbol_detector import SymbolDetector
from app.scanner.import_resolver.resolver import ImportResolver
from app.scanner.call_graph.builder import CallGraphBuilder
from app.scanner.call_graph.resolver import CallResolver


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

        self.call_graph_builder = CallGraphBuilder()

    def scan(
            self,
            path: str | Path,
            include_files: bool = True,
            time_zone: str = "GMT",
            progress_callback: Callable[[str, int], None] | None = None,
        ) -> tuple[ProjectScanResult, object]:

        def progress(message: str, percent: int) -> None:
            if progress_callback is not None:
                progress_callback(message, percent)

        progress("Scanning files", 5)
        result = self.filesystem.scan(
            str(path),
            include_files=include_files,
            time_zone=time_zone,
        )

        progress("Building project index", 20)
        index = self.index_builder.build(result)

        progress("Detecting languages", 30)
        result = self.language_detector.analyze(result)
        progress("Detecting frameworks", 35)
        result = self.framework_detector.analyze(result, index)
        progress("Inspecting Git metadata", 40)
        result = self.git_detector.analyze(result)
        progress("Analyzing dependencies", 50)
        result = self.dependency_detector.analyze(result, index)
        progress("Detecting symbols", 60)
        result = self.symbol_detector.analyze(result, index)

        progress("Indexing symbols", 70)
        index.symbol_index = self.index_builder.symbol_index_builder.build(
            scan_result=result,
            module_index=index.module_index,
        )

        # Resolve imports
        progress("Resolving imports", 78)
        result = self.import_resolver.resolve(result, index)

        # Build call graph and resolve calls
        progress("Building call graph", 88)
        raw_calls = self.call_graph_builder.build(index.module_index)
        call_resolver = CallResolver(index.symbol_index, result)
        resolved_calls = call_resolver.resolve(raw_calls)

        # Build knowledge graph — includes file/module/symbol nodes,
        # import edges, and now call edges from the resolved call graph.
        progress("Building knowledge graph", 95)
        index.knowledge_graph = self.index_builder.knowledge_graph_builder.build(
            result=result,
            index=index,
            resolved_calls=resolved_calls,
        )

        return result, index
