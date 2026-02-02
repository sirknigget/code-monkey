# Quick Plan: TaskResult Progress Tracking for ProjectMapper

## Task
Make `project_mapper.py` return progress using `TaskResult`. Progress composition:
- Initial scan: 1 point
- Summary processing from `process_changed_directories`: `progress_max` points
- Project summarization: 1 point

Update unit and integration tests to respect progress, with progress bars in integration tests.

## Changes Required

### 1. Modify `project_mapper.py`
- Change `scan()` and `update()` to return `TaskResult[dict[Path, str]]` instead of `dict[Path, str]`
- Compute total progress max: `1 (initial scan) + N (directories) + 1 (project summarization) = N + 2`
- Yield `TaskResult` objects at each stage with proper progress values
- Update `_run()` method to be a generator yielding `TaskResult`

### 2. Update Unit Tests (`test_project_mapper.py`)
- Add tests for `TaskResult` return type from `scan()` and `update()`
- Test that progress values are computed correctly
- Test progress percentage calculations

### 3. Update Integration Tests (`test_project_mapper_integration.py`)
- Add progress bar display during scan/update operations
- Print progress updates in real-time
- Test that final results are correctly extracted from `TaskResult`

### 4. Update Real LLM Tests (`test_project_mapper_real_llm.py`)
- Add progress bar display using rich or tqdm
- Print progress during long-running operations
- Show directory processing progress

## Files to Modify
1. `code_monkey/agents/project_librarian/project_mapper.py`
2. `tests/agents/project_librarian/test_project_mapper.py`
3. `tests/agents/project_librarian/test_project_mapper_integration.py`
4. `tests/agents/project_librarian/test_project_mapper_real_llm.py`

## Implementation Notes
- Progress formula: `progress_max = num_changed_dirs + 2` (1 for scan, 1 for project context)
- Initial scan yields `TaskResult(result={}, progress=0, progress_max=N+2)`
- After each directory: `TaskResult(result=results, progress=i, progress_max=N+2)`
- After project summarization: `TaskResult(result=final_result, progress=N+2, progress_max=N+2)`
