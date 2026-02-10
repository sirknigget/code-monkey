"""Unit tests for ProjectMapper."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_monkey.agents.project_librarian.project_mapper import ProjectMapper
from code_monkey.agents.project_librarian.summarizer import Summarizer
from code_monkey.agents.project_librarian.types import FileContext, ModuleContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PATCH_HASHES = "code_monkey.agents.project_librarian.project_mapper.ProjectFileHashes"
PATCH_CACHE = "code_monkey.agents.project_librarian.project_mapper.CacheManager"


def make_summarizer(
    file_summary: str = "file-summary",
    module_summary: str = "module-summary",
) -> MagicMock:
    """Return a MagicMock Summarizer whose methods return deterministic strings."""
    summarizer = MagicMock(spec=Summarizer)
    summarizer.summarize_file.return_value = file_summary
    summarizer.summarize_module.return_value = module_summary
    return summarizer


# ---------------------------------------------------------------------------
# TestNoChanges
# ---------------------------------------------------------------------------


class TestNoChanges:
    """When modified_files is empty and cache is fully summarized,
    the summarizer must not be called at all."""

    def test_cached_summaries_returned_unchanged(self, tmp_path: Path) -> None:
        cached_context = ModuleContext(
            summary="root-summary",
            files={
                "main.py": FileContext(summary="main-file-summary"),
            },
            submodules={
                "pkg": ModuleContext(
                    summary="pkg-summary",
                    files={"mod.py": FileContext(summary="mod-file-summary")},
                )
            },
        )
        summarizer = make_summarizer()

        with (
            patch(PATCH_HASHES) as mock_hashes,
            patch(PATCH_CACHE) as mock_cache,
        ):
            mock_hashes.return_value.load.return_value = {}
            mock_cache.return_value.load_code_context.return_value = cached_context

            result = ProjectMapper(tmp_path, summarizer).map_modules()

        summarizer.summarize_file.assert_not_called()
        summarizer.summarize_module.assert_not_called()

        assert result.summary == "root-summary"
        assert result.files["main.py"].summary == "main-file-summary"
        assert result.submodules["pkg"].summary == "pkg-summary"
        assert result.submodules["pkg"].files["mod.py"].summary == "mod-file-summary"


# ---------------------------------------------------------------------------
# TestFirstRun
# ---------------------------------------------------------------------------


class TestFirstRun:
    """When there is no cached context and modified_files contains new files,
    every file and module must be summarized."""

    def test_all_files_summarized(self, tmp_path: Path) -> None:
        # Create actual files so read_text() works
        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()
        (pkg_dir / "mod.py").write_text("def foo(): pass", encoding="utf-8")
        (tmp_path / "main.py").write_text("# main", encoding="utf-8")

        summarizer = MagicMock(spec=Summarizer)
        summarizer.summarize_file.side_effect = lambda fp, code: f"summary-of-{fp.name}"
        summarizer.summarize_module.return_value = "module-summary"

        modified_files: dict[str, str | None] = {
            str(tmp_path / "main.py"): "hash-main",
            str(pkg_dir / "mod.py"): "hash-mod",
        }

        with (
            patch(PATCH_HASHES) as mock_hashes,
            patch(PATCH_CACHE) as mock_cache,
        ):
            mock_hashes.return_value.load.return_value = modified_files
            mock_cache.return_value.load_code_context.return_value = None

            result = ProjectMapper(tmp_path, summarizer).map_modules()

        assert result.files["main.py"].summary == "summary-of-main.py"
        assert result.submodules["pkg"].files["mod.py"].summary == "summary-of-mod.py"
        assert result.submodules["pkg"].summary == "module-summary"
        assert result.summary == "module-summary"

        assert summarizer.summarize_file.call_count == 2
        assert summarizer.summarize_module.call_count == 2


# ---------------------------------------------------------------------------
# TestModifiedFile
# ---------------------------------------------------------------------------


class TestModifiedFile:
    """When one file is modified, that file gets a new summary, its parent
    module is re-summarized, and unchanged sibling files retain cached summaries."""

    def test_only_modified_file_and_parent_resummmarized(self, tmp_path: Path) -> None:
        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()
        # Only the modified file needs to exist on disk for read_text
        (pkg_dir / "changed.py").write_text("# changed", encoding="utf-8")

        cached_context = ModuleContext(
            summary="root-summary",
            submodules={
                "pkg": ModuleContext(
                    summary="pkg-old-summary",
                    files={
                        "changed.py": FileContext(summary="changed-old-summary"),
                        "stable.py": FileContext(summary="stable-summary"),
                    },
                )
            },
        )

        summarizer = MagicMock(spec=Summarizer)
        summarizer.summarize_file.return_value = "changed-new-summary"
        summarizer.summarize_module.return_value = "pkg-new-summary"

        modified_files: dict[str, str | None] = {
            str(pkg_dir / "changed.py"): "new-hash",
        }

        with (
            patch(PATCH_HASHES) as mock_hashes,
            patch(PATCH_CACHE) as mock_cache,
        ):
            mock_hashes.return_value.load.return_value = modified_files
            mock_cache.return_value.load_code_context.return_value = cached_context

            result = ProjectMapper(tmp_path, summarizer).map_modules()

        pkg = result.submodules["pkg"]
        assert pkg.files["changed.py"].summary == "changed-new-summary"
        assert pkg.files["stable.py"].summary == "stable-summary"
        assert pkg.summary == "pkg-new-summary"

        # Root was invalidated because a file changed, so it gets re-summarized
        assert result.summary == "pkg-new-summary"

        # summarize_file called once (only changed.py); stable.py retained
        summarizer.summarize_file.assert_called_once()
        call_filepath = summarizer.summarize_file.call_args[0][0]
        assert call_filepath.name == "changed.py"


# ---------------------------------------------------------------------------
# TestDeletedFile
# ---------------------------------------------------------------------------


class TestDeletedFile:
    """When a file hash is None (deleted), the file must be absent from the
    returned context and the parent module must be re-summarized."""

    def test_deleted_file_absent_and_module_resummmarized(self, tmp_path: Path) -> None:
        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()
        # "kept.py" still exists; "deleted.py" does not
        (pkg_dir / "kept.py").write_text("# kept", encoding="utf-8")

        cached_context = ModuleContext(
            summary="root-summary",
            submodules={
                "pkg": ModuleContext(
                    summary="pkg-old-summary",
                    files={
                        "deleted.py": FileContext(summary="deleted-summary"),
                        "kept.py": FileContext(summary="kept-summary"),
                    },
                )
            },
        )

        summarizer = MagicMock(spec=Summarizer)
        summarizer.summarize_file.return_value = "kept-summary-unchanged"
        summarizer.summarize_module.return_value = "pkg-new-summary"

        modified_files: dict[str, str | None] = {
            str(pkg_dir / "deleted.py"): None,
        }

        with (
            patch(PATCH_HASHES) as mock_hashes,
            patch(PATCH_CACHE) as mock_cache,
        ):
            mock_hashes.return_value.load.return_value = modified_files
            mock_cache.return_value.load_code_context.return_value = cached_context

            result = ProjectMapper(tmp_path, summarizer).map_modules()

        pkg = result.submodules["pkg"]
        assert "deleted.py" not in pkg.files
        assert "kept.py" in pkg.files
        assert pkg.summary == "pkg-new-summary"

        # summarize_file must NOT be called for the kept file (its summary is
        # already cached and its hash hasn't changed)
        summarizer.summarize_file.assert_not_called()


# ---------------------------------------------------------------------------
# TestBottomUpOrder
# ---------------------------------------------------------------------------


class TestBottomUpOrder:
    """Verify summarize_file is called before summarize_module for the same
    module, and deeper modules are processed before shallower ones."""

    def test_summarize_order(self, tmp_path: Path) -> None:
        # Structure: tmp_path/pkg/sub/deep.py  and  tmp_path/pkg/top.py
        pkg_dir = tmp_path / "pkg"
        sub_dir = pkg_dir / "sub"
        sub_dir.mkdir(parents=True)
        (sub_dir / "deep.py").write_text("# deep", encoding="utf-8")
        (pkg_dir / "top.py").write_text("# top", encoding="utf-8")

        call_log: list[str] = []

        summarizer = MagicMock(spec=Summarizer)

        def record_file(fp: Path, code: str) -> str:
            call_log.append(f"file:{fp.name}")
            return f"summary-{fp.name}"

        def record_module(directory: Path, file_infos, submodule_infos) -> str:
            call_log.append(f"module:{directory.name}")
            return f"summary-module-{directory.name}"

        summarizer.summarize_file.side_effect = record_file
        summarizer.summarize_module.side_effect = record_module

        modified_files: dict[str, str | None] = {
            str(sub_dir / "deep.py"): "h1",
            str(pkg_dir / "top.py"): "h2",
        }

        with (
            patch(PATCH_HASHES) as mock_hashes,
            patch(PATCH_CACHE) as mock_cache,
        ):
            mock_hashes.return_value.load.return_value = modified_files
            mock_cache.return_value.load_code_context.return_value = None

            ProjectMapper(tmp_path, summarizer).map_modules()

        # deep.py file summary must appear before sub module summary
        assert call_log.index("file:deep.py") < call_log.index("module:sub")
        # sub module must be summarized before pkg module
        assert call_log.index("module:sub") < call_log.index("module:pkg")
        # top.py file summary must appear before pkg module summary
        assert call_log.index("file:top.py") < call_log.index("module:pkg")
        # pkg must be summarized before the root (tmp_path folder name)
        root_name = tmp_path.name
        assert call_log.index("module:pkg") < call_log.index(f"module:{root_name}")
