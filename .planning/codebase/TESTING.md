# Testing Patterns

**Analysis Date:** 2026-01-31

## Test Framework

**Runner:**
- `pytest` >= 8.0.0
- `pytest-asyncio` >= 1.3.0 for async tests
- Config: `pythonpath = ["."]` in `pyproject.toml`

**Assertion Library:**
- pytest built-in assertions (assert statements)

**Run Commands:**
```bash
uv run pytest              # Run all tests
uv run pytest -v           # Verbose output
uv run pytest --tb=short   # Shorter traceback
```

## Test File Organization

**Location:**
- Separate `tests/` directory mirroring source structure
- Co-located by agent: `tests/agents/project_librarian/`, `tests/agents/web_researcher/`

**Naming:**
- `test_*.py` pattern: `test_file_discovery.py`, `test_hash_utils.py`
- Test classes: `TestDiscoverPythonFiles`, `TestComputeFileHash`

**Structure:**
```
tests/
├── agents/
│   ├── project_librarian/
│   │   ├── test_file_discovery.py
│   │   ├── test_hash_utils.py
│   │   ├── test_code_parser.py
│   │   └── test_utilities_integration.py
│   └── web_researcher/
│       ├── test_google_search.py
│       ├── test_playwright_tools.py
│       └── test_web_researcher.py
```

## Test Structure

**Suite Organization:**
- Test classes grouping related tests: `class TestDiscoverPythonFiles:`
- Each test method has descriptive name: `test_discovers_python_files_at_root_and_nested`
- Each test has docstring explaining what is verified

**Patterns:**
```python
class TestDiscoverPythonFiles:
    """Test suite for discover_python_files function."""

    def test_discovers_python_files_at_root_and_nested(
        self, tmp_path: Path
    ) -> None:
        """Verify Python files at root and nested levels are discovered."""
        # Create test structure
        (tmp_path / "root_file.py").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested_file.py").touch()

        # Discover files
        result = discover_python_files(tmp_path)

        # Verify both files found
        assert len(result) == 2
        assert (tmp_path / "root_file.py") in result
        assert (tmp_path / "subdir" / "nested_file.py") in result
```

**Setup Pattern:**
- Uses pytest fixtures: `tmp_path`, `tmpdir`, `tmp_path`
- Tempfile for file operations
- No explicit setup/teardown methods needed for simple tests

**Teardown Pattern:**
- Explicit cleanup in `try/finally`:
```python
try:
    result = compute_file_hash(temp_path)
    assert result == expected_hash
finally:
    Path(temp_path).unlink()
```

## Mocking

**Framework:** Not configured

**Patterns:**
- No mocking framework (unittest.mock) detected
- Tests use real file system operations
- Tests create actual temporary files for testing
- Tests use real API calls (with `.env` loading)

**What is Mocked:**
- Nothing mocked in current tests
- All I/O operations are real

**What NOT to Mock:**
- File operations use real temp files
- API calls use real services (with env vars)

## Fixtures and Factories

**Test Data:**
- Created inline in test methods
- Used `tempfile.NamedTemporaryFile` for file content
- Used `textwrap.dedent` for multi-line test strings:
```python
file1.write_text(
    textwrap.dedent(
        """
        class DataProcessor:
            def process(self, data):
                return data.upper()
        """
    )
)
```

**Location:**
- No dedicated fixtures file
- Fixtures defined in `conftest.py` (not present, using pytest defaults)

## Coverage

**Requirements:** None enforced

**View Coverage:**
```bash
uv run pytest --cov=code_monkey --cov-report=term-missing
```

## Test Types

**Unit Tests:**
- Focus on single functions/classes
- Test hash_utils: 8 test cases
- Test code_parser: 5 test classes, 17+ test cases
- Test file_discovery: 6 test cases

**Integration Tests:**
- `test_utilities_integration.py` tests full workflow
- Tests discovery + hashing + parsing together
- Tests module imports and API cohesion

**E2E Tests:**
- `test_google_search.py`: Real Google search API call
- `test_playwright_tools.py`: Real browser automation tests
- Uses `@pytest.mark.asyncio` for async tests

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
async def test_playwright_tools_initialize():
    """Test PlaywrightTools initialization."""
    pt = await PlaywrightTools.initialize(headless=True)
    assert pt._playwright is not None
    await pt.teardown()
```

**Error Testing:**
```python
def test_raises_on_nonexistent_file():
    """OSError is raised when file does not exist."""
    nonexistent_path = "/tmp/this_file_does_not_exist_123456789.xyz"
    assert not Path(nonexistent_path).exists()

    with pytest.raises(OSError):
        compute_file_hash(nonexistent_path)
```

**Path Handling:**
```python
def test_discovers_python_files_at_root_and_nested(
    self, tmp_path: Path
) -> None:
    """Verify Python files at root and nested levels are discovered."""
    (tmp_path / "root_file.py").touch()
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "nested_file.py").touch()
    result = discover_python_files(tmp_path)
```

**Environment Loading:**
```python
from dotenv import load_dotenv
load_dotenv(override=True)
```

---

*Testing analysis: 2026-01-31*
