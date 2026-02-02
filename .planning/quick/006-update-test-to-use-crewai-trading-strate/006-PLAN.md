---
phase: quick-006
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: []
autonomous: true
must_haves:
  truths:
    - "Tests use crewai_trading_strategy template via copy utility"
    - "Template fixture provides isolated working copy per test"
    - "Original mock_project template remains unchanged"
  artifacts:
    - path: "tests/fixtures/template_fixture.py"
      provides: "Fixture to copy and yield crewai_trading_strategy template"
    - path: "tests/agents/project_librarian/test_project_mapper_real_llm.py"
      provides: "Updated test using new fixture and template paths"
  key_links:
    - from: "tests/fixtures/template_fixture.py"
      to: "mock_project/template/crewai_trading_strategy"
      via: "shutil.copytree"
    - from: "test_project_mapper_real_llm.py"
      to: "tests/fixtures/template_fixture.py"
      via: "import and use crewai_template fixture"
---

<objective>
Update test_project_mapper_real_llm.py to use the crewai_trading_strategy template with a proper copy utility fixture.

Purpose: The current test references an undefined `MOCK_PROJECT_PATH` and uses the wrong template. This update fixes the fixture bug and switches to the proper template structure.
Output: Working tests using crewai_trading_strategy template with isolated working copies
</objective>

<execution_context>
@/Users/omergilad/.claude/get-shit-done/workflows/execute-plan.md
@/Users/omergilad/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@tests/agents/project_librarian/test_project_mapper_real_llm.py

Current issues in test file:
- `mock_project_dir` fixture defined but never used
- `MOCK_PROJECT_PATH` referenced but never defined
- Tests should use `crewai_trading_strategy` template paths
</context>

<tasks>

<task type="auto">
  <name>Create template fixture with copy utility</name>
  <files>tests/fixtures/template_fixture.py</files>
  <action>
    Create `tests/fixtures/template_fixture.py` with:

    1. Import shutil, tempfile, Path, pytest
    2. Define TEMPLATE_ROOT constant pointing to mock_project/template/crewai_trading_strategy
    3. Create `@pytest.fixture(scope="session")` named `crewai_template_root` that returns TEMPLATE_ROOT path
    4. Create `@pytest.fixture` named `crewai_working_copy` that:
       - Creates temp directory via tempfile.mkdtemp()
       - Copies TEMPLATE_ROOT to temp dir via shutil.copytree()
       - Yields the path to the working copy
       - In teardown: removes the temp directory via shutil.rmtree()

    This ensures each test gets an isolated copy that can be modified without affecting the original template.
  </action>
  <verify>
    Run `python -c "from tests.fixtures.template_fixture import crewai_working_copy; print('Fixture imports successfully')"`
  </verify>
  <done>
    Fixture file created at tests/fixtures/template_fixture.py with copy utility and proper teardown
  </done>
</task>

<task type="auto">
  <name>Update test file to use new fixture and paths</name>
  <files>tests/agents/project_librarian/test_project_mapper_real_llm.py</files>
  <action>
    Update the test file to:

    1. Remove the broken `mock_project_dir` fixture (lines 17-20)
    2. Add import: `from tests.fixtures.template_fixture import crewai_working_copy`
    3. Replace all references to `MOCK_PROJECT_PATH` with `crewai_working_copy` (as a Path via fixture)
    4. Update file path references from `src/requests/` to `src/crewai_trading_strategy/`:
       - Line 85: `src/requests/__init__.py` → `src/crewai_trading_strategy/__init__.py`
       - Line 111-112: `src/requests/exceptions.py`, `src/requests/status_codes.py` → valid files in the template (e.g., `src/utils/safe_python_code_executor.py`, `src/crewai_trading_strategy/constants.py`)
       - Line 185: `src/requests/new_feature` → `src/utils/new_feature`

    Key path changes:
    - `MOCK_PROJECT_PATH / "src" / "requests"` → `crewai_working_copy / "src" / "crewai_trading_strategy"`
    - `MOCK_PROJECT_PATH / "src" / "requests" / "exceptions.py"` → choose existing file like `src/utils/safe_python_code_executor.py`
  </action>
  <verify>
    Run `python -m pytest tests/agents/project_librarian/test_project_mapper_real_llm.py -v --collect-only` to verify test collection works
  </verify>
  <done>
    Test file updated with working fixture, correct template paths, and proper crewai_trading_strategy structure
  </done>
</task>

</tasks>

<verification>
Run the full test suite to confirm:
- `python -m pytest tests/agents/project_librarian/test_project_mapper_real_llm.py -v`
- All tests pass using the crewai_trading_strategy template
</verification>

<success_criteria>
- Tests/fixtures/template_fixture.py created with copy utility
- Test file imports and uses the new fixture
- All test assertions pass with crewai_trading_strategy template
- Original template directory remains unmodified
</success_criteria>

<output>
After completion, create `.planning/quick/006-update-test-to-use-crewai-trading-strate/006-01-SUMMARY.md`
</output>
