"""Tests for ProjectMapper class."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_monkey.agents.project_librarian.cache_manager import (
    CacheManager,
    CodeContext,
    ModuleContext,
    FileContext,
)
from code_monkey.agents.project_librarian.project_mapper import (
    ProjectMapper,
    ProjectMapperResult,
)


class TestProjectMapperInitialization:
    """Tests for ProjectMapper initialization."""

    def test_initializes_root_and_llm(self, tmp_path: Path) -> None:
        """Should initialize with root and LLM."""
        mock_llm = MagicMock()

        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        assert mapper.root == tmp_path
        assert mapper.llm == mock_llm

    def test_default_cache_dir_is_codemonkey(self, tmp_path: Path) -> None:
        """Should default cache dir to root/.codemonkey."""
        mock_llm = MagicMock()

        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        expected = tmp_path / ".codemonkey"
        assert mapper._cache.cache_dir == expected

    def test_cache_is_cache_manager_instance(self, tmp_path: Path) -> None:
        """Should create CacheManager instance."""
        mock_llm = MagicMock()

        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        assert isinstance(mapper._cache, CacheManager)


class TestProjectMapperResult:
    """Tests for ProjectMapperResult class."""

    def test_creates_with_contexts(self) -> None:
        """Should create with code_context and project_context."""
        code_ctx = CodeContext(root_summary="root", modules={})
        result = ProjectMapperResult(
            code_context=code_ctx,
            project_context="project context",
        )

        assert result.code_context == code_ctx
        assert result.project_context == "project context"

    def test_repr_format(self) -> None:
        """Should have readable string representation."""
        code_ctx = CodeContext(
            root_summary="root",
            modules={"pkg": ModuleContext(summary="pkg", files={}, submodules={})},
        )
        result = ProjectMapperResult(
            code_context=code_ctx,
            project_context="context",
        )

        repr_str = repr(result)
        assert "modules=1" in repr_str


class TestComputeFileHashes:
    """Tests for file hash computation."""

    def test_computes_hashes_for_python_files(self, tmp_path: Path) -> None:
        """Should compute hashes for all Python files."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "file1.py").write_text("x = 1")
        (tmp_path / "file2.py").write_text("y = 2")

        result = mapper._compute_file_hashes()

        assert len(result) == 2
        assert all(isinstance(h, str) and len(h) == 64 for h in result.values())

    def test_returns_empty_dict_for_no_files(self, tmp_path: Path) -> None:
        """Should return empty dict when no Python files exist."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        result = mapper._compute_file_hashes()

        assert result == {}

    def test_hashes_are_deterministic(self, tmp_path: Path) -> None:
        """Same content should produce same hash."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "file.py").write_text("x = 1")

        hash1 = mapper._compute_file_hashes()[str(tmp_path / "file.py")]
        hash2 = mapper._compute_file_hashes()[str(tmp_path / "file.py")]

        assert hash1 == hash2

    def test_different_content_produces_different_hash(self, tmp_path: Path) -> None:
        """Different content should produce different hash."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "file.py").write_text("x = 1")
        hash1 = mapper._compute_file_hashes()[str(tmp_path / "file.py")]

        (tmp_path / "file.py").write_text("x = 2")
        hash2 = mapper._compute_file_hashes()[str(tmp_path / "file.py")]

        assert hash1 != hash2

    def test_ignores_non_python_files(self, tmp_path: Path) -> None:
        """Should only compute hashes for .py files."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "file.py").write_text("x = 1")
        (tmp_path / "readme.md").write_text("# Readme")
        (tmp_path / "config.json").write_text("{}")

        result = mapper._compute_file_hashes()

        assert len(result) == 1
        assert str(tmp_path / "file.py") in result

    def test_excludes_pycache_and_venvs(self, tmp_path: Path) -> None:
        """Should exclude __pycache__, .venv directories."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "main.py").write_text("x = 1")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "cache.py").write_text("x = 1")
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "lib").mkdir()
        (tmp_path / ".venv" / "lib" / "package.py").write_text("x = 1")

        result = mapper._compute_file_hashes()

        assert len(result) == 1
        assert str(tmp_path / "main.py") in result


class TestBuildModulePath:
    """Tests for _build_module_path method."""

    def test_root_module(self, tmp_path: Path) -> None:
        """Root directory should return empty tuple."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        result = mapper._build_module_path(tmp_path)

        assert result == ()

    def test_single_level_module(self, tmp_path: Path) -> None:
        """Single level directory should return single tuple."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        result = mapper._build_module_path(pkg_dir)

        assert result == ("pkg",)

    def test_nested_module(self, tmp_path: Path) -> None:
        """Nested directory should return path tuple."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        nested = tmp_path / "pkg" / "subpkg" / "deeper"
        nested.mkdir(parents=True)

        result = mapper._build_module_path(nested)

        assert result == ("pkg", "subpkg", "deeper")


class TestGetSetModule:
    """Tests for _get_module and _set_module methods."""

    def test_get_module_returns_none_for_empty(self, tmp_path: Path) -> None:
        """Should return None for empty context."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        ctx = CodeContext(root_summary="", modules={})
        result = mapper._get_module(ctx, ("pkg",))

        assert result is None

    def test_get_module_returns_module(self, tmp_path: Path) -> None:
        """Should return module at path."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        module = ModuleContext(summary="pkg", files={}, submodules={})
        ctx = CodeContext(root_summary="", modules={"pkg": module})
        result = mapper._get_module(ctx, ("pkg",))

        assert result is not None
        assert result.summary == "pkg"

    def test_set_module_creates_new(self, tmp_path: Path) -> None:
        """Should create new module at path."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        ctx = CodeContext(root_summary="", modules={})
        module = ModuleContext(summary="pkg", files={}, submodules={})
        result = mapper._set_module(ctx, ("pkg",), module)

        assert "pkg" in result.modules
        assert result.modules["pkg"].summary == "pkg"

    def test_set_module_preserves_existing(self, tmp_path: Path) -> None:
        """Should preserve existing modules when setting new one."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        existing = ModuleContext(summary="existing", files={}, submodules={})
        ctx = CodeContext(root_summary="", modules={"existing": existing})
        new_module = ModuleContext(summary="new", files={}, submodules={})
        result = mapper._set_module(ctx, ("new",), new_module)

        assert "existing" in result.modules
        assert "new" in result.modules
        assert result.modules["existing"].summary == "existing"


class TestProcessFile:
    """Tests for _process_file method."""

    def test_process_file_returns_file_context(self, tmp_path: Path) -> None:
        """Should return FileContext for a file."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "test.py").write_text("x = 1")

        with patch.object(mapper._summarizer, 'summarize_file', return_value="summary"):
            result = mapper._process_file(tmp_path / "test.py", None)

        assert isinstance(result, FileContext)
        assert result.summary == "summary"


class TestScanGenerator:
    """Tests for scan() as a generator."""

    def test_scan_returns_generator(self, tmp_path: Path) -> None:
        """Scan should return a generator."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        result = mapper.scan()

        import types
        assert isinstance(result, types.GeneratorType)

    def test_scan_yields_taskresult(self, tmp_path: Path) -> None:
        """Scan should yield TaskResult objects."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "main.py").write_text("x = 1")

        with patch.object(mapper._summarizer, 'summarize_file', return_value="file summary"):
            with patch.object(mapper._summarizer, 'summarize_module', return_value="module summary"):
                with patch.object(mapper._summarizer, 'summarize_project', return_value="root summary"):
                    with patch.object(mapper._summarizer, 'generate_project_context', return_value="project context"):
                        results = list(mapper.scan())

        assert len(results) >= 1
        for r in results:
            assert isinstance(r.result, ProjectMapperResult)

    def test_scan_progress_increases(self, tmp_path: Path) -> None:
        """Progress should increase across TaskResult yields."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "main.py").write_text("x = 1")

        with patch.object(mapper._summarizer, 'summarize_file', return_value="file summary"):
            with patch.object(mapper._summarizer, 'summarize_module', return_value="module summary"):
                with patch.object(mapper._summarizer, 'summarize_project', return_value="root summary"):
                    with patch.object(mapper._summarizer, 'generate_project_context', return_value="project context"):
                        results = list(mapper.scan())

        progresses = [r.progress for r in results]
        for i in range(1, len(progresses)):
            assert progresses[i] >= progresses[i - 1]

    def test_scan_final_result_has_contexts(self, tmp_path: Path) -> None:
        """Final TaskResult should contain code_context and project_context."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "main.py").write_text("x = 1")

        with patch.object(mapper._summarizer, 'summarize_file', return_value="file summary"):
            with patch.object(mapper._summarizer, 'summarize_module', return_value="module summary"):
                with patch.object(mapper._summarizer, 'summarize_project', return_value="root summary"):
                    with patch.object(mapper._summarizer, 'generate_project_context', return_value="project context"):
                        results = list(mapper.scan())

        final_result = results[-1]
        assert isinstance(final_result.result.code_context, CodeContext)
        assert isinstance(final_result.result.project_context, str)


class TestUpdateGenerator:
    """Tests for update() as a generator."""

    def test_update_returns_generator(self, tmp_path: Path) -> None:
        """Update should return a generator."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        result = mapper.update([tmp_path / "main.py"])

        import types
        assert isinstance(result, types.GeneratorType)

    def test_update_yields_taskresult(self, tmp_path: Path) -> None:
        """Update should yield TaskResult objects."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "main.py").write_text("x = 1")

        with patch.object(mapper._summarizer, 'summarize_file', return_value="file summary"):
            with patch.object(mapper._summarizer, 'summarize_module', return_value="module summary"):
                with patch.object(mapper._summarizer, 'summarize_project', return_value="root summary"):
                    with patch.object(mapper._summarizer, 'generate_project_context', return_value="project context"):
                        results = list(mapper.update([tmp_path / "main.py"]))

        assert len(results) >= 1
        for r in results:
            assert isinstance(r.result, ProjectMapperResult)
