"""Integration tests for ProjectMapper using real LLM.

This test module uses the actual LLM from code_monkey/models/models.py
to test ProjectMapper's full functionality with a realistic mock project.
"""

import json
import shutil
from pathlib import Path

import pytest

from code_monkey.models.models import get_minimax_model
from code_monkey.agents.project_librarian.project_mapper import ProjectMapper


# Path to the mock project folder
@pytest.fixture(scope="session")
def mock_project_dir(pytestconfig) -> Path:
    return pytestconfig.rootpath / "mock_project"

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
        module_summaries = mapper.scan()

        # Verify scan returned results - scan() returns dict[Path, str] of module summaries
        assert module_summaries is not None
        assert len(module_summaries) > 0

        # Verify .codemonkey cache was created
        cache_path = MOCK_PROJECT_PATH / ".codemonkey"
        assert cache_path.exists()

        # Verify file_hashes.json cache exists
        file_hashes_path = cache_path / "file_hashes.json"
        assert file_hashes_path.exists()

        # Verify hashes file contains data
        with open(file_hashes_path) as f:
            hashes = json.load(f)
            assert len(hashes) > 0

        # Verify project_context.json exists
        project_context_path = cache_path / "project_context.json"
        assert project_context_path.exists()

        # Verify project context contains meaningful content
        with open(project_context_path) as f:
            context_data = json.load(f)
            # Context is stored as {"context": "..."} so check the context value
            assert "context" in context_data
            assert len(context_data["context"]) > 10  # Should have some description

        # Verify module summary files exist
        module_summary_files = list(cache_path.rglob("_module.md"))
        assert len(module_summary_files) > 0

    def test_real_llm_incremental_update(self):
        """Test incremental update behavior with real LLM."""
        llm = get_minimax_model()
        mapper = ProjectMapper(root=MOCK_PROJECT_PATH, llm=llm)

        # First scan
        result1 = mapper.scan()
        assert len(result1) > 0

        # Modify a file in the mock project
        test_file = MOCK_PROJECT_PATH / "src" / "requests" / "__init__.py"
        original_content = test_file.read_text()

        # Add a comment to trigger change detection
        modified_content = original_content + "\n# Modified for testing incremental update\n"
        test_file.write_text(modified_content)

        try:
            # Second scan should detect the change and return module summaries
            result2 = mapper.scan()
            assert result2 is not None
            assert len(result2) >= 1  # Should return at least some module summaries
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

        # Run update with specific files - returns dict[Path, str] of module summaries
        result = mapper.update(files_to_update)
        assert result is not None
        assert len(result) >= 1  # Should return module summaries

    def test_real_llm_generates_module_summaries(self):
        """Test that module summaries are generated in the cache."""
        llm = get_minimax_model()
        mapper = ProjectMapper(root=MOCK_PROJECT_PATH, llm=llm)

        # Run scan
        mapper.scan()

        # Check that cache directory has module summaries
        cache_path = MOCK_PROJECT_PATH / ".codemonkey"

        # Should have multiple _module.md files
        module_summary_files = list(cache_path.rglob("_module.md"))
        assert len(module_summary_files) > 3  # At least root, src, tests

        # Each summary should contain meaningful content
        for summary_file in module_summary_files[:3]:  # Check first 3
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
            # New files should be processed - returns module summaries dict
            assert len(result) >= 1
        finally:
            # Clean up
            shutil.rmtree(new_dir)

    def test_cache_contains_file_summaries(self):
        """Verify individual file summaries are cached."""
        llm = get_minimax_model()
        mapper = ProjectMapper(root=MOCK_PROJECT_PATH, llm=llm)

        # Run scan
        mapper.scan()

        # Check for file-specific summaries in cache
        cache_path = MOCK_PROJECT_PATH / ".codemonkey"

        # Look for any .md files in the cache (these are file/module summaries)
        md_files = list(cache_path.rglob("*.md"))
        assert len(md_files) > 0

        # Check that at least some files have meaningful content
        non_module_files = [f for f in md_files if f.name != "_module.md"]
        if non_module_files:
            for summary_file in non_module_files[:3]:
                with open(summary_file) as f:
                    content = f.read()
                    # Should have LLM-generated content
                    assert len(content) > 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
