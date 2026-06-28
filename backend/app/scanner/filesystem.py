"""
Filesystem scanner.

Scans a project directory recursively and gathers
basic metadata and statistics.

No AI.
No FastAPI.
No Git.
"""

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
import hashlib

from app.scanner.constants import (
    DEFAULT_IGNORE_DIRS,
    DEFAULT_IGNORE_FILES,
    SUPPORTED_EXTENSIONS,
)

from app.scanner.models import (
    DirectoryScanResult,
    FileInfo,
    ProjectScanResult,
    ProjectStatistics,
)


class FileSystemScanner:
    """Filesystem scanner."""

    _TIMEZONES = {
        "GMT": timezone.utc,
        "UTC": timezone.utc,
        "IST": timezone(timedelta(hours=5, minutes=30)),
    }

    def scan(
            self,
            path: str,
            include_files: bool = True,
            time_zone: str = "GMT",
            ) -> ProjectScanResult:

        root = Path(path)
        project_id = hashlib.sha256(
            root.resolve().as_posix().lower().encode("utf-8")
            ).hexdigest()

        if not root.exists():
            raise FileNotFoundError(path)

        if not root.is_dir():
            raise NotADirectoryError(path)

        result = self._scan_directory(
            root=root,
            current=root,
            depth=0,
            include_files=include_files,
            time_zone=time_zone,
            )

        self._calculate_average_size(result.statistics)

        return ProjectScanResult(
            project_id=project_id,
            project_name=root.name,
            root_path=str(root.resolve()),
            statistics=result.statistics,
            files=result.files,
        )

    def _scan_directory(
            self,
            root: Path,
            current: Path,
            depth: int,
            include_files: bool,
            time_zone: str,
        ) -> DirectoryScanResult:

        result = DirectoryScanResult()

        try:

            for item in current.iterdir():

                if self._should_ignore(item):
                    continue

                if item.is_dir():

                    result.statistics.total_directories += 1

                    self._update_max_depth(
                        result.statistics,
                        depth + 1,
                    )

                    child = self._scan_directory(
                        root=root,
                        current=item,
                        depth=depth + 1,
                        include_files=include_files,
                        time_zone=time_zone,
                    )

                    result.statistics.total_files += (
                        child.statistics.total_files
                    )

                    result.statistics.total_directories += (
                        child.statistics.total_directories
                    )

                    result.statistics.total_size += (
                        child.statistics.total_size
                    )

                    self._merge_extensions(
                        result.statistics.extensions,
                        child.statistics.extensions,
                    )

                    result.statistics.hidden_files += (
                        child.statistics.hidden_files
                    )

                    result.statistics.max_depth = max(
                        result.statistics.max_depth,
                        child.statistics.max_depth,
                    )

                    result.files.extend(child.files)

                elif item.is_file():

                    info = self._create_file_info(item, root, time_zone)

                    if include_files:
                        result.files.append(info)

                    result.statistics.total_files += 1
                    result.statistics.total_size += info.size

                    self._update_extension_stats(
                        result.statistics,
                        info.extension,
                    )

                    self._update_hidden_files(
                    result.statistics,
                    item,
                    )

                    

        except PermissionError:
            pass

        return result

    def _should_ignore(
        self,
        path: Path,
    ) -> bool:

        if path.is_dir():
            return path.name in DEFAULT_IGNORE_DIRS

        if path.name in DEFAULT_IGNORE_FILES:
            return True

        if path.suffix:
            return (
                path.suffix.lower()
                not in SUPPORTED_EXTENSIONS
            )

        return False

    def _create_file_info(
        self,
        file_path: Path,
        root: Path,
        time_zone: str,
        ) -> FileInfo:

        tz = self._get_timezone(time_zone)

        try:
            stats = file_path.stat()
        except OSError:
            return FileInfo(
                path=file_path.relative_to(root).as_posix(),
                extension=file_path.suffix.lower(),
                size=0,
                modified_time=datetime.fromtimestamp(0, tz=tz),
                created_time=datetime.fromtimestamp(0, tz=tz),
            )

        created_timestamp = getattr(
            stats,
            "st_birthtime",
            stats.st_ctime,
        )

        return FileInfo(
            path=file_path.relative_to(root).as_posix(),
            extension=file_path.suffix.lower(),
            size=stats.st_size,
            modified_time=datetime.fromtimestamp(
                stats.st_mtime,
                tz=tz,
            ),
            created_time=datetime.fromtimestamp(
                created_timestamp,
                tz=tz,
            ),
        )

    def _get_timezone(self, time_zone: str):

        normalized = time_zone.upper()

        if normalized not in self._TIMEZONES:
            raise ValueError("time_zone must be 'GMT', 'UTC', or 'IST'")

        return self._TIMEZONES[normalized]


    def _update_extension_stats(
        self,
        statistics:ProjectStatistics,
        extension: str,
    ) -> None:

        if extension == "":
            extension = "no_extension"

        statistics.extensions.setdefault(extension, 0)

        statistics.extensions[extension] += 1

    def _merge_extensions(
        self,
        target: dict[str, int],
        source: dict[str, int],
    ) -> None:

        for ext, count in source.items():

            target[ext] = target.get(ext, 0) + count

    def _update_hidden_files(
        self,
        statistics: ProjectStatistics,
        file_path: Path,
    ) -> None:

        if file_path.name.startswith("."):
            statistics.hidden_files += 1

    def _update_max_depth(
        self,
        statistics: ProjectStatistics,
        depth: int,
    ) -> None:

        statistics.max_depth = max(
            statistics.max_depth,
            depth,
        )

    def _calculate_average_size(
        self,
        statistics: ProjectStatistics,
    ) -> None:

        if statistics.total_files == 0:
            statistics.average_file_size = 0
            return

        statistics.average_file_size = round(
            statistics.total_size
            / statistics.total_files,
            2,
        )