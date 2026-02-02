# Technology Stack

**Analysis Date:** 2026-02-02

## Languages

**Primary:**
- Python 3.12+ - Core application language

## Runtime

**Environment:**
- Python 3.12 (specified in `.python-version`)

**Package Manager:**
- `uv` - Fast Python package manager
- Lockfile: `uv.lock`

## Frameworks

**Core:**
- `langchain` (>=1.2.0) - LLM framework and orchestration
- `langgraph` (>=1.0.5) - Agent orchestration and state management

**Testing:**
- `pytest` (>=8.0.0) - Test runner
- `pytest-asyncio` (>=1.3.0) - Async test support for pytest

**Web Scraping/Automation:**
- `playwright` (>=1.40.0) - Browser automation
- `beautifulsoup4` (>=4.14.3) - HTML/XML parsing
- `lxml` (>=6.0.2) - XML processing library

## Key Dependencies

**LLM Integration:**
- `langchain-anthropic` (>=1.3.0) - Anthropic API integration
- `langchain-openai` (>=1.1.6) - OpenAI API integration
- `langchain-community` (>=0.4.1) - Community tools and integrations

**HTTP/Network:**
- `requests` (>=2.31.0) - HTTP library
- `dotenv` (>=0.9.9) - Environment variable loading

## Configuration

**Environment:**
- Configuration via `.env` file
- `dotenv.load_dotenv()` loads variables at runtime
- Key variables: `ANTHROPIC_API_KEY`, `SERPER_API_KEY`, `LANGSMITH_*`

**Build:**
- `pyproject.toml` - Project configuration
- `pytest.ini_options` configured in pyproject.toml with `pythonpath = ["."]`

## Platform Requirements

**Development:**
- Python 3.12+
- `uv` package manager
- Playwright browsers (installed via `playwright install`)

**Production:**
- Python 3.12+ runtime
- All dependencies from `pyproject.toml`

---

*Stack analysis: 2026-02-02*
