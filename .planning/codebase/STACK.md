# Technology Stack

**Analysis Date:** 2026-01-31

## Languages

**Primary:**
- Python 3.12 - Core language for all agents, tools, and orchestration

## Runtime

**Environment:**
- Python 3.12+ (specified in `.python-version`)
- Virtual environment: `.venv/` with `uv` package management

**Package Manager:**
- `uv`  (modern, fast Python package manager)
- Lockfile: `uv.lock` present

## Frameworks

**Core:**
- `langgraph` 1.0.5+ - Agent orchestration and state management
- `langchain` 1.2.0+ - LLM framework and abstractions
- `langchain-community` 0.4.1+ - Community integrations (PlayWrightBrowserToolkit)

**LLM Providers:**
- `langchain-anthropic` 1.3.0+ - Anthropic API integration
- `langchain-openai` 1.1.6+ - OpenAI API integration

**Testing:**
- `pytest` 8.0.0+ - Test framework
- `pytest-asyncio` 1.3.0+ - Async test support for Python's asyncio

**Web Automation:**
- `playwright` 1.40.0+ - Browser automation for web research

**HTTP/Data:**
- `requests` 2.31.0+ - HTTP library for API calls
- `beautifulsoup4` 4.14.3+ - HTML/XML parsing

**Configuration:**
- `dotenv` 0.9.9+ - Environment variable management

## Key Dependencies

**Critical:**
- `langgraph` - Powers the multi-agent architecture with stateful workflows
- `langchain` - Provides LLM abstractions and tool calling
- `playwright` - Enables browser automation for web research

**Infrastructure:**
- `langchain-anthropic` - Connects to Anthropic API for model inference
- `langchain-openai` - Connects to OpenAI API (available as alternative)
- `langchain-community` - Community tools including PlayWrightBrowserToolkit

**Data Processing:**
- `requests` - HTTP requests for external APIs
- `beautifulsoup4` - Parsing web content

## Configuration

**Environment:**
- `.env` file for local development
- Loaded via `dotenv.load_dotenv(override=True)` in `src/main.py`

**Key environment variables:**
```
LANGSMITH_TRACING=true                    # LangSmith observability
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=lsv2_pt_...             # LangSmith authentication
SERPER_API_KEY=...                        # Google search API key
ANTHROPIC_BASE_URL=https://api.minimax.io/anthropic
ANTHROPIC_AUTH_TOKEN=sk-...               # Anthropic API key
ANTHROPIC_MODEL=MiniMax-M1.1              # Model name
```

**Project:**
- `pyproject.toml` - Project metadata and dependencies
- `.python-version` - Python 3.12
- `.gitignore` - Git ignore rules
- `CLAUDE.md` - Claude Code instructions

## Platform Requirements

**Development:**
- macOS (observed in environment)
- Python 3.12+
- `uv` package manager
- Playwright browsers (installed via `playwright install`)

**Production:**
- Python 3.12+ runtime
- Environment variables for API keys
- Browser binaries for Playwright

---

*Stack analysis: 2026-01-31*
