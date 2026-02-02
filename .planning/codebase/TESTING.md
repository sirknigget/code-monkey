# Testing

**Analysis Date:** 2026-02-02

## Framework

**Primary:** pytest

**Async Support:** pytest-asyncio

## Test Structure

**Location:** `tests/` directory mirroring source structure

```
tests/
├── conftest.py                          # Shared fixtures
├── testing_utils.py                     # Test utilities
└── agents/
    ├── project_librarian/
    │   ├── test_project_mapper.py       # ProjectMapper unit tests
    │   ├── test_directory_processor.py  # DirectoryProcessor tests
    │   ├── test_cache_manager.py        # CacheManager tests
    │   ├── test_summarizer.py           # Summarizer tests
    │   ├── test_project_mapper_integration.py
    │   ├── test_project_mapper_real_llm.py
    │   ├── utils/
    │   │   ├── test_code_parser.py
    │   │   ├── test_file_discovery.py
    │   │   ├── test_hash_utils.py
    │   │   └── test_utilities_integration.py
    └── web_researcher/
        ├── test_web_researcher.py
        ├── test_google_search.py
        └── test_playwright_tools.py
```

## Key Fixtures

**conftest.py:**

| Fixture | Purpose |
|---------|---------|
| `mock_llm` | MagicMock LLM for unit tests |
| `template_project(tmp_path)` | Creates isolated copy of `mock_project/template` |

**Pattern:** Template-based testing with isolated working copies

## Mocking Strategy

**LLM Mocking:**
- Use `unittest.mock.MagicMock()` for LangChain model instances
- Patch summarizer methods to return mock summaries

**File System:**
- Use `pytest.TempPathFactory` (tmp_path fixture)
- Template projects copied to isolated temp directories

## Test Categories

**Unit Tests:**
- Located alongside source files (e.g., `test_project_mapper.py`)
- Mock all external dependencies (LLM, file system)
- Fast execution, no network calls

**Integration Tests:**
- `test_*_integration.py` suffix
- Test component interactions
- May use real LLM or mock file operations

**Real LLM Tests:**
- `test_project_mapper_real_llm.py`
- Uses actual API calls (requires API keys)
- Slower, for validation rather than CI

## Test Patterns

**Generator Testing:**

```python
def test_scan_yields_taskresult(self, tmp_path: Path) -> None:
    """Scan should yield TaskResult objects."""
    mock_llm = MagicMock()
    mapper = ProjectMapper(root=tmp_path, llm=mock_llm)
    (tmp_path / "main.py").write_text("x = 1")

    results = list(mapper.scan())

    assert len(results) >= 1
    for r in results:
        assert isinstance(r, TaskResult)
```

**Patch-Based Mocking:**

```python
with patch.object(mapper._summarizer, 'summarize_file', return_value="mock"):
    with patch.object(mapper._summarizer, 'summarize_module', return_value="module"):
        results = list(mapper.scan())
```

**Progress Tracking Verification:**

```python
progresses = [r.progress for r in results]
for i in range(1, len(progresses)):
    assert progresses[i] >= progresses[i - 1]  # Monotonic increase
```

## Coverage

**Areas with good coverage:**
- ProjectMapper (multiple test files)
- DirectoryProcessor
- CacheManager
- Summarizer
- Utility functions (code_parser, file_discovery, hash_utils)

**Areas needing coverage:**
- `main.py` entry point
- `models.py` model factory functions
- `utils/` shared utilities (task_result, json_utils, langchain_utils)

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=code_monkey

# Run specific test file
uv run pytest tests/agents/project_librarian/test_project_mapper.py

# Run integration tests
uv run pytest tests/agents/project_librarian/test_project_mapper_integration.py

# Skip real LLM tests
uv run pytest --ignore=tests/agents/project_librarian/test_project_mapper_real_llm.py
```

## pytest Configuration

**From pyproject.toml:**

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
asyncio_mode = "auto"
```

---

*Testing analysis: 2026-02-02*
