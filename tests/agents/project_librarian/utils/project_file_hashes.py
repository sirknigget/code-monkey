"""Utility for computing and persisting file hash changes."""

from pathlib import Path

from code_monkey.agents.project_librarian.cache_manager import CacheManager
from code_monkey.agents.project_librarian.utils.file_discovery import (
    discover_python_files,
)
from code_monkey.agents.project_librarian.utils.hash_utils import compute_file_hash


class ProjectFileHashes:
    """Computes changed file hashes relative to a cached baseline."""

    def __init__(self, working_dir: Path) -> None:
        self.working_dir = working_dir

    def load(self) -> dict[str, str | None]:
        """Return only changed files compared to the cached hashes.

        Returns:
            A dict of changed files where:
            - Added files map to their current hash
            - Modified files map to their current hash
            - Deleted files map to None
            - Unchanged files are omitted
        """
        discovered_files = discover_python_files(root=self.working_dir)
        current_hashes: dict[str, str] = {
            str(filepath): compute_file_hash(filepath) for filepath in discovered_files
        }

        cache_manager = CacheManager(root=self.working_dir)
        cached_hashes: dict[str, str] = cache_manager.load_hashes()

        result: dict[str, str | None] = {}

        for path, current_hash in current_hashes.items():
            if path not in cached_hashes or cached_hashes[path] != current_hash:
                result[path] = current_hash

        for path in cached_hashes:
            if path not in current_hashes:
                result[path] = None

        return result

    def save(self, file_hashes: dict[str, str]) -> None:
        """Persist the given file hashes to the cache.

        Args:
            file_hashes: A mapping of file paths to their hashes.
        """
        cache_manager = CacheManager(root=self.working_dir)
        cache_manager.save_hashes(file_hashes)
