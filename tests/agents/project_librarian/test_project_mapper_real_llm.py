"""Integration tests for ProjectMapper using real LLM.

This test module uses the actual LLM from code_monkey/models/models.py
to test ProjectMapper's full functionality with a realistic mock project.
"""

import json
import shutil
from pathlib import Path

import pytest

from code_monkey.agents.project_librarian.project_mapper import ProjectMapper
from code_monkey.models.models import get_minimax_model
from tests.testing_utils import print_progress_bar


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
        print("[TEST] Starting test_real_llm_fresh_scan")
        print(f"[TEST] Working copy: {mock_project_working_copy}")

        llm = get_minimax_model()
        mapper = ProjectMapper(root=mock_project_working_copy, llm=llm)

        # Run full scan with progress bar
        print("[TEST] Running full scan with real LLM...")
        print("[PROGRESS]")
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
        print(f"[TEST] Scan completed. Found {len(module_summaries)} module summaries")

        # Verify .codemonkey cache was created
        cache_path = mock_project_working_copy / ".codemonkey"
        assert cache_path.exists()
        print(f"[TEST] Cache directory created: {cache_path}")

        # Verify file_hashes.json cache exists
        file_hashes_path = cache_path / "file_hashes.json"
        assert file_hashes_path.exists()

        # Verify hashes file contains data
        with open(file_hashes_path) as f:
            hashes = json.load(f)
            assert len(hashes) > 0
            print(f"[TEST] File hashes cached: {len(hashes)} files")

        # Verify project_context.json exists
        project_context_path = cache_path / "project_context.json"
        assert project_context_path.exists()

        # Verify project context contains meaningful content
        with open(project_context_path) as f:
            context_data = json.load(f)
            # Context is stored as {"context": "..."} so check the context value
            assert "context" in context_data
            assert len(context_data["context"]) > 10  # Should have some description
            print(f"[TEST] Project context generated: {len(context_data['context'])} characters")

        # Verify module summary files exist
        module_summary_files = list(cache_path.rglob("_module.md"))
        assert len(module_summary_files) > 0
        print(f"[TEST] Module summary files: {len(module_summary_files)}")
        print("[TEST] test_real_llm_fresh_scan PASSED")

    def test_real_llm_incremental_update(self, mock_project_working_copy: Path):
        """Test incremental update behavior with real LLM."""
        print("[TEST] Starting test_real_llm_incremental_update")
        print(f"[TEST] Working copy: {mock_project_working_copy}")

        llm = get_minimax_model()
        mapper = ProjectMapper(root=mock_project_working_copy, llm=llm)

        # First scan with progress bar
        print("[TEST] Running initial scan...")
        print("[PROGRESS]")
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
        print(f"[TEST] Initial scan complete: {len(result1)} modules")

        # Modify a file in the mock project
        test_file = mock_project_working_copy / "src" / "crewai_trading_strategy" / "__init__.py"
        original_content = test_file.read_text()
        print(f"[TEST] Modifying file: {test_file}")

        # Add a comment to trigger change detection
        modified_content = original_content + "\n# Modified for testing incremental update\n"
        test_file.write_text(modified_content)

        try:
            # Second scan should detect the change and return module summaries
            print("[TEST] Running incremental scan after file modification...")
            print("[PROGRESS]")
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
            print(f"[TEST] Incremental scan complete: {len(result2)} modules")
            print("[TEST] test_real_llm_incremental_update PASSED")
        finally:
            # Restore original content
            test_file.write_text(original_content)
            print("[TEST] Restored original file content")

    def test_real_llm_specified_file_update(self, mock_project_working_copy: Path):
        """Test update with specific file paths using real LLM."""
        print("[TEST] Starting test_real_llm_specified_file_update")
        print(f"[TEST] Working copy: {mock_project_working_copy}")

        llm = get_minimax_model()
        mapper = ProjectMapper(root=mock_project_working_copy, llm=llm)

        # Initial scan
        print("[TEST] Running initial scan...")
        print("[PROGRESS]")
        for task_result in mapper.scan():
            print_progress_bar(
                task_result.progress,
                task_result.progress_max,
                prefix="[SCAN]",
            )
        print("[TEST] Initial scan complete")

        # Specify specific files to update
        files_to_update = [
            mock_project_working_copy / "src" / "utils" / "safe_python_code_executor.py",
            mock_project_working_copy / "src" / "crewai_trading_strategy" / "constants.py",
        ]
        print(f"[TEST] Files to update: {len(files_to_update)}")

        # Run update with specific files - returns dict[Path, str] of module summaries
        print("[TEST] Running update for specified files...")
        print("[PROGRESS]")
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
        print(f"[TEST] Update complete: {len(result)} modules processed")
        print("[TEST] test_real_llm_specified_file_update PASSED")

    def test_real_llm_generates_module_summaries(self, mock_project_working_copy: Path):
        """Test that module summaries are generated in the cache."""
        print("[TEST] Starting test_real_llm_generates_module_summaries")
        print(f"[TEST] Working copy: {mock_project_working_copy}")

        llm = get_minimax_model()
        mapper = ProjectMapper(root=mock_project_working_copy, llm=llm)

        # Run scan
        print("[TEST] Running scan...")
        print("[PROGRESS]")
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
        print(f"[TEST] Found {len(module_summary_files)} module summary files")

        # Each summary should contain meaningful content
        for summary_file in module_summary_files[:3]:  # Check first 3
            with open(summary_file) as f:
                content = f.read()
                assert len(content) > 10  # Should have some LLM-generated content
        print("[TEST] Verified content in first 3 module summaries")
        print("[TEST] test_real_llm_generates_module_summaries PASSED")

    def test_real_llm_cache_survives_reload(self, mock_project_working_copy: Path):
        """Test that cached data can be reloaded correctly."""
        print("[TEST] Starting test_real_llm_cache_survives_reload")
        print(f"[TEST] Working copy: {mock_project_working_copy}")

        llm = get_minimax_model()
        mapper = ProjectMapper(root=mock_project_working_copy, llm=llm)

        # Initial scan
        print("[TEST] Running initial scan...")
        print("[PROGRESS]")
        for task_result in mapper.scan():
            print_progress_bar(
                task_result.progress,
                task_result.progress_max,
                prefix="[SCAN]",
            )

        # Create new mapper instance (simulates restart)
        print("[TEST] Creating new mapper instance (simulating restart)...")
        mapper2 = ProjectMapper(root=mock_project_working_copy, llm=llm)

        # Should be able to load existing hashes
        print("[TEST] Loading cached file hashes...")
        loaded_hashes = mapper2._cache.load_hashes()
        assert loaded_hashes is not None
        assert len(loaded_hashes) > 0
        print(f"[TEST] Loaded {len(loaded_hashes)} cached file hashes")

        # Should be able to load project context
        print("[TEST] Loading cached project context...")
        context = mapper2._cache.load_project_context()
        assert context is not None
        assert len(context) > 0
        print(f"[TEST] Loaded project context: {len(context)} characters")
        print("[TEST] test_real_llm_cache_survives_reload PASSED")


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
        print("[TEST] Starting test_handles_new_subdirectory")
        print(f"[TEST] Working copy: {mock_project_working_copy}")

        llm = get_minimax_model()
        mapper = ProjectMapper(root=mock_project_working_copy, llm=llm)

        # Initial scan
        print("[TEST] Running initial scan...")
        print("[PROGRESS]")
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
        print(f"[TEST] Created new directory: {new_dir}")
        print(f"[TEST] Added 2 new files in {new_dir}")

        try:
            # Scan again - should discover new files
            print("[TEST] Running re-scan to discover new files...")
            print("[PROGRESS]")
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
            print(f"[TEST] Re-scan complete: {len(result)} modules")
            print("[TEST] test_handles_new_subdirectory PASSED")
        finally:
            # Clean up
            shutil.rmtree(new_dir)
            print("[TEST] Cleaned up new directory")

    def test_cache_contains_file_summaries(self, mock_project_working_copy: Path):
        """Verify individual file summaries are cached."""
        print("[TEST] Starting test_cache_contains_file_summaries")
        print(f"[TEST] Working copy: {mock_project_working_copy}")

        llm = get_minimax_model()
        mapper = ProjectMapper(root=mock_project_working_copy, llm=llm)

        # Run scan
        print("[TEST] Running scan...")
        print("[PROGRESS]")
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
        print(f"[TEST] Found {len(md_files)} .md files in cache")

        # Check that at least some files have meaningful content
        non_module_files = [f for f in md_files if f.name != "_module.md"]
        if non_module_files:
            for summary_file in non_module_files[:3]:
                with open(summary_file) as f:
                    content = f.read()
                    # Should have LLM-generated content
                    assert len(content) > 10
            print(f"[TEST] Verified content in {min(3, len(non_module_files))} file summaries")
        else:
            print("[TEST] No non-module .md files found")
        print("[TEST] test_cache_contains_file_summaries PASSED")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
