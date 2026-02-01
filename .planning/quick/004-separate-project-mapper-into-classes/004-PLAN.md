---
phase: quick
plan: "004"
type: execute
wave: 1
files_modified:
  - "code_monkey/agents/project_librarian/project_mapper.py"
  - "code_monkey/agents/project_librarian/__init__.py"
autonomous: true
---

<objective>
Separate project_mapper.py into multiple files, one per class. The goal is cleaner organization and easier maintenance.

Output structure:
- `models.py` - FileSummary, ModuleSummary (NamedTuple models)
- `cache_manager.py` - CacheManager class
- `summarizer.py` - Summarizer class
- `directory_processor.py` - DirectoryProcessor class
- `project_mapper.py` - ProjectMapper class (main, imports others)
- `__init__.py` - Public exports of all classes
</objective>

<context>
Current file: @code_monkey/agents/project_librarian/project_mapper.py

**Main classes to extract:**
1. FileSummary (NamedTuple, lines 37-46)
2. ModuleSummary (NamedTuple, lines 49-62)
3. CacheManager (class, lines 70-264)
4. Summarizer (class, lines 272-490)
5. DirectoryProcessor (class, lines 498-661)
6. ProjectMapper (class, lines 669-827)

**Shared imports to distribute:**
- json, tempfile, time, concurrent.futures, pathlib, typing
- langchain_core modules
- code_monkey utilities (compute_file_hash, discover_python_files, parse_python_code)
</context>

<tasks>

<task type="auto">
  <name>Create models.py with FileSummary and ModuleSummary</name>
  <action>
    Create `models.py` containing:
    - All shared imports needed by multiple modules
    - FileSummary NamedTuple
    - ModuleSummary NamedTuple
    - __all__ = ["FileSummary", "ModuleSummary"]

    Shared imports to include in models.py (so other modules can import from here):
    ```python
    from pathlib import Path
    from typing import NamedTuple
    ```
  </action>
  <verify>
    uv run python -c "from code_monkey.agents.project_librarian.models import FileSummary, ModuleSummary; print('models.py OK')"
  </verify>
  <done>
    models.py created with FileSummary and ModuleSummary
  </done>
</task>

<task type="auto">
  <name>Create cache_manager.py with CacheManager class</name>
  <action>
    Create `cache_manager.py` containing:
    - Import from models: Path, json, tempfile
    - CacheManager class (original implementation)
    - __all__ = ["CacheManager"]
  </action>
  <verify>
    uv run python -c "from code_monkey.agents.project_librarian.cache_manager import CacheManager; print('cache_manager.py OK')"
  </verify>
  <done>
    cache_manager.py created with CacheManager class
  </done>
</task>

<task type="auto">
  <name>Create summarizer.py with Summarizer class</name>
  <action>
    Create `summarizer.py` containing:
    - Import from models: Path
    - Import from langchain: BaseChatModel, ChatPromptTemplate, StrOutputParser, RunnableSequence
    - Summarizer class (original implementation with 3 templates and retry logic)
    - __all__ = ["Summarizer"]
  </action>
  <verify>
    uv run python -c "from code_monkey.agents.project_librarian.summarizer import Summarizer; print('summarizer.py OK')"
  </verify>
  <done>
    summarizer.py created with Summarizer class
  </done>
</task>

<task type="auto">
  <name>Create directory_processor.py with DirectoryProcessor class</name>
  <action>
    Create `directory_processor.py` containing:
    - Import from models: Path, FileSummary
    - Import from cache_manager: CacheManager
    - Import from summarizer: Summarizer
    - Import from code_monkey utilities: parse_python_code
    - concurrent.futures import
    - DirectoryProcessor class (original implementation)
    - __all__ = ["DirectoryProcessor"]
  </action>
  <verify>
    uv run python -c "from code_monkey.agents.project_librarian.directory_processor import DirectoryProcessor; print('directory_processor.py OK')"
  </verify>
  <done>
    directory_processor.py created with DirectoryProcessor class
  </done>
</task>

<task type="auto">
  <name>Create project_mapper.py with ProjectMapper class</name>
  <action>
    Create `project_mapper.py` containing:
    - Import from models: Path
    - Import from cache_manager: CacheManager
    - Import from summarizer: Summarizer
    - Import from directory_processor: DirectoryProcessor
    - Import from code_monkey utilities: compute_file_hash, discover_python_files
    - ProjectMapper class (main orchestrator)
    - __all__ = ["ProjectMapper"]
  </action>
  <verify>
    uv run python -c "from code_monkey.agents.project_librarian.project_mapper import ProjectMapper; print('project_mapper.py OK')"
  </verify>
  <done>
    project_mapper.py created with ProjectMapper class
  </done>
</task>

<task type="auto">
  <name>Update __init__.py with all exports</name>
  <action>
    Update `__init__.py` to export all classes:
    ```python
    """Project Librarian agent utilities and ProjectMapper."""

    from code_monkey.agents.project_librarian.models import (
        FileSummary,
        ModuleSummary,
    )
    from code_monkey.agents.project_librarian.cache_manager import CacheManager
    from code_monkey.agents.project_librarian.summarizer import Summarizer
    from code_monkey.agents.project_librarian.directory_processor import (
        DirectoryProcessor,
    )
    from code_monkey.agents.project_librarian.project_mapper import ProjectMapper
    from code_monkey.agents.project_librarian.utilities import (
        compute_file_hash,
        discover_python_files,
        parse_python_code,
    )

    __all__ = [
        "CacheManager",
        "DirectoryProcessor",
        "FileSummary",
        "ModuleSummary",
        "ProjectMapper",
        "Summarizer",
        "compute_file_hash",
        "discover_python_files",
        "parse_python_code",
    ]
    ```
  </action>
  <verify>
    uv run python -c "from code_monkey.agents.project_librarian import ProjectMapper, CacheManager, Summarizer, DirectoryProcessor, FileSummary, ModuleSummary; print('All exports OK')"
  </verify>
  <done>
    __init__.py updated with all exports
  </done>
</task>

</tasks>

<success_criteria>
- models.py exists with FileSummary and ModuleSummary
- cache_manager.py exists with CacheManager
- summarizer.py exists with Summarizer
- directory_processor.py exists with DirectoryProcessor
- project_mapper.py exists with ProjectMapper
- __init__.py exports all 5 classes
- All imports resolve without errors
- Backward compatibility: imports from main module still work
</success_criteria>

<output>
After completion, create `.planning/quick/004-SUMMARY.md` with:
- Brief description of what was refactored
- New file structure
- Verification that all imports work
