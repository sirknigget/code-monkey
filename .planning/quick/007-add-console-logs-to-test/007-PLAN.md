# Quick Plan 007: Add Console Logs to Test File

## Task
Add console logs (print statements) to `tests/agents/project_librarian/test_project_mapper_real_llm.py` at various test steps.

## Steps
1. Add print statements at key test steps in `TestProjectMapperRealLLM` class
2. Add print statements in `TestProjectMapperRealLLMWithModifiedProject` class
3. Include informative messages showing test progress and results

## Changes
- Add logging to `test_real_llm_fresh_scan`: log scan start, module count, cache creation, hash verification, context verification
- Add logging to `test_real_llm_incremental_update`: log initial scan, file modification, incremental scan results
- Add logging to `test_real_llm_specified_file_update`: log initial scan, files being updated, update results
- Add logging to `test_real_llm_generates_module_summaries`: log scan start, module file count, content checks
- Add logging to `test_real_llm_cache_survives_reload`: log initial scan, cache loading, context loading
- Add logging to `test_handles_new_subdirectory`: log initial scan, new directory creation, re-scan results
- Add logging to `test_cache_contains_file_summaries`: log scan start, md file count, content verification
