"""Tests for ProjectFileHashes utility class."""

from pathlib import Path
from unittest.mock import patch

from code_monkey.agents.project_librarian.utils.project_file_hashes import (
    ProjectFileHashes,
)

WORKING_DIR = Path("/fake/project")

DISCOVER = "code_monkey.agents.project_librarian.utils.project_file_hashes.discover_python_files"
COMPUTE = "code_monkey.agents.project_librarian.utils.project_file_hashes.compute_file_hash"
CACHE_MANAGER = "code_monkey.agents.project_librarian.utils.project_file_hashes.CacheManager"


class TestProjectFileHashesLoad:
    """Tests for ProjectFileHashes.load()."""

    def test_all_files_unchanged_returns_empty_dict(self) -> None:
        """When current hashes match cached hashes exactly, returns empty dict."""
        file_a = Path("/fake/project/a.py")
        file_b = Path("/fake/project/b.py")

        with (
            patch(DISCOVER, return_value=[file_a, file_b]) as mock_discover,
            patch(COMPUTE, side_effect=lambda p: {file_a: "hash_a", file_b: "hash_b"}[p]),
            patch(CACHE_MANAGER) as mock_cm_cls,
        ):
            mock_cm_cls.return_value.load_hashes.return_value = {
                str(file_a): "hash_a",
                str(file_b): "hash_b",
            }

            result = ProjectFileHashes(WORKING_DIR).load()

        assert result == {}

    def test_new_file_added_returned_with_hash(self) -> None:
        """A file present on disk but absent from cache is returned with its current hash."""
        new_file = Path("/fake/project/new.py")

        with (
            patch(DISCOVER, return_value=[new_file]),
            patch(COMPUTE, return_value="hash_new"),
            patch(CACHE_MANAGER) as mock_cm_cls,
        ):
            mock_cm_cls.return_value.load_hashes.return_value = {}

            result = ProjectFileHashes(WORKING_DIR).load()

        assert result == {str(new_file): "hash_new"}

    def test_modified_file_returned_with_new_hash(self) -> None:
        """A file whose hash differs from the cached value is returned with its new hash."""
        file = Path("/fake/project/changed.py")

        with (
            patch(DISCOVER, return_value=[file]),
            patch(COMPUTE, return_value="hash_new"),
            patch(CACHE_MANAGER) as mock_cm_cls,
        ):
            mock_cm_cls.return_value.load_hashes.return_value = {
                str(file): "hash_old",
            }

            result = ProjectFileHashes(WORKING_DIR).load()

        assert result == {str(file): "hash_new"}

    def test_deleted_file_returned_mapped_to_none(self) -> None:
        """A file present in cache but absent from disk is returned mapped to None."""
        deleted_file = "/fake/project/deleted.py"

        with (
            patch(DISCOVER, return_value=[]),
            patch(COMPUTE),
            patch(CACHE_MANAGER) as mock_cm_cls,
        ):
            mock_cm_cls.return_value.load_hashes.return_value = {
                deleted_file: "hash_old",
            }

            result = ProjectFileHashes(WORKING_DIR).load()

        assert result == {deleted_file: None}

    def test_mixed_changes_returns_only_changed_files(self) -> None:
        """Only added, modified, and deleted files are returned; unchanged files are omitted."""
        unchanged = Path("/fake/project/unchanged.py")
        added = Path("/fake/project/added.py")
        modified = Path("/fake/project/modified.py")
        deleted_path = "/fake/project/deleted.py"

        hash_map = {
            unchanged: "hash_unchanged",
            added: "hash_added",
            modified: "hash_modified_new",
        }

        with (
            patch(DISCOVER, return_value=[unchanged, added, modified]),
            patch(COMPUTE, side_effect=lambda p: hash_map[p]),
            patch(CACHE_MANAGER) as mock_cm_cls,
        ):
            mock_cm_cls.return_value.load_hashes.return_value = {
                str(unchanged): "hash_unchanged",
                str(modified): "hash_modified_old",
                deleted_path: "hash_deleted",
            }

            result = ProjectFileHashes(WORKING_DIR).load()

        assert result == {
            str(added): "hash_added",
            str(modified): "hash_modified_new",
            deleted_path: None,
        }


class TestProjectFileHashesSave:
    """Tests for ProjectFileHashes.save()."""

    def test_delegates_to_cache_manager_save_hashes(self) -> None:
        """save() passes the provided hashes to CacheManager.save_hashes."""
        hashes = {
            "/fake/project/a.py": "hash_a",
            "/fake/project/b.py": "hash_b",
        }

        with patch(CACHE_MANAGER) as mock_cm_cls:
            mock_instance = mock_cm_cls.return_value
            ProjectFileHashes(WORKING_DIR).save(hashes)

        mock_instance.save_hashes.assert_called_once_with(hashes)
