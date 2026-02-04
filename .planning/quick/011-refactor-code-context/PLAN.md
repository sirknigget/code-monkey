# Quick Task 011: Refactor cache_manager and project_mapper for unified code context

## Objective
Refactor `cache_manager.py` to use a single JSON file for code context with a hierarchical object structure. Refactor `project_mapper.py` to use incremental updates.

## Changes

### 1. cache_manager.py

**Add data classes:**
```python
class FileContext(NamedTuple):
    """A file in the code hierarchy."""
    summary: str

class ModuleContext(NamedTuple):
    """A module in the code hierarchy."""
    summary: str
    files: dict[str, FileContext]
    submodules: dict[str, ModuleContext]

class CodeContext(NamedTuple):
    """Root code context containing modules hierarchy."""
    root_summary: str  # Summary of root module
    modules: dict[str, ModuleContext]  # Top-level modules
```

**Add methods:**
- `save_code_context(ctx: CodeContext) -> None`
- `load_code_context() -> CodeContext | None`
- Keep `save_project_context`/`load_project_context` as-is (separate from code context)

**Remove:**
- `save_file_summary`/`load_file_summary`
- `save_module_summary`/`load_module_summary`

### 2. project_mapper.py

**Update flow:**
1. `scan()`:
   - Load `CodeContext` from cache at start
   - Compute hashes, find changed files
   - Only process changed directories
   - For each changed module: regenerate module summary
   - Regenerate root summary if any changes
   - Save new `CodeContext` to cache
   - Generate `ProjectContext` (unchanged)

2. `update(paths)`:
   - Same incremental flow as `scan()`

3. When revising existing summaries:
   - Read the current summary first
   - Preserve non-changed parts

### 3. Tests

**Delete:**
- `tests/agents/project_librarian/test_cache_manager.py`
- `tests/agents/project_librarian/test_project_mapper.py`

**Create new tests:**
- Test `CodeContext`, `ModuleContext`, `FileContext` structures
- Test `save_code_context`/`load_code_context` round-trip
- Test `project_mapper.py` incremental update logic
- Test that unchanged modules preserve their summaries

## Files Modified

| File | Changes |
|------|---------|
| `code_monkey/agents/project_librarian/cache_manager.py` | Add data classes, refactor to single JSON |
| `code_monkey/agents/project_librarian/project_mapper.py` | Use incremental context updates |
| `tests/agents/project_librarian/test_cache_manager.py` | Delete and recreate |
| `tests/agents/project_librarian/test_project_mapper.py` | Delete and recreate |

## Verification

- All new tests pass
- Integration with existing codebase works
