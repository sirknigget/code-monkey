# code-monkey Roadmap

## Current Milestone: v1.0 Foundation

Building core infrastructure for the multi-agent coding assistant.

### Phase 01: Build Project Librarian agent utilities

**Goal:** Build utility functions for file discovery, code parsing, and hash computation
**Depends on:** N/A (first phase)
**Plans:** 4 plans in 4 waves

Plans:
- [x] 01-01-PLAN.md — File discovery utility (pathlib glob with directory exclusion)
- [x] 01-02-PLAN.md — Code parser utility (AST-based class/function/import extraction)
- [x] 01-03-PLAN.md — Hash utilities (SHA-256 file hashing for change detection)
- [x] 01-04-PLAN.md — Integration tests and module finalization

**Status:** Complete ✓ (2026-01-31)

**Details:**
Building core utilities for the Project Librarian agent using Python standard library:
- File discovery with pathlib.Path.glob(), excluding venv/.git/__pycache__
- Code parsing with ast.NodeVisitor to extract classes, functions, imports
- SHA-256 hashing with hashlib.file_digest() for change detection

### Phase 02: Project Mapper class

**Goal:** Build ProjectMapper class for project context file generation
**Depends on:** Phase 01
**Plans:** 1 plan in 1 wave

Plans:
- [x] 02-PLAN.md — ProjectMapper class with run() method, hash-based change detection, LLM summarization, and cache infrastructure

**Status:** Complete (2026-02-01)

**Details:**
ProjectMapper class with 4 internal composed classes:
- CacheManager: atomic cache writes to .codemonkey/
- Summarizer: 3 LLM templates with 10-line limit, 3x retry with backoff
- DirectoryProcessor: top-down traversal, parallel file processing
- ProjectMapper: public scan()/update() API, hash-based change detection

Cache structure:
- .codemonkey/file_hashes.json - hash cache
- .codemonkey/code_context/{path}.md - per-file summaries
- .codemonkey/project_context.json - project context

**Verification:** Passed (6/6 must-haves verified)

---

## Future Milestones

### v1.1 Lead Developer Agent

- Lead Developer agent for code execution
- Security reviewer integration
- CLI interface
