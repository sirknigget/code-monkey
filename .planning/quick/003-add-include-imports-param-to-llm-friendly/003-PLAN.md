# Quick Plan: Add include_imports parameter to llm_friendly_string

## Task 1: Update llm_friendly_string method signature
**File:** `code_monkey/agents/project_librarian/utilities/code_parser.py`

Add optional `include_imports: bool = True` parameter to `llm_friendly_string` method. When `False`, the imports section should not be included in the output.

## Task 2: Update tests
**File:** `tests/agents/project_librarian/test_code_parser.py`

Add tests for the new parameter:
- `test_excludes_imports_when_false` - Verify imports section is omitted
- `test_includes_imports_by_default` - Verify imports section is included (default behavior)
