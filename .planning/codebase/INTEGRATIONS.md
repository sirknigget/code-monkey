# External Integrations

**Analysis Date:** 2026-02-02

## APIs & External Services

**LLM Providers:**

- **Anthropic** - Primary LLM provider (MiniMax-M2.1 model via custom endpoint)
  - SDK/Client: `langchain-anthropic.ChatAnthropic`
  - Base URL: `https://api.minimax.io/anthropic` (custom proxy)
  - Auth: `ANTHROPIC_API_KEY` environment variable
  - Config: `ANTHROPIC_MODEL` env var (defaults to "MiniMax-M2.1")

- **OpenAI** - Secondary LLM provider
  - SDK/Client: `langchain_openai.ChatOpenAI`
  - Model: `gpt-4o` by default
  - Auth: `OPENAI_API_KEY` (implicit via langchain-openai)

**Web Search:**

- **Serper API** - Google search results
  - SDK/Client: `langchain_community.utilities.GoogleSerperAPIWrapper`
  - Auth: `SERPER_API_KEY` environment variable
  - Usage: `code_monkey/agents/web_researcher/tools.py`

**Observability:**

- **LangSmith** - LLM tracing and observability
  - Endpoint: `https://api.smith.langchain.com`
  - Auth: `LANGSMITH_API_KEY` environment variable
  - Config: `LANGSMITH_TRACING`, `LANGSMITH_PROJECT`

## Data Storage

**Caching:**
- Local filesystem only
- Cache directory: `.codemonkey/` (at project root)
- Storage format: JSON files for hashes, Markdown for summaries
- Files:
  - `.codemonkey/file_hashes.json` - File hash cache
  - `.codemonkey/code_context/*.md` - Per-file summaries
  - `.codemonkey/project_context.json` - Project-level context
- Implementation: `code_monkey/agents/project_librarian/cache_manager.py`

**File Storage:**
- Local filesystem only
- No external cloud storage integration detected

## Authentication & Identity

**Auth Provider:**
- API keys via environment variables
- No OAuth or identity provider integration

## Monitoring & Observability

**Error Tracking:**
- Not detected (no Sentry, Rollbar, etc.)

**Logs:**
- Python standard `logging` module
- Basic configuration in `code_monkey/main.py`:
  ```python
  logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
  ```

## CI/CD & Deployment

**Hosting:**
- Not detected (no Dockerfile, docker-compose.yml, or cloud config)

**CI Pipeline:**
- Not detected (no GitHub Actions, CircleCI, etc.)

## Environment Configuration

**Required env vars:**
- `ANTHROPIC_API_KEY` - Anthropic/MiniMax API key
- `ANTHROPIC_BASE_URL` - Custom Anthropic endpoint (optional, defaults to minimax)
- `ANTHROPIC_MODEL` - Model name (optional, defaults to MiniMax-M2.1)
- `SERPER_API_KEY` - Google search API key
- `LANGSMITH_TRACING` - Enable LangSmith tracing (optional)
- `LANGSMITH_API_KEY` - LangSmith API key (optional)
- `LANGSMITH_ENDPOINT` - LangSmith endpoint (optional)
- `LANGSMITH_PROJECT` - LangSmith project name (optional)

**Secrets location:**
- `.env` file at project root (gitignored)

## Webhooks & Callbacks

**Incoming:**
- Not detected (no web framework for HTTP endpoints)

**Outgoing:**
- Anthropic API calls via langchain-anthropic
- OpenAI API calls via langchain-openai
- Serper API calls for web search
- LangSmith API calls for tracing

---

*Integration audit: 2026-02-02*
