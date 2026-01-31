# code-monkey

## What This Is

A LangGraph-based coding assistant with multi-agent architecture for development tasks. Currently has a Web Researcher agent; building toward a complete system with Project Librarian and Lead Developer agents.

## Core Value

A coding assistant that understands project context and can research, read, and modify code autonomously.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Project Librarian agent utilities:
  - File discovery — find files matching patterns, exclude venv/.git/pytest_cache
  - Parse code structure — extract classes, functions, imports from Python files
  - Hash computation — SHA-256 for change detection
- [ ] Lead Developer agent for code execution

### Out of Scope

- Mobile UI — CLI-first approach
- Cloud deployment — local development only for now

## Context

Brownfield project with existing:
- Web Researcher agent (working, tested)
- Playwright browser tools
- Google search integration
- Test infrastructure

## Constraints

- **Tech stack**: Python 3.12+, LangGraph, Playwright
- **Local-only**: No cloud services, no external API dependencies except LLMs
- **Import path**: `code_monkey/` package (not `src/`)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Package name | Avoids `src/` layout issues | ✓ Working |
| Iterative milestones | One task at a time, ask for next | — Pending |

---
*Last updated: 2026-01-31 after project initialization (iterative mode)*
