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

---

## Future Milestones

### v1.1 Lead Developer Agent

- Lead Developer agent for code execution
- Security reviewer integration
- CLI interface
