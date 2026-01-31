# External Integrations

**Analysis Date:** 2026-01-31

## APIs & External Services

**LLM Providers:**

- **Anthropic** - Primary LLM provider
  - SDK/Client: `langchain-anthropic`
  - Auth: `ANTHROPIC_AUTH_TOKEN` env var
  - Base URL: `ANTHROPIC_BASE_URL` (custom endpoint to minimax.io)
  - Model: `ANTHROPIC_MODEL` (set to MiniMax-M2.1)
  - Used by: `src/agents/web_researcher/web_researcher.py` for agent reasoning

- **OpenAI** - Alternative LLM provider
  - SDK/Client: `langchain-openai`
  - Available but not currently used

**Web Research:**

- **Serper API** - Google search results
  - SDK/Client: `langchain_community.utilities.GoogleSerperAPIWrapper`
  - Auth: `SERPER_API_KEY` env var
  - Used by: `google_search_tool` in `src/agents/web_researcher/tools.py`
  - Returns: Top 10 organic Google results

- **Playwright** - Browser automation
  - SDK/Client: `playwright` + `langchain_community.agent_toolkits.PlayWrightBrowserToolkit`
  - Purpose: Navigate web pages, extract content for web research
  - Used by: `PlaywrightTools` class in `src/agents/web_researcher/tools.py`
  - Browser: Chromium (headless mode)

**Observability:**

- **LangSmith** - LLM observability and tracing
  - SDK/Client: Built into langchain via environment variables
  - Auth: `LANGSMITH_API_KEY` env var
  - Endpoint: `LANGSMITH_ENDPOINT` (https://api.smith.langchain.com)
  - Project: `LANGSMITH_PROJECT` (code_monkey)
  - Enabled: `LANGSMITH_TRACING=true`

## Data Storage

**Databases:**
- None currently detected (in-memory only)

**File Storage:**
- Local filesystem only
- No cloud storage integration

**Caching:**
- In-memory checkpointer: `langgraph.checkpoint.memory.InMemorySaver`
  - Used in `src/agents/web_researcher/web_researcher.py` for agent state
- Planned cache: `.codemonkey/file-hashes`, `.codemonkey/code-context`, `.codemonkey/project-context`

## Authentication & Identity

**Auth Provider:**
- API key-based authentication via environment variables
- No OAuth or user authentication system

**Auth Variables:**
- `ANTHROPIC_AUTH_TOKEN` - Anthropic API key
- `SERPER_API_KEY` - Serper API key
- `LANGSMITH_API_KEY` - LangSmith API key

## Monitoring & Observability

**Error Tracking:**
- LangSmith tracing for LLM calls
- No dedicated error tracking service (e.g., Sentry)

**Logs:**
- Python standard logging
- LangSmith traces for agent execution

## CI/CD & Deployment

**Hosting:**
- Not detected (local development focus)

**CI Pipeline:**
- Not configured
- Tests via `pytest` available at `tests/`

## Environment Configuration

**Required env vars:**
| Variable | Purpose | Required |
|----------|---------|----------|
| `ANTHROPIC_AUTH_TOKEN` | Anthropic API key | Yes |
| `ANTHROPIC_BASE_URL` | Anthropic endpoint | Yes (custom) |
| `ANTHROPIC_MODEL` | Model name | Yes |
| `SERPER_API_KEY` | Google search | Yes |
| `LANGSMITH_API_KEY` | Tracing | Optional |
| `LANGSMITH_TRACING` | Enable tracing | Optional |

**Secrets location:**
- `.env` file (gitignored)
- Never committed to version control

**Configuration approach:**
- `dotenv` loads `.env` in `src/main.py`
- `load_dotenv(override=True)` allows environment to override file

## Webhooks & Callbacks

**Incoming:**
- None currently configured

**Outgoing:**
- `LANGSMITH_ENDPOINT` - LangSmith API calls
- `api.minimax.io/anthropic` - Anthropic API calls
- `google.serper.dev` - Serper API calls

---

*Integration audit: 2026-01-31*
