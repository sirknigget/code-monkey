---
phase: quick
plan: 013
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/agents/project_librarian/test_summarizer.py
autonomous: true

must_haves:
  truths:
    - "Summarizer.summarize_file passes correct prompt variables to LLM chain"
    - "Summarizer.summarize_module formats file infos and passes to LLM chain"
    - "Summarizer.summarize_project extracts module summaries and passes to LLM chain"
    - "Summarizer initializes with retry-wrapped LLM"
  artifacts:
    - path: "tests/agents/project_librarian/test_summarizer.py"
      provides: "Unit tests for Summarizer class"
      min_lines: 100
  key_links:
    - from: "tests/agents/project_librarian/test_summarizer.py"
      to: "code_monkey/agents/project_librarian/summarizer.py"
      via: "imports Summarizer class"
      pattern: "from code_monkey.*summarizer import"
---

<objective>
Write comprehensive unit tests for the Summarizer class using mock LLM.

Purpose: Verify that the Summarizer correctly builds prompts and passes the right variables to LLM chains without making actual API calls.
Output: tests/agents/project_librarian/test_summarizer.py with passing tests.
</objective>

<execution_context>
@/Users/omergilad/.claude/get-shit-done/workflows/execute-plan.md
@/Users/omergilad/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@code_monkey/agents/project_librarian/summarizer.py
@code_monkey/agents/project_librarian/summarizer_prompts.py
@code_monkey/agents/project_librarian/cache_manager.py
@tests/agents/project_librarian/test_cache_manager.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write unit tests for Summarizer class</name>
  <files>tests/agents/project_librarian/test_summarizer.py</files>
  <action>
Write comprehensive unit tests for the Summarizer class. Use a mock LLM that captures invocations to verify prompt construction.

Test structure (follow test_cache_manager.py style with pytest fixtures and class-based test grouping):

1. **Fixtures:**
   - `mock_llm`: Create a mock BaseChatModel that returns predictable responses and allows inspection of received prompts
   - `summarizer`: Summarizer instance with mock LLM

2. **TestSummarizerInit:**
   - Test that __init__ wraps LLM with retry (verify with_retry called)
   - Test that chains are created

3. **TestSummarizeFile:**
   - Test that summarize_file passes correct input_vars: filepath, code, parent_context, max_lines
   - Test default parent_context is "(none)" when None passed
   - Test output is stripped

4. **TestSummarizeModule:**
   - Test that summarize_module formats file_infos correctly (concatenates with "---" separator)
   - Test correct input_vars: module_path, file_summaries, parent_context, max_lines
   - Test with multiple FileInfo entries
   - Test with empty file_infos list

5. **TestModuleSummariesFromCodeContext:**
   - Test _module_summaries_from_code_context extracts all summaries recursively
   - Test root module uses empty string as path
   - Test nested modules build correct paths (e.g., "pkg/subpkg")

6. **TestSummarizeProject:**
   - Test summarize_project passes correct input_vars: module_summaries, project_name, project_structure, max_lines
   - Test that module summaries are formatted correctly

Mock LLM approach:
```python
from unittest.mock import MagicMock, patch
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

class MockLLM(BaseChatModel):
    """Mock LLM that captures calls and returns predictable responses."""

    def __init__(self):
        super().__init__()
        self.last_input = None
        self.response_text = "Mock summary response"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.last_input = messages
        # Return structure that StrOutputParser expects
        ...

    def with_retry(self, **kwargs):
        return self  # Return self for testing

    @property
    def _llm_type(self):
        return "mock"
```

Alternative simpler approach - patch the chain invoke:
```python
@pytest.fixture
def summarizer():
    mock_llm = MagicMock(spec=BaseChatModel)
    mock_llm.with_retry.return_value = mock_llm
    return Summarizer(mock_llm)

def test_summarize_file(summarizer):
    with patch.object(summarizer._file_chain, 'invoke', return_value="  Summary  ") as mock_invoke:
        result = summarizer.summarize_file(Path("/test/file.py"), "def foo(): pass")
        mock_invoke.assert_called_once()
        call_args = mock_invoke.call_args[0][0]
        assert call_args["filepath"] == "/test/file.py"
        assert call_args["code"] == "def foo(): pass"
        assert call_args["parent_context"] == "(none)"
        assert call_args["max_lines"] == Summarizer.MAX_FILE_SUMMARY_LINES
        assert result == "Summary"  # Verify strip() applied
```

Use the patching approach as it is cleaner and directly tests the contract.
  </action>
  <verify>uv run pytest tests/agents/project_librarian/test_summarizer.py -v</verify>
  <done>All tests pass. Tests verify prompt variable construction for all three summarization methods.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/agents/project_librarian/test_summarizer.py -v` - all tests pass
- Tests cover: __init__, summarize_file, summarize_module, _module_summaries_from_code_context, summarize_project
- No actual LLM calls made (all mocked)
</verification>

<success_criteria>
- At least 10 test cases covering the Summarizer class
- All three summarization methods tested (file, module, project)
- Mock LLM used throughout (no real API calls)
- Tests verify correct prompt variable construction
- All tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/013-write-unit-tests-for-summarizer/013-SUMMARY.md`
</output>
