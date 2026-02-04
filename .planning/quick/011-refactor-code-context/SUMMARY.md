# Quick Task 011: Refactor code context for unified JSON structure

## Summary

Successfully refactored `cache_manager.py` and `project_mapper.py` to use a unified code context structure stored as a single JSON file.

## Changes Made

### 1. cache_manager.py

**Added data classes:**
- `FileContext(summary: str)` - A file in the code hierarchy
- `ModuleContext(summary: str, files: dict, submodules: dict)` - A module with files and child modules
- `CodeContext(root_summary: str, modules: dict)` - Root context containing modules hierarchy

**Added methods:**
- `save_code_context(ctx: CodeContext)` - Atomically save code context
- `load_code_context() -> CodeContext | None` - Load code context from cache

**Removed:**
- `save_file_summary()`/`load_file_summary()` - Replaced by unified context
- `save_module_summary()`/`load_module_summary()` - Replaced by unified context

**Updated filenames:**
- `file_hashes.json` - unchanged
- `code_context.json` (was individual .md files) - new unified file
- `project_context.json` - unchanged

### 2. project_mapper.py

**Updated flow:**
1. Loads `CodeContext` from cache at start
2. Computes hashes, finds changed files
3. Only processes changed directories
4. Updates module summaries when files change
5. Regenerates root summary when changes occur
6. Saves complete `CodeContext` to cache

**New result type:**
- `ProjectMapperResult` now contains `code_context: CodeContext` and `project_context: str`

### 3. summarizer.py

**Added:**
- `summarize_project(code_context: CodeContext, project_name: str) -> str`
- Support for `CodeContext` in `generate_project_context()`

## Files Modified

| File | Changes |
|------|---------|
| `code_monkey/agents/project_librarian/cache_manager.py` | Added data structures, unified JSON |
| `code_monkey/agents/project_librarian/project_mapper.py` | Updated to use CodeContext |
| `code_monkey/agents/project_librarian/summarizer.py` | Added CodeContext support |

## Files Created

| File | Description |
|------|-------------|
| `tests/agents/project_librarian/test_cache_manager.py` | Tests for cache manager and data structures |
| `tests/agents/project_librarian/test_project_mapper.py` | Tests for project mapper |

## Files Deleted

| File | Reason |
|------|--------|
| `tests/agents/project_librarian/test_cache_manager.py` (old) | Replaced with new tests |
| `tests/agents/project_librarian/test_project_mapper.py` (old) | Replaced with new tests |

## Code Structure

```python
# cache_manager.py
class FileContext(NamedTuple):
    summary: str

class ModuleContext(NamedTuple):
    summary: str
    files: dict[str, FileContext]
    submodules: dict[str, ModuleContext]

class CodeContext(NamedTuple):
    root_summary: str
    modules: dict[str, ModuleContext]
```

## JSON Format

```json
{
  "root_summary": "...",
  "modules": {
    "pkg": {
      "summary": "...",
      "files": {
        "main.py": {"summary": "..."}
      },
      "submodules": {
        "subpkg": { ... }
      }
    }
  }
}
```

## Verification

- All imports successful
- All files have valid Python syntax
- Tests written but could not run due to environment restrictions (.env file permission issues)

## Next Steps

1. Run tests when environment issues are resolved:
   ```bash
   pytest tests/agents/project_librarian/test_cache_manager.py
   pytest tests/agents/project_librarian/test_project_mapper.py
   ```

2. Verify integration with existing codebase works

3. Consider removing unused methods from `summarizer.py` that accept old dict format
