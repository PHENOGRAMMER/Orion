"""
Project index builder.
"""

from pathlib import Path

from app.scanner.import_resolver.module_utils import ModuleNameBuilder
from app.scanner.index import ProjectIndex
from app.scanner.models import FileInfo, ProjectScanResult
from app.scanner.source_detector import SourceRootDetector


class ProjectIndexBuilder:
    """
    Builds fast lookup indexes for a scanned project.
    """

    KNOWN_PROJECT_FILES = {
        "package.json",
        "requirements.txt",
        "pyproject.toml",
        "Dockerfile",
        "docker-compose.yml",
        "Cargo.toml",
        "pom.xml",
        "build.gradle",
        "composer.json",
        "angular.json",
        "vite.config.ts",
        "vite.config.js",
        "next.config.js",
        "tailwind.config.js",
        "README.md",
        "LICENSE",
    }

    def __init__(self) -> None:

        self.module_builder = ModuleNameBuilder()
        self.source_detector = SourceRootDetector()

    def build(
        self,
        scan_result: ProjectScanResult,
    ) -> ProjectIndex:

        index = ProjectIndex()

        project_root = Path(scan_result.root_path).resolve()

        #
        # Detect source roots
        #

        index.source_roots = self.source_detector.detect(
            project_root,
        )

        #
        # Index every scanned file
        #

        for file in scan_result.files:

            self._index_file(
                index=index,
                file=file,
                project_root=project_root,
            )

        return index

    def _index_file(
        self,
        index: ProjectIndex,
        file: FileInfo,
        project_root: Path,
    ) -> None:

        #
        # Relative path (stored everywhere)
        #

        relative_path = Path(file.path)

        #
        # Absolute path (used internally)
        #

        absolute_path = (
            project_root / relative_path
        ).resolve()

        #
        # Filename index
        #

        index.files_by_name.setdefault(
            relative_path.name,
            [],
        ).append(file)

        #
        # Extension index
        #

        index.files_by_extension.setdefault(
            file.extension,
            [],
        ).append(file)

        index.total_size_by_extension[file.extension] = (
            index.total_size_by_extension.get(
                file.extension,
                0,
            )
            + file.size
        )

        #
        # Directory index
        #

        if relative_path.parent != Path("."):

            directory_path = relative_path.parent.as_posix()

            directory_name = relative_path.parent.name

            index.directories.add(
                directory_path,
            )

            index.directories_by_name.setdefault(
                directory_name,
                directory_path,
            )

        #
        # Project config files
        #

        if relative_path.name in self.KNOWN_PROJECT_FILES:

            index.config_files.setdefault(
                relative_path.name,
                [],
            ).append(file)

        #
        # Python module index
        #

        if file.extension == ".py":

            module_name = self.module_builder.build(
                absolute_path,
                index.source_roots,
            )

            if module_name:

                index.module_index[module_name] = (
                    relative_path
                )