# Technology Stack

**Analysis Date:** 2026-01-31

## Languages

**Primary:**
- Python 3.12+ - Core language for all application code

## Runtime

**Environment:**
- Python 3.12+ (required)
- uv package manager for dependency management

**Package Manager:**
- uv (modern Python package manager)
- Lockfile: `.venv/pyvenv.cfg` (managed by uv)

## Frameworks

**Core:**
- LangChain 1.2.0+ - LLM framework for building AI applications
- LangGraph 1.0.5+ - Agent orchestration framework for multi-agent workflows

**Testing:**
- pytest 8.0.0+ - Test framework
- pytest-asyncio 1.3.0+ - Async test support for pytest

**Build/Dev:**
- uv - Package management and development workflow

## Key Dependencies

**LLM & AI:**
- langchain >=1.2.0 - Core LLM framework
- langchain-anthropic >=1.3.0 - Anthropic API integration
- langchain-openai >=1.1.6 - OpenAI API integration
- langchain-community >=0.4.1 - Community-contributed integrations

**Web Automation:**
- playwright >=1.40.0 - Browser automation for web research
- beautifulsoup4 >=4.14.3 - HTML/XML parsing
- lxml >=6.0.2 - XML/HTML processing library

**HTTP & Data:**
- requests >=2.31.0 - HTTP library for API calls
- dotenv >=0.9.9 - Environment variable management

## Configuration

**Environment:**
- Loaded via `dotenv.load_dotenv()` in `/Users/omergilad/workspace/AI/code-monkey/code_monkey/main.py`
- `.env` file contains all configuration
- Override=True allows .env to override system environment

**Build Configuration:**
- `pyproject.toml` - Project metadata and dependencies
- Python path configured in pytest: `pythonpath = ["."]`

## Platform Requirements

**Development:**
- Python 3.12+
- uv package manager
- Playwright browsers (installed via playwright Python package)

**Production:**
- Python 3.12+ runtime
- All dependencies from `pyproject.toml`
- Environment variables for API keys

---

*Stack analysis: 2026-01-31*
