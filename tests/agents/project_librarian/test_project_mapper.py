"""Unit tests for ProjectMapper."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_monkey.agents.project_librarian.project_mapper import ProjectMapper
from code_monkey.agents.project_librarian.summarizer import Summarizer
from code_monkey.agents.project_librarian.types import FileContext, ModuleContext
from code_monkey.agents.project_librarian.utils.project_file_hashes import Hashes

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PATCH_HASHES = "code_monkey.agents.project_librarian.project_mapper.ProjectFileHashes"
PATCH_CACHE = "code_monkey.agents.project_librarian.project_mapper.CacheManager"
PATCH_STRUCTURE = "code_monkey.agents.project_librarian.project_mapper.ProjectStructure"


def make_summarizer(
    file_summary: str = "file-summary",
    module_summary: str = "module-summary",
    project_summary: str = "project-summary",
) -> MagicMock:
    """Return a MagicMock Summarizer whose methods return deterministic strings."""
    summarizer = MagicMock(spec=Summarizer)
    summarizer.summarize_file.return_value = file_summary
    summarizer.summarize_module.return_value = module_summary
    summarizer.summarize_project.return_value = project_summary
    return summarizer


# ---------------------------------------------------------------------------
# TestNoChanges
# ---------------------------------------------------------------------------


class TestNoChanges:
    """When modified_files is empty and cache is fully summarized,
    file and module summarizers must not be called; project summary is always
    regenerated and all outputs are persisted to cache."""

    @pytest.mark.asyncio
    async def test_cached_summaries_persisted_unchanged(self, tmp_path: Path) -> None:
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
            patch(PATCH_STRUCTURE) as mock_structure,
        ):
            mock_hashes.return_value.load.return_value = Hashes(
                modified_only={}, current={}
            )
            mock_cache.return_value.load_code_context.return_value = cached_context
            mock_structure.return_value.build.return_value = "project-structure"

            await ProjectMapper(tmp_path, summarizer).map_project()

        summarizer.summarize_file.assert_not_called()
        summarizer.summarize_module.assert_not_called()
        summarizer.summarize_project.assert_called_once()

        saved_context = mock_cache.return_value.save_code_context.call_args[0][0]
        assert saved_context.summary == "root-summary"
        assert saved_context.files["main.py"].summary == "main-file-summary"
        assert saved_context.submodules["pkg"].summary == "pkg-summary"
        assert (
            saved_context.submodules["pkg"].files["mod.py"].summary
            == "mod-file-summary"
        )

        mock_cache.return_value.save_project_context.assert_called_once_with(
            "project-summary"
        )
        mock_cache.return_value.save_hashes.assert_called_once_with({})


# ---------------------------------------------------------------------------
# TestFirstRun
# ---------------------------------------------------------------------------


class TestFirstRun:
    """When there is no cached context and modified_files contains new files,
    every file and module must be summarized and all outputs persisted."""

    @pytest.mark.asyncio
    async def test_all_files_summarized_and_saved(self, tmp_path: Path) -> None:
        # Create actual files so read_text() works
        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()
        (pkg_dir / "mod.py").write_text("def foo(): pass", encoding="utf-8")
        (tmp_path / "main.py").write_text("# main", encoding="utf-8")

        summarizer = MagicMock(spec=Summarizer)
        summarizer.summarize_file.side_effect = lambda fp, code: f"summary-of-{fp.name}"
        summarizer.summarize_module.return_value = "module-summary"
        summarizer.summarize_project.return_value = "project-summary"

        modified_files: dict[str, str | None] = {
            "main.py": "hash-main",
            "pkg/mod.py": "hash-mod",
        }
        current: dict[str, str] = {"main.py": "hash-main", "pkg/mod.py": "hash-mod"}

        with (
            patch(PATCH_HASHES) as mock_hashes,
            patch(PATCH_CACHE) as mock_cache,
            patch(PATCH_STRUCTURE) as mock_structure,
        ):
            mock_hashes.return_value.load.return_value = Hashes(
                modified_only=modified_files, current=current
            )
            mock_cache.return_value.load_code_context.return_value = None
            mock_structure.return_value.build.return_value = "project-structure"

            await ProjectMapper(tmp_path, summarizer).map_project()

        assert summarizer.summarize_file.call_count == 2
        assert summarizer.summarize_module.call_count == 2
        summarizer.summarize_project.assert_called_once()

        saved_context = mock_cache.return_value.save_code_context.call_args[0][0]
        assert saved_context.files["main.py"].summary == "summary-of-main.py"
        assert (
            saved_context.submodules["pkg"].files["mod.py"].summary
            == "summary-of-mod.py"
        )
        assert saved_context.submodules["pkg"].summary == "module-summary"

        mock_cache.return_value.save_project_context.assert_called_once_with(
            "project-summary"
        )
        mock_cache.return_value.save_hashes.assert_called_once_with(current)


# ---------------------------------------------------------------------------
# TestModifiedFile
# ---------------------------------------------------------------------------


class TestModifiedFile:
    """When one file is modified, that file gets a new summary, its parent
    module is re-summarized, and unchanged sibling files retain cached summaries."""

    @pytest.mark.asyncio
    async def test_only_modified_file_and_parent_resummarized(
        self, tmp_path: Path
    ) -> None:
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
        summarizer.summarize_project.return_value = "project-summary"

        modified_files: dict[str, str | None] = {"pkg/changed.py": "new-hash"}
        current: dict[str, str] = {
            "pkg/changed.py": "new-hash",
            "pkg/stable.py": "stable-hash",
        }

        with (
            patch(PATCH_HASHES) as mock_hashes,
            patch(PATCH_CACHE) as mock_cache,
            patch(PATCH_STRUCTURE) as mock_structure,
        ):
            mock_hashes.return_value.load.return_value = Hashes(
                modified_only=modified_files, current=current
            )
            mock_cache.return_value.load_code_context.return_value = cached_context
            mock_structure.return_value.build.return_value = "project-structure"

            await ProjectMapper(tmp_path, summarizer).map_project()

        saved_context = mock_cache.return_value.save_code_context.call_args[0][0]
        pkg = saved_context.submodules["pkg"]
        assert pkg.files["changed.py"].summary == "changed-new-summary"
        assert pkg.files["stable.py"].summary == "stable-summary"
        assert pkg.summary == "pkg-new-summary"
        # Root was invalidated because a file changed
        assert saved_context.summary == "pkg-new-summary"

        # summarize_file called once (only changed.py); stable.py retained
        summarizer.summarize_file.assert_called_once()
        # pkg and root are re-summarized (changed.py's parent + root)
        assert summarizer.summarize_module.call_count == 2
        summarizer.summarize_project.assert_called_once()


# ---------------------------------------------------------------------------
# TestDeletedFile
# ---------------------------------------------------------------------------


class TestDeletedFile:
    """When a file hash is None (deleted), the file must be absent from the
    saved context and empty modules must be pruned."""

    @pytest.mark.asyncio
    async def test_deleted_file_absent_and_module_resummarized(
        self, tmp_path: Path
    ) -> None:
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
        summarizer.summarize_project.return_value = "project-summary"

        modified_files: dict[str, str | None] = {"pkg/deleted.py": None}
        current: dict[str, str] = {"pkg/kept.py": "kept-hash"}

        with (
            patch(PATCH_HASHES) as mock_hashes,
            patch(PATCH_CACHE) as mock_cache,
            patch(PATCH_STRUCTURE) as mock_structure,
        ):
            mock_hashes.return_value.load.return_value = Hashes(
                modified_only=modified_files, current=current
            )
            mock_cache.return_value.load_code_context.return_value = cached_context
            mock_structure.return_value.build.return_value = "project-structure"

            await ProjectMapper(tmp_path, summarizer).map_project()

        saved_context = mock_cache.return_value.save_code_context.call_args[0][0]
        pkg = saved_context.submodules["pkg"]
        assert "deleted.py" not in pkg.files
        assert "kept.py" in pkg.files
        assert pkg.summary == "pkg-new-summary"

        # summarize_file must NOT be called for the kept file (its summary is cached)
        summarizer.summarize_file.assert_not_called()
        # pkg and root are re-summarized (deleted file's parent + root)
        assert summarizer.summarize_module.call_count == 2
        summarizer.summarize_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_deleted_last_file_prunes_empty_module(self, tmp_path: Path) -> None:
        cached_context = ModuleContext(
            summary="root-summary",
            submodules={
                "pkg": ModuleContext(
                    summary="pkg-old-summary",
                    files={
                        "deleted.py": FileContext(summary="deleted-summary"),
                    },
                )
            },
        )

        summarizer = MagicMock(spec=Summarizer)
        summarizer.summarize_module.return_value = "root-new-summary"
        summarizer.summarize_project.return_value = "project-summary"

        modified_files: dict[str, str | None] = {"pkg/deleted.py": None}

        with (
            patch(PATCH_HASHES) as mock_hashes,
            patch(PATCH_CACHE) as mock_cache,
            patch(PATCH_STRUCTURE) as mock_structure,
        ):
            mock_hashes.return_value.load.return_value = Hashes(
                modified_only=modified_files, current={}
            )
            mock_cache.return_value.load_code_context.return_value = cached_context
            mock_structure.return_value.build.return_value = "project-structure"

            await ProjectMapper(tmp_path, summarizer).map_project()

        saved_context = mock_cache.return_value.save_code_context.call_args[0][0]
        assert "pkg" not in saved_context.submodules
        summarizer.summarize_file.assert_not_called()
        summarizer.summarize_module.assert_called_once()
        summarizer.summarize_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_deleted_last_file_prunes_empty_ancestor_modules(
        self, tmp_path: Path
    ) -> None:
        cached_context = ModuleContext(
            summary="root-summary",
            submodules={
                "pkg": ModuleContext(
                    summary="pkg-old-summary",
                    submodules={
                        "sub": ModuleContext(
                            summary="sub-old-summary",
                            files={
                                "deleted.py": FileContext(summary="deleted-summary"),
                            },
                        )
                    },
                )
            },
        )

        summarizer = MagicMock(spec=Summarizer)
        summarizer.summarize_module.return_value = "root-new-summary"
        summarizer.summarize_project.return_value = "project-summary"

        modified_files: dict[str, str | None] = {"pkg/sub/deleted.py": None}

        with (
            patch(PATCH_HASHES) as mock_hashes,
            patch(PATCH_CACHE) as mock_cache,
            patch(PATCH_STRUCTURE) as mock_structure,
        ):
            mock_hashes.return_value.load.return_value = Hashes(
                modified_only=modified_files, current={}
            )
            mock_cache.return_value.load_code_context.return_value = cached_context
            mock_structure.return_value.build.return_value = "project-structure"

            await ProjectMapper(tmp_path, summarizer).map_project()

        saved_context = mock_cache.return_value.save_code_context.call_args[0][0]
        assert "pkg" not in saved_context.submodules
        summarizer.summarize_file.assert_not_called()
        summarizer.summarize_module.assert_called_once()
        summarizer.summarize_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_deleting_multiple_files_prunes_module_once_empty(
        self, tmp_path: Path
    ) -> None:
        cached_context = ModuleContext(
            summary="root-summary",
            submodules={
                "pkg": ModuleContext(
                    summary="pkg-old-summary",
                    files={
                        "first.py": FileContext(summary="first-summary"),
                        "second.py": FileContext(summary="second-summary"),
                    },
                )
            },
        )

        summarizer = MagicMock(spec=Summarizer)
        summarizer.summarize_module.return_value = "root-new-summary"
        summarizer.summarize_project.return_value = "project-summary"

        modified_files: dict[str, str | None] = {
            "pkg/first.py": None,
            "pkg/second.py": None,
        }

        with (
            patch(PATCH_HASHES) as mock_hashes,
            patch(PATCH_CACHE) as mock_cache,
            patch(PATCH_STRUCTURE) as mock_structure,
        ):
            mock_hashes.return_value.load.return_value = Hashes(
                modified_only=modified_files, current={}
            )
            mock_cache.return_value.load_code_context.return_value = cached_context
            mock_structure.return_value.build.return_value = "project-structure"

            await ProjectMapper(tmp_path, summarizer).map_project()

        saved_context = mock_cache.return_value.save_code_context.call_args[0][0]
        assert "pkg" not in saved_context.submodules
        summarizer.summarize_file.assert_not_called()
        summarizer.summarize_module.assert_called_once()
        summarizer.summarize_project.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "modified_files",
        [
            {"pkg/deleted.py": None, "pkg/added.py": "added-hash"},
            {"pkg/added.py": "added-hash", "pkg/deleted.py": None},
        ],
    )
    async def test_delete_and_add_in_same_module_does_not_prune_module(
        self, tmp_path: Path, modified_files: dict[str, str | None]
    ) -> None:
        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()
        (pkg_dir / "added.py").write_text("# added", encoding="utf-8")

        cached_context = ModuleContext(
            summary="root-summary",
            submodules={
                "pkg": ModuleContext(
                    summary="pkg-old-summary",
                    files={
                        "deleted.py": FileContext(summary="deleted-summary"),
                    },
                )
            },
        )

        summarizer = MagicMock(spec=Summarizer)
        summarizer.summarize_file.return_value = "added-summary"
        summarizer.summarize_module.side_effect = [
            "pkg-new-summary",
            "root-new-summary",
        ]
        summarizer.summarize_project.return_value = "project-summary"

        current: dict[str, str] = {"pkg/added.py": "added-hash"}

        with (
            patch(PATCH_HASHES) as mock_hashes,
            patch(PATCH_CACHE) as mock_cache,
            patch(PATCH_STRUCTURE) as mock_structure,
        ):
            mock_hashes.return_value.load.return_value = Hashes(
                modified_only=modified_files, current=current
            )
            mock_cache.return_value.load_code_context.return_value = cached_context
            mock_structure.return_value.build.return_value = "project-structure"

            await ProjectMapper(tmp_path, summarizer).map_project()

        saved_context = mock_cache.return_value.save_code_context.call_args[0][0]
        pkg = saved_context.submodules["pkg"]
        assert "deleted.py" not in pkg.files
        assert pkg.files["added.py"].summary == "added-summary"
        assert pkg.summary == "pkg-new-summary"
        assert saved_context.summary == "root-new-summary"
        summarizer.summarize_file.assert_called_once()
        assert summarizer.summarize_module.call_count == 2
        summarizer.summarize_project.assert_called_once()


# ---------------------------------------------------------------------------
# TestWholeTreePrune
# ---------------------------------------------------------------------------


class TestWholeTreePrune:
    """Whole-tree prune should clean stale empty modules after build-phase mutations."""

    @pytest.mark.asyncio
    async def test_stale_empty_cached_submodule_pruned_on_unrelated_change(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "main.py").write_text("# main", encoding="utf-8")

        cached_context = ModuleContext(
            summary="root-summary",
            files={"main.py": FileContext(summary="main-summary")},
            submodules={
                "stale": ModuleContext(summary="stale-summary"),
            },
        )

        summarizer = MagicMock(spec=Summarizer)
        summarizer.summarize_file.return_value = "main-new-summary"
        summarizer.summarize_module.return_value = "root-new-summary"
        summarizer.summarize_project.return_value = "project-summary"

        modified_files: dict[str, str | None] = {"main.py": "main-new-hash"}
        current: dict[str, str] = {"main.py": "main-new-hash"}

        with (
            patch(PATCH_HASHES) as mock_hashes,
            patch(PATCH_CACHE) as mock_cache,
            patch(PATCH_STRUCTURE) as mock_structure,
        ):
            mock_hashes.return_value.load.return_value = Hashes(
                modified_only=modified_files, current=current
            )
            mock_cache.return_value.load_code_context.return_value = cached_context
            mock_structure.return_value.build.return_value = "project-structure"

            await ProjectMapper(tmp_path, summarizer).map_project()

        saved_context = mock_cache.return_value.save_code_context.call_args[0][0]
        assert "stale" not in saved_context.submodules
        assert saved_context.files["main.py"].summary == "main-new-summary"
        assert saved_context.summary == "root-new-summary"
        summarizer.summarize_file.assert_called_once()
        summarizer.summarize_module.assert_called_once()
        summarizer.summarize_project.assert_called_once()


# ---------------------------------------------------------------------------
# TestBottomUpOrder
# ---------------------------------------------------------------------------


class TestBottomUpOrder:
    """Verify summarize_file is called before summarize_module for the same
    module, and deeper modules are processed before shallower ones."""

    @pytest.mark.asyncio
    async def test_summarize_order(self, tmp_path: Path) -> None:
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
        summarizer.summarize_project.return_value = "project-summary"

        modified_files: dict[str, str | None] = {
            "pkg/sub/deep.py": "h1",
            "pkg/top.py": "h2",
        }

        with (
            patch(PATCH_HASHES) as mock_hashes,
            patch(PATCH_CACHE) as mock_cache,
            patch(PATCH_STRUCTURE) as mock_structure,
        ):
            mock_hashes.return_value.load.return_value = Hashes(
                modified_only=modified_files, current={}
            )
            mock_cache.return_value.load_code_context.return_value = None
            mock_structure.return_value.build.return_value = "project-structure"

            await ProjectMapper(tmp_path, summarizer).map_project()

        # 2 files changed → 2 file summarizations
        assert summarizer.summarize_file.call_count == 2
        # sub + pkg + root → 3 module summarizations
        assert summarizer.summarize_module.call_count == 3

        # deep.py file summary must appear before sub module summary
        assert call_log.index("file:deep.py") < call_log.index("module:sub")
        # sub module must be summarized before pkg module
        assert call_log.index("module:sub") < call_log.index("module:pkg")
        # top.py file summary must appear before pkg module summary
        assert call_log.index("file:top.py") < call_log.index("module:pkg")
        # pkg must be summarized before the root (tmp_path folder name)
        root_name = tmp_path.name
        assert call_log.index("module:pkg") < call_log.index(f"module:{root_name}")


# ---------------------------------------------------------------------------
# TestSaveOrder
# ---------------------------------------------------------------------------


class TestSaveOrder:
    """Verify that hashes are saved last — after code context and project context."""

    @pytest.mark.asyncio
    async def test_hashes_saved_after_context(self, tmp_path: Path) -> None:
        summarizer = make_summarizer()
        save_order: list[str] = []

        with (
            patch(PATCH_HASHES) as mock_hashes,
            patch(PATCH_CACHE) as mock_cache,
            patch(PATCH_STRUCTURE) as mock_structure,
        ):
            mock_hashes.return_value.load.return_value = Hashes(
                modified_only={}, current={}
            )
            mock_cache.return_value.load_code_context.return_value = None
            mock_structure.return_value.build.return_value = "project-structure"

            mock_cache.return_value.save_code_context.side_effect = lambda _: (
                save_order.append("code")
            )
            mock_cache.return_value.save_project_context.side_effect = lambda _: (
                save_order.append("project")
            )
            mock_cache.return_value.save_hashes.side_effect = lambda _: (
                save_order.append("hashes")
            )

            await ProjectMapper(tmp_path, summarizer).map_project()

        assert save_order == ["code", "project", "hashes"]
        # No files → no file summarizations; empty root still gets module-summarized
        assert summarizer.summarize_file.call_count == 0
        assert summarizer.summarize_module.call_count == 1


# ---------------------------------------------------------------------------
# TestGetters
# ---------------------------------------------------------------------------


class TestGetters:
    """get_code_context and get_project_context delegate to CacheManager."""

    def test_get_project_context_returns_cached_value(self, tmp_path: Path) -> None:
        summarizer = make_summarizer()
        with patch(PATCH_CACHE) as mock_cache:
            mock_cache.return_value.load_project_context.return_value = (
                "my project summary"
            )
            mapper = ProjectMapper(tmp_path, summarizer)
            result = mapper.get_project_context()
        assert result == "my project summary"

    def test_get_project_context_returns_none_when_missing(
        self, tmp_path: Path
    ) -> None:
        summarizer = make_summarizer()
        with patch(PATCH_CACHE) as mock_cache:
            mock_cache.return_value.load_project_context.return_value = None
            mapper = ProjectMapper(tmp_path, summarizer)
            result = mapper.get_project_context()
        assert result is None

    def test_get_code_context_returns_cached_value(self, tmp_path: Path) -> None:
        summarizer = make_summarizer()
        cached = ModuleContext(summary="root", files={}, submodules={})
        with patch(PATCH_CACHE) as mock_cache:
            mock_cache.return_value.load_code_context.return_value = cached
            mapper = ProjectMapper(tmp_path, summarizer)
            result = mapper.get_code_context()
        assert result is cached

    def test_get_code_context_returns_none_when_missing(self, tmp_path: Path) -> None:
        summarizer = make_summarizer()
        with patch(PATCH_CACHE) as mock_cache:
            mock_cache.return_value.load_code_context.return_value = None
            mapper = ProjectMapper(tmp_path, summarizer)
            result = mapper.get_code_context()
        assert result is None
