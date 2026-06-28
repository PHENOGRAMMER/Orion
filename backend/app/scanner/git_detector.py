"""
Git repository detector.
"""

from git import GitCommandError

from app.scanner.git_service import GitService
from app.scanner.models import ProjectScanResult


class GitDetector:

    def __init__(self):

        self.git = GitService()

    def analyze(
        self,
        result: ProjectScanResult,
    ) -> ProjectScanResult:

        repo = self.git.open_repository(
            result.root_path
        )

        if repo is None:
            return result

        git = result.git_statistics

        git.is_git_repository = True

        git.repository_root = repo.working_tree_dir

        git.current_branch = repo.active_branch.name

        git.dirty = repo.is_dirty()

        git.untracked_files = list(
            repo.untracked_files
        )

        git.total_commits = sum(
            1 for _ in repo.iter_commits()
        )

        #
        # Last commit
        #

        commit = repo.head.commit

        git.last_commit_hash = commit.hexsha

        git.last_commit_author = commit.author.name
        git.last_commit_email = commit.author.email

        git.last_commit_date = (
            commit.committed_datetime
        )

        #
        # Tags
        #

        git.tags = [
            tag.name
            for tag in repo.tags
        ]

        #
        # Remotes
        #

        git.remotes = {
            remote.name: next(remote.urls)
            for remote in repo.remotes
        }

        #
        # Default branch
        #

        try:

            git.default_branch = (
                repo.git.symbolic_ref(
                    "refs/remotes/origin/HEAD"
                )
                .split("/")[-1]
            )

        except GitCommandError:

            pass

        return result