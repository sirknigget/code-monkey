# Quick Task 005: ProjectMapper Integration Test with Real LLM

## Description
Create an additional `project_mapper.py` integration test that uses a real LLM from `code_monkey/models/models.py` and works on a realistic mock project folder.

## Tasks

### Task 1: Create mock project folder with realistic Python project structure
**Objective:** Generate a realistic multi-module Python project in `mock_project_folder/`

**Actions:**
1. Clone or download a well-known small Python project (e.g., `httpx` or `requests` or similar popular library)
2. Structure should include:
   - Multiple hierarchical modules
   - Package with `__init__.py` files
   - Various file types (.py files)
   - Working code structure

**Expected Output:** `mock_project_folder/` directory with complete Python project

---

### Task 2: Create integration test for ProjectMapper with real LLM
**Objective:** Write a comprehensive integration test that uses real LLM and tests ProjectMapper functionality

**Actions:**
1. Create `tests/test_project_mapper_real_llm.py`
2. Use `get_minimax_model()` from `code_monkey/models/models.py`
3. Test should:
   - Initialize ProjectMapper with mock project folder
   - Run full `scan()` and verify `.codemonkey` cache is populated
   - Update some files in the mock project
   - Run `scan()` again to verify incremental update behavior
   - Modify specific files and call `update([paths])` with file list
   - Verify `.codemonkey` folder contains plausible results

**Expected Output:** `tests/test_project_mapper_real_llm.py` with passing test

---

### Task 3: Verify test execution and cache generation
**Objective:** Run the test and verify plausible results in `.codemonkey` folder

**Actions:**
1. Run the integration test
2. Verify `.codemonkey/file-hashes` exists and contains hash entries
3. Verify `.codemonkey/project-context` exists and contains project summary
4. Verify module summaries are generated for directories

**Expected Output:** Test passes, `.codemonkey` cache populated with realistic data

---

## Completion Criteria
- [x] `mock_project_folder/` exists with realistic Python project
- [x] `tests/test_project_mapper_real_llm.py` created and passes
- [x] `.codemonkey/` cache generated with plausible content
