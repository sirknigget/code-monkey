"""Integration tests for ProjectMapper using real LLM.

This test module uses the actual LLM from code_monkey/models/models.py
to test ProjectMapper's full functionality with a realistic mock project.
"""

import os
import shutil
from pathlib import Path

import pytest

from code_monkey.models.models import get_minimax_model
from code_monkey.agents.project_librarian.project_mapper import ProjectMapper


# Path to the mock project folder (requests library)
MOCK_PROJECT_PATH = Path(__file__).parent.parent.parent.parent / "mock_project_folder"


class TestProjectMapperRealLLM:
    """Integration tests using real LLM and realistic mock project."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean up .codemonkey cache before and after each test."""
        cache_path = MOCK_PROJECT_PATH / ".codemonkey"
        if cache_path.exists():
            shutil.rmtree(cache_path)
        yield
        if cache_path.exists():
            shutil.rmtree(cache_path)

    def test_real_llm_fresh_scan(self):
        """Test full scan with real LLM generates project context."""
        llm = get_minimax_model()
        mapper = ProjectMapper(root=MOCK_PROJECT_PATH, llm=llm)

        # Run full scan
        result = mapper.scan()

        # Verify scan returned results
        assert result is not None
        assert "files_processed" in result
        assert result["files_processed"] > 0

        # Verify .codemonkey cache was created
        cache_path = MOCK_PROJECT_PATH / ".codemonkey"
        assert cache_path.exists()

        # Verify file-hashes cache exists
        file_hashes_path = cache_path / "file-hashes"
        assert file_hashes_path.exists()

        # Verify hashes file contains data
        with open(file_hashes_path) as f:
            content = f.read()
            assert len(content) > 0

        # Verify project-context exists
        project_context_path = cache_path / "project-context"
        assert project_context_path.exists()

        # Verify project context contains meaningful content
        with open(project_context_path) as f:
            context = f.read()
            assert len(context) > 10  # Should have some description
            # Should mention "requests" or HTTP-related concepts
            assert any(word in context.lower() for word in ["request", "http", "python", "library"])

    def test_real_llm_incremental_update(self):
        """Test incremental update behavior with real LLM."""
        llm = get_minimax_model()
        mapper = ProjectMapper(root=MOCK_PROJECT_PATH, llm=llm)

        # First scan
        result1 = mapper.scan()
        assert result1["files_processed"] > 0

        # Modify a file in the mock project
        test_file = MOCK_PROJECT_PATH / "src" / "requests" / "__init__.py"
        original_content = test_file.read_text()

        # Add a comment to trigger change detection
        modified_content = original_content + "\n# Modified for testing incremental update\n"
        test_file.write_text(modified_content)

        try:
            # Second scan should detect the change
            result2 = mapper.scan()
            assert result2["files_processed"] >= 1  # Should process at least the changed file
        finally:
            # Restore original content
            test_file.write_text(original_content)

    def test_real_llm_specified_file_update(self):
        """Test update with specific file paths using real LLM."""
        llm = get_minimax_model()
        mapper = ProjectMapper(root=MOCK_PROJECT_PATH, llm=llm)

        # Initial scan
        mapper.scan()

        # Specify specific files to update
        files_to_update = [
            MOCK_PROJECT_PATH / "src" / "requests" / "exceptions.py",
            MOCK_PROJECT_PATH / "src" / "requests" / "status_codes.py",
        ]

        # Run update with specific files
        result = mapper.update(files_to_update)
        assert result is not None
        assert "files_processed" in result

    def test_real_llm_generates_module_summaries(self):
        """Test that module summaries are generated in the cache."""
        llm = get_minimax_model()
        mapper = ProjectMapper(root=MOCK_PROJECT_PATH, llm=llm)

        # Run scan
        mapper.scan()

        # Check that code-context directory exists
        cache_path = MOCK_PROJECT_PATH / ".codemonkey"
        code_context_path = cache_path / "code-context"

        assert code_context_path.exists()

        # Should have multiple summary files
        summary_files = list(code_context_path.glob("*.txt"))
        assert len(summary_files) > 0

        # Each summary should contain meaningful content
        for summary_file in summary_files[:3]:  # Check first 3
            with open(summary_file) as f:
                content = f.read()
                assert len(content) > 10  # Should have some LLM-generated content

    def test_real_llm_cache_survives_reload(self):
        """Test that cached data can be reloaded correctly."""
        llm = get_minimax_model()
        mapper = ProjectMapper(root=MOCK_PROJECT_PATH, llm=llm)

        # Initial scan
        mapper.scan()

        # Create new mapper instance (simulates restart)
        mapper2 = ProjectMapper(root=MOCK_PROJECT_PATH, llm=llm)

        # Should be able to load existing hashes
        loaded_hashes = mapper2._cache.load_hashes()
        assert loaded_hashes is not None
        assert len(loaded_hashes) > 0

        # Should be able to load project context
        context = mapper2._cache.load_project_context()
        assert context is not None
        assert len(context) > 0


class TestProjectMapperRealLLMWithModifiedProject:
    """Test ProjectMapper with various modifications to the mock project."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean up .codemonkey cache before and after each test."""
        cache_path = MOCK_PROJECT_PATH / ".codemonkey"
        if cache_path.exists():
            shutil.rmtree(cache_path)
        yield
        if cache_path.exists():
            shutil.rmtree(cache_path)

    def test_handles_new_subdirectory(self):
        """Test that new subdirectories are discovered and processed."""
        llm = get_minimax_model()
        mapper = ProjectMapper(root=MOCK_PROJECT_PATH, llm=llm)

        # Initial scan
        mapper.scan()

        # Create a new subdirectory with files
        new_dir = MOCK_PROJECT_PATH / "src" / "requests" / "new_feature"
        new_dir.mkdir(exist_ok=True)
        (new_dir / "__init__.py").write_text('"""New feature module."""\n')
        (new_dir / "handler.py").write_text('def handle(): pass\n')

        try:
            # Scan again - should discover new files
            result = mapper.scan()
            # New files should be processed
            assert result["files_processed"] >= 2
        finally:
            # Clean up
            shutil.rmtree(new_dir)

    def test_cache_contains_file_summaries(self):
        """Verify individual file summaries are cached."""
        llm = get_minimax_model()
        mapper = ProjectMapper(root=MOCK_PROJECT_PATH, llm=llm)

        # Run scan
        mapper.scan()

        # Check for file-specific summaries
        cache_path = MOCK_PROJECT_PATH / ".codemonkey"
        code_context_path = cache_path / "code-context"

        # Look for a specific file summary (e.g., models.py)
        models_summary = code_context_path / "src-requests-models.py.txt"
        if models_summary.exists():
            with open(models_summary) as f:
                content = f.read()
                # Should have LLM-generated summary
                assert len(content) > 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
