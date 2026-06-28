"""
Low-level Git operations.
"""

from pathlib import Path

from git import InvalidGitRepositoryError
from git import Repo


class GitService:

    def open_repository(
        self,
        path: str,
    ) -> Repo | None:

        try:
            return Repo(
                Path(path),
                search_parent_directories=True,
            )

        except InvalidGitRepositoryError:
            return None