"""
Project index builder.
"""

from pathlib import Path

from app.scanner.index import ProjectIndex
from app.scanner.models import FileInfo
from app.scanner.models import ProjectScanResult


class ProjectIndexBuilder:
    """
    Builds a ProjectIndex from a ProjectScanResult.
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
        ".github",
        "README.md",
        "LICENSE",
    }

    def build(
        self,
        result: ProjectScanResult,
    ) -> ProjectIndex:

        index = ProjectIndex()

        for file in result.files:

            self._index_file(index, file)

        return index

    def _index_file(
        self,
        index: ProjectIndex,
        file: FileInfo,
    ) -> None:

        path = Path(file.path)

        #
        # filename
        #

        index.files_by_name.setdefault(path.name, []).append(file)

        #
        # extension
        #

        index.files_by_extension.setdefault(
            file.extension,
            [],
        ).append(file)

        index.total_size_by_extension[file.extension] = (
            index.total_size_by_extension.get(file.extension, 0)
            + file.size
        )

        #
        # directories
        #

        if path.parent != Path("."):

            directory_path = path.parent.as_posix()
            directory_name = path.parent.name

            index.directories.add(directory_path)
            index.directories_by_name.setdefault(
                directory_name,
                directory_path,
            )

        #
        # config files
        #

        if path.name in self.KNOWN_PROJECT_FILES:

            index.config_files.setdefault(path.name, []).append(file)