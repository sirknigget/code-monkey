"""Tests for ProjectFileHashes utility class."""

from pathlib import Path
from unittest.mock import patch

from code_monkey.agents.project_librarian.utils.project_file_hashes import (
    Hashes,
    ProjectFileHashes,
)

WORKING_DIR = Path("/fake/project")

DISCOVER = "code_monkey.agents.project_librarian.utils.project_file_hashes.discover_python_files"
COMPUTE = "code_monkey.agents.project_librarian.utils.project_file_hashes.compute_file_hash"
CACHE_MANAGER = "code_monkey.agents.project_librarian.utils.project_file_hashes.CacheManager"


class TestProjectFileHashesLoad:
    """Tests for ProjectFileHashes.load()."""

    def test_all_files_unchanged_returns_empty_modified_only(self) -> None:
        """When current hashes match cached hashes exactly, modified_only is empty."""
        file_a = Path("a.py")
        file_b = Path("b.py")

        with (
            patch(DISCOVER, return_value=[file_a, file_b]),
            patch(
                COMPUTE,
                side_effect=lambda p: {
                    WORKING_DIR / file_a: "hash_a",
                    WORKING_DIR / file_b: "hash_b",
                }[p],
            ),
            patch(CACHE_MANAGER) as mock_cm_cls,
        ):
            mock_cm_cls.return_value.load_hashes.return_value = {
                str(file_a): "hash_a",
                str(file_b): "hash_b",
            }

            result = ProjectFileHashes(WORKING_DIR).load()

        assert result == Hashes(
            modified_only={},
            current={str(file_a): "hash_a", str(file_b): "hash_b"},
        )

    def test_new_file_added_returned_with_hash(self) -> None:
        """A file present on disk but absent from cache appears in modified_only and current."""
        new_file = Path("new.py")

        with (
            patch(DISCOVER, return_value=[new_file]),
            patch(COMPUTE, return_value="hash_new"),
            patch(CACHE_MANAGER) as mock_cm_cls,
        ):
            mock_cm_cls.return_value.load_hashes.return_value = {}

            result = ProjectFileHashes(WORKING_DIR).load()

        assert result == Hashes(
            modified_only={str(new_file): "hash_new"},
            current={str(new_file): "hash_new"},
        )

    def test_modified_file_returned_with_new_hash(self) -> None:
        """A file whose hash differs from cached value appears in modified_only with new hash."""
        file = Path("changed.py")

        with (
            patch(DISCOVER, return_value=[file]),
            patch(COMPUTE, return_value="hash_new"),
            patch(CACHE_MANAGER) as mock_cm_cls,
        ):
            mock_cm_cls.return_value.load_hashes.return_value = {
                str(file): "hash_old",
            }

            result = ProjectFileHashes(WORKING_DIR).load()

        assert result == Hashes(
            modified_only={str(file): "hash_new"},
            current={str(file): "hash_new"},
        )

    def test_deleted_file_returned_mapped_to_none(self) -> None:
        """A file present in cache but absent from disk appears in modified_only mapped to None."""
        deleted_file = "deleted.py"

        with (
            patch(DISCOVER, return_value=[]),
            patch(COMPUTE),
            patch(CACHE_MANAGER) as mock_cm_cls,
        ):
            mock_cm_cls.return_value.load_hashes.return_value = {
                deleted_file: "hash_old",
            }

            result = ProjectFileHashes(WORKING_DIR).load()

        assert result == Hashes(
            modified_only={deleted_file: None},
            current={},
        )

    def test_mixed_changes(self) -> None:
        """modified_only contains only changed files; current contains all discovered files."""
        unchanged = Path("unchanged.py")
        added = Path("added.py")
        modified = Path("modified.py")
        deleted_path = "deleted.py"

        hash_map = {
            WORKING_DIR / unchanged: "hash_unchanged",
            WORKING_DIR / added: "hash_added",
            WORKING_DIR / modified: "hash_modified_new",
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

        assert result == Hashes(
            modified_only={
                str(added): "hash_added",
                str(modified): "hash_modified_new",
                deleted_path: None,
            },
            current={
                str(unchanged): "hash_unchanged",
                str(added): "hash_added",
                str(modified): "hash_modified_new",
            },
        )


class TestProjectFileHashesSave:
    """Tests for ProjectFileHashes.save()."""

    def test_delegates_to_cache_manager_save_hashes(self) -> None:
        """save() passes the provided hashes to CacheManager.save_hashes."""
        hashes = {
            "a.py": "hash_a",
            "b.py": "hash_b",
        }

        with patch(CACHE_MANAGER) as mock_cm_cls:
            mock_instance = mock_cm_cls.return_value
            ProjectFileHashes(WORKING_DIR).save(hashes)

        mock_instance.save_hashes.assert_called_once_with(hashes)
