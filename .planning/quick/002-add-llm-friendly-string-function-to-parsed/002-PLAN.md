# Quick Plan: Add llm_friendly_string function to ParsedCode

## Task 1: Add llm_friendly_string method to ParsedCode class
**File:** `code_monkey/agents/project_librarian/utilities/code_parser.py`

Add a method to `ParsedCode` that outputs the parsed code structure in an LLM-friendly format.

Expected output format:
```
=== Classes ===
- ClassName
  - method1
  - async method2
  - InnerClass
    - inner_method

=== Functions ===
- function_name
- async async_function

=== Imports ===
- module.submodule
- module
```

## Task 2: Add test for llm_friendly_string
**File:** `tests/agents/project_librarian/test_code_parser.py`

Add tests covering:
- Classes with methods
- Inner classes
- Top-level functions
- Imports
- Empty case
