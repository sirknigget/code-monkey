"""Utility for computing and persisting file hash changes."""

from dataclasses import dataclass
from pathlib import Path

from code_monkey.agents.project_librarian.cache_manager import CacheManager
from code_monkey.agents.project_librarian.utils.file_discovery import (
    discover_python_files,
)
from code_monkey.agents.project_librarian.utils.hash_utils import compute_file_hash


@dataclass
class Hashes:
    """Result of a file hash load operation.

    Attributes:
        modified_only: Changed files only — added/modified map to their current
            hash, deleted files map to None, unchanged files are omitted.
        current: All currently discovered files mapped to their current hash.
    """

    modified_only: dict[str, str | None]
    current: dict[str, str]


class ProjectFileHashes:
    """Computes changed file hashes relative to a cached baseline."""

    def __init__(self, working_dir: Path) -> None:
        self.working_dir = working_dir

    def load(self) -> Hashes:
        """Return file hashes compared to the cached baseline.

        Returns:
            Hashes with:
            - modified_only: added/modified files (hash) and deleted files (None)
            - current: all currently discovered files with their hashes
        """
        discovered_files = discover_python_files(root=self.working_dir)
        current_hashes: dict[str, str] = {
            str(filepath): compute_file_hash(self.working_dir / filepath)
            for filepath in discovered_files
        }

        cache_manager = CacheManager(root=self.working_dir)
        cached_hashes: dict[str, str] = cache_manager.load_hashes()

        modified_only: dict[str, str | None] = {}

        for path, current_hash in current_hashes.items():
            if path not in cached_hashes or cached_hashes[path] != current_hash:
                modified_only[path] = current_hash

        for path in cached_hashes:
            if path not in current_hashes:
                modified_only[path] = None

        return Hashes(modified_only=modified_only, current=current_hashes)

    def save(self, file_hashes: dict[str, str]) -> None:
        """Persist the given file hashes to the cache.

        Args:
            file_hashes: A mapping of file paths to their hashes.
        """
        cache_manager = CacheManager(root=self.working_dir)
        cache_manager.save_hashes(file_hashes)
