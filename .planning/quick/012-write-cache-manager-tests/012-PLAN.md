# Quick 012: Write Cache Manager Tests

**Task:** Write tests for `cache_manager.py` and run to verify.

## Test Coverage Requirements

### FileContext & ModuleContext Models
- Test `FileContext` dataclass initialization
- Test `ModuleContext` dataclass with files and submodules
- Test `module_context_from_dict` recursive loading

### CacheManager Core
- Test `load_hashes()` returns empty dict when no cache
- Test `save_hashes()` and `load_hashes()` roundtrip
- Test `load_code_context()` returns None when no cache
- Test `save_code_context()` and `load_code_context()` roundtrip
- Test `save_project_context()` and `load_project_context()` roundtrip
- Test atomic write pattern (temp file + rename)
- Test error handling for corrupted files

## Tasks

1. **Write test file** (`tests/agents/project_librarian/test_cache_manager.py`)
   - Use pytest fixtures for temp directory
   - Test all CacheManager methods
   - Cover edge cases (missing files, corrupted JSON)

2. **Run tests and verify**
   - Execute `uv run pytest tests/agents/project_librarian/test_cache_manager.py`
   - All tests should pass
