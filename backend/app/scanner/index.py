"""
Project index.

Provides fast lookups over scanned project files.
"""

from dataclasses import dataclass, field

from app.scanner.models import FileInfo
from app.scanner.source_detector.models import SourceRoot
from app.scanner.import_resolver.models import ModuleInfo
from app.scanner.symbol_index import SymbolIndex
from app.scanner.knowledge_graph.graph import KnowledgeGraph


@dataclass(slots=True)
class ProjectIndex:
    """
    Runtime index built from a ProjectScanResult.

    Used internally by detectors for O(1) lookups.
    """

    # filename -> list[FileInfo]
    files_by_name: dict[str, list[FileInfo]] = field(default_factory=dict)

    # extension -> list[FileInfo]
    files_by_extension: dict[str, list[FileInfo]] = field(default_factory=dict)

    # relative directory paths
    directories: set[str] = field(default_factory=set)

    # directory name -> relative directory path
    directories_by_name: dict[str, str] = field(default_factory=dict)

    # configuration files
    config_files: dict[str, list[FileInfo]] = field(default_factory=dict)

    # extension -> cumulative file size in bytes
    total_size_by_extension: dict[str, int] = field(default_factory=dict)

    module_index: dict[str, ModuleInfo] = field(default_factory=dict)

    # resolved absolute path -> module, avoiding a full module-index scan for
    # every Python file during import resolution
    module_by_path: dict[str, ModuleInfo] = field(default_factory=dict)

    source_roots: list[SourceRoot] = field(default_factory=list)

    symbol_index: SymbolIndex = field(default_factory=SymbolIndex)

    knowledge_graph: KnowledgeGraph = field(default_factory=KnowledgeGraph)
