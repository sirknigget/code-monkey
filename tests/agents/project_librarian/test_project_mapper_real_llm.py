"""Integration tests for ProjectMapper using real LLM.

This test module uses the actual LLM from code_monkey/models/models.py
to test ProjectMapper's full functionality with a realistic mock project.
"""

import logging
import json
import shutil
from pathlib import Path

import pytest

from code_monkey.agents.project_librarian.project_mapper import ProjectMapper
from code_monkey.models.models import get_minimax_model
from tests.testing_utils import print_progress_bar

logger = logging.getLogger(__name__)


class TestProjectMapperRealLLM:
    """Integration tests using real LLM and realistic mock project."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, mock_project_working_copy: Path):
        """Clean up .codemonkey cache before and after each test."""
        cache_path = mock_project_working_copy / ".codemonkey"
        if cache_path.exists():
            shutil.rmtree(cache_path)
        yield
        if cache_path.exists():
            shutil.rmtree(cache_path)

    def test_real_llm_fresh_scan(self, mock_project_working_copy: Path):
        """Test full scan with real LLM generates project context."""
        logger.info("[TEST] Starting test_real_llm_fresh_scan")
        logger.info("[TEST] Working copy: %s", mock_project_working_copy)

        llm = get_minimax_model()
        mapper = ProjectMapper(root=mock_project_working_copy, llm=llm)

        # Run full scan with progress bar
        logger.info("[TEST] Running full scan with real LLM...")
        logger.info("[PROGRESS]")
        module_summaries = None
        for task_result in mapper.scan():
            print_progress_bar(
                task_result.progress,
                task_result.progress_max,
                prefix="[SCAN]",
            )
            if task_result.progress == task_result.progress_max:
                module_summaries = task_result.result.module_summaries

        # Verify scan returned results - scan() returns dict[Path, str] of module summaries
        assert module_summaries is not None
        assert len(module_summaries) > 0
        logger.info("[TEST] Scan completed. Found %d module summaries", len(module_summaries))

        # Verify .codemonkey cache was created
        cache_path = mock_project_working_copy / ".codemonkey"
        assert cache_path.exists()
        logger.info("[TEST] Cache directory created: %s", cache_path)

        # Verify file_hashes.json cache exists
        file_hashes_path = cache_path / "file_hashes.json"
        assert file_hashes_path.exists()

        # Verify hashes file contains data
        with open(file_hashes_path) as f:
            hashes = json.load(f)
            assert len(hashes) > 0
            logger.info("[TEST] File hashes cached: %d files", len(hashes))

        # Verify project_context.json exists
        project_context_path = cache_path / "project_context.json"
        assert project_context_path.exists()

        # Verify project context contains meaningful content
        with open(project_context_path) as f:
            context_data = json.load(f)
            # Context is stored as {"context": "..."} so check the context value
            assert "context" in context_data
            assert len(context_data["context"]) > 10  # Should have some description
            logger.info("[TEST] Project context generated: %d characters", len(context_data["context"]))

        # Verify module summary files exist
        module_summary_files = list(cache_path.rglob("_module.md"))
        assert len(module_summary_files) > 0
        logger.info("[TEST] Module summary files: %d", len(module_summary_files))
        logger.info("[TEST] test_real_llm_fresh_scan PASSED")

    def test_real_llm_incremental_update(self, mock_project_working_copy: Path):
        """Test incremental update behavior with real LLM."""
        logger.info("[TEST] Starting test_real_llm_incremental_update")
        logger.info("[TEST] Working copy: %s", mock_project_working_copy)

        llm = get_minimax_model()
        mapper = ProjectMapper(root=mock_project_working_copy, llm=llm)

        # First scan with progress bar
        logger.info("[TEST] Running initial scan...")
        logger.info("[PROGRESS]")
        result1 = None
        for task_result in mapper.scan():
            print_progress_bar(
                task_result.progress,
                task_result.progress_max,
                prefix="[SCAN]",
            )
            if task_result.progress == task_result.progress_max:
                result1 = task_result.result.module_summaries

        assert result1 is not None and len(result1) > 0
        logger.info("[TEST] Initial scan complete: %d modules", len(result1))

        # Modify a file in the mock project
        test_file = mock_project_working_copy / "src" / "crewai_trading_strategy" / "__init__.py"
        original_content = test_file.read_text()
        logger.info("[TEST] Modifying file: %s", test_file)

        # Add a comment to trigger change detection
        modified_content = original_content + "\n# Modified for testing incremental update\n"
        test_file.write_text(modified_content)

        try:
            # Second scan should detect the change and return module summaries
            logger.info("[TEST] Running incremental scan after file modification...")
            logger.info("[PROGRESS]")
            result2 = None
            for task_result in mapper.scan():
                print_progress_bar(
                    task_result.progress,
                    task_result.progress_max,
                    prefix="[SCAN]",
                )
                if task_result.progress == task_result.progress_max:
                    result2 = task_result.result.module_summaries

            assert result2 is not None
            assert len(result2) >= 1  # Should return at least some module summaries
            logger.info("[TEST] Incremental scan complete: %d modules", len(result2))
            logger.info("[TEST] test_real_llm_incremental_update PASSED")
        finally:
            # Restore original content
            test_file.write_text(original_content)
            logger.info("[TEST] Restored original file content")

    def test_real_llm_specified_file_update(self, mock_project_working_copy: Path):
        """Test update with specific file paths using real LLM."""
        logger.info("[TEST] Starting test_real_llm_specified_file_update")
        logger.info("[TEST] Working copy: %s", mock_project_working_copy)

        llm = get_minimax_model()
        mapper = ProjectMapper(root=mock_project_working_copy, llm=llm)

        # Initial scan
        logger.info("[TEST] Running initial scan...")
        logger.info("[PROGRESS]")
        for task_result in mapper.scan():
            print_progress_bar(
                task_result.progress,
                task_result.progress_max,
                prefix="[SCAN]",
            )
        logger.info("[TEST] Initial scan complete")

        # Specify specific files to update
        files_to_update = [
            mock_project_working_copy / "src" / "utils" / "safe_python_code_executor.py",
            mock_project_working_copy / "src" / "crewai_trading_strategy" / "constants.py",
        ]
        logger.info("[TEST] Files to update: %d", len(files_to_update))

        # Run update with specific files - returns dict[Path, str] of module summaries
        logger.info("[TEST] Running update for specified files...")
        logger.info("[PROGRESS]")
        result = None
        for task_result in mapper.update(files_to_update):
            print_progress_bar(
                task_result.progress,
                task_result.progress_max,
                prefix="[UPDATE]",
            )
            if task_result.progress == task_result.progress_max:
                result = task_result.result.module_summaries

        assert result is not None
        assert len(result) >= 1  # Should return module summaries
        logger.info("[TEST] Update complete: %d modules processed", len(result))
        logger.info("[TEST] test_real_llm_specified_file_update PASSED")

    def test_real_llm_generates_module_summaries(self, mock_project_working_copy: Path):
        """Test that module summaries are generated in the cache."""
        logger.info("[TEST] Starting test_real_llm_generates_module_summaries")
        logger.info("[TEST] Working copy: %s", mock_project_working_copy)

        llm = get_minimax_model()
        mapper = ProjectMapper(root=mock_project_working_copy, llm=llm)

        # Run scan
        logger.info("[TEST] Running scan...")
        logger.info("[PROGRESS]")
        for task_result in mapper.scan():
            print_progress_bar(
                task_result.progress,
                task_result.progress_max,
                prefix="[SCAN]",
            )

        # Check that cache directory has module summaries
        cache_path = mock_project_working_copy / ".codemonkey"

        # Should have multiple _module.md files
        module_summary_files = list(cache_path.rglob("_module.md"))
        assert len(module_summary_files) > 3  # At least root, src, tests
        logger.info("[TEST] Found %d module summary files", len(module_summary_files))

        # Each summary should contain meaningful content
        for summary_file in module_summary_files[:3]:  # Check first 3
            with open(summary_file) as f:
                content = f.read()
                assert len(content) > 10  # Should have some LLM-generated content
        logger.info("[TEST] Verified content in first 3 module summaries")
        logger.info("[TEST] test_real_llm_generates_module_summaries PASSED")

    def test_real_llm_cache_survives_reload(self, mock_project_working_copy: Path):
        """Test that cached data can be reloaded correctly."""
        logger.info("[TEST] Starting test_real_llm_cache_survives_reload")
        logger.info("[TEST] Working copy: %s", mock_project_working_copy)

        llm = get_minimax_model()
        mapper = ProjectMapper(root=mock_project_working_copy, llm=llm)

        # Initial scan
        logger.info("[TEST] Running initial scan...")
        logger.info("[PROGRESS]")
        for task_result in mapper.scan():
            print_progress_bar(
                task_result.progress,
                task_result.progress_max,
                prefix="[SCAN]",
            )

        # Create new mapper instance (simulates restart)
        logger.info("[TEST] Creating new mapper instance (simulating restart)...")
        mapper2 = ProjectMapper(root=mock_project_working_copy, llm=llm)

        # Should be able to load existing hashes
        logger.info("[TEST] Loading cached file hashes...")
        loaded_hashes = mapper2._cache.load_hashes()
        assert loaded_hashes is not None
        assert len(loaded_hashes) > 0
        logger.info("[TEST] Loaded %d cached file hashes", len(loaded_hashes))

        # Should be able to load project context
        logger.info("[TEST] Loading cached project context...")
        context = mapper2._cache.load_project_context()
        assert context is not None
        assert len(context) > 0
        logger.info("[TEST] Loaded project context: %d characters", len(context))
        logger.info("[TEST] test_real_llm_cache_survives_reload PASSED")


class TestProjectMapperRealLLMWithModifiedProject:
    """Test ProjectMapper with various modifications to the mock project."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, mock_project_working_copy: Path):
        """Clean up .codemonkey cache before and after each test."""
        cache_path = mock_project_working_copy / ".codemonkey"
        if cache_path.exists():
            shutil.rmtree(cache_path)
        yield
        if cache_path.exists():
            shutil.rmtree(cache_path)

    def test_handles_new_subdirectory(self, mock_project_working_copy: Path):
        """Test that new subdirectories are discovered and processed."""
        logger.info("[TEST] Starting test_handles_new_subdirectory")
        logger.info("[TEST] Working copy: %s", mock_project_working_copy)

        llm = get_minimax_model()
        mapper = ProjectMapper(root=mock_project_working_copy, llm=llm)

        # Initial scan
        logger.info("[TEST] Running initial scan...")
        logger.info("[PROGRESS]")
        for task_result in mapper.scan():
            print_progress_bar(
                task_result.progress,
                task_result.progress_max,
                prefix="[SCAN]",
            )

        # Create a new subdirectory with files
        new_dir = mock_project_working_copy / "src" / "utils" / "new_feature"
        new_dir.mkdir(exist_ok=True)
        (new_dir / "__init__.py").write_text('"""New feature module."""\n')
        (new_dir / "handler.py").write_text('def handle(): pass\n')
        logger.info("[TEST] Created new directory: %s", new_dir)
        logger.info("[TEST] Added 2 new files in %s", new_dir)

        try:
            # Scan again - should discover new files
            logger.info("[TEST] Running re-scan to discover new files...")
            logger.info("[PROGRESS]")
            result = None
            for task_result in mapper.scan():
                print_progress_bar(
                    task_result.progress,
                    task_result.progress_max,
                    prefix="[SCAN]",
                )
                if task_result.progress == task_result.progress_max:
                    result = task_result.result.module_summaries

            # New files should be processed - returns module summaries dict
            assert result is not None and len(result) >= 1
            logger.info("[TEST] Re-scan complete: %d modules", len(result))
            logger.info("[TEST] test_handles_new_subdirectory PASSED")
        finally:
            # Clean up
            shutil.rmtree(new_dir)
            logger.info("[TEST] Cleaned up new directory")

    def test_cache_contains_file_summaries(self, mock_project_working_copy: Path):
        """Verify individual file summaries are cached."""
        logger.info("[TEST] Starting test_cache_contains_file_summaries")
        logger.info("[TEST] Working copy: %s", mock_project_working_copy)

        llm = get_minimax_model()
        mapper = ProjectMapper(root=mock_project_working_copy, llm=llm)

        # Run scan
        logger.info("[TEST] Running scan...")
        logger.info("[PROGRESS]")
        for task_result in mapper.scan():
            print_progress_bar(
                task_result.progress,
                task_result.progress_max,
                prefix="[SCAN]",
            )

        # Check for file-specific summaries in cache
        cache_path = mock_project_working_copy / ".codemonkey"

        # Look for any .md files in the cache (these are file/module summaries)
        md_files = list(cache_path.rglob("*.md"))
        assert len(md_files) > 0
        logger.info("[TEST] Found %d .md files in cache", len(md_files))

        # Check that at least some files have meaningful content
        non_module_files = [f for f in md_files if f.name != "_module.md"]
        if non_module_files:
            for summary_file in non_module_files[:3]:
                with open(summary_file) as f:
                    content = f.read()
                    # Should have LLM-generated content
                    assert len(content) > 10
            logger.info("[TEST] Verified content in %d file summaries", min(3, len(non_module_files)))
        else:
            logger.info("[TEST] No non-module .md files found")
        logger.info("[TEST] test_cache_contains_file_summaries PASSED")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
