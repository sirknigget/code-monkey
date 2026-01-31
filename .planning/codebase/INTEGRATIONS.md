# External Integrations

**Analysis Date:** 2026-01-31

## APIs & External Services

**LLM Providers:**

- **Anthropic / MiniMax** - Primary LLM provider
  - SDK/Client: `langchain-anthropic.ChatAnthropic`
  - Function: `get_minimax_model()` in `code_monkey/models/models.py`
  - Auth: `ANTHROPIC_API_KEY` env var
  - Base URL: `ANTHROPIC_BASE_URL` (custom endpoint: `https://api.minimax.io/anthropic`)
  - Model: `ANTHROPIC_MODEL` (set to `MiniMax-M2.1`)
  - Used by: `code_monkey/agents/web_researcher/web_researcher.py` for agent reasoning

- **OpenAI** - Alternative LLM provider
  - SDK/Client: `langchain-openai.ChatOpenAI`
  - Function: `get_openai_model()` in `code_monkey/models/models.py`
  - Auth: `OPENAI_API_KEY` env var (not currently set)
  - Available but not currently used

**Web Research:**

- **Serper API** - Google search results
  - SDK/Client: `langchain_community.utilities.GoogleSerperAPIWrapper`
  - Auth: `SERPER_API_KEY` env var
  - Tool: `google_search_tool()` in `code_monkey/agents/web_researcher/tools.py`
  - Returns: Top 10 organic Google results
  - Config: `NUM_GOOGLE_RESULTS = 10`

- **Playwright** - Browser automation
  - SDK/Client: `playwright` + `langchain_community.agent_toolkits.PlayWrightBrowserToolkit`
  - Purpose: Navigate web pages, extract content for web research
  - Used by: `PlaywrightTools` class in `code_monkey/agents/web_researcher/tools.py`
  - Browser: Chromium (headless mode via `playwright.chromium.launch`)

**Observability:**

- **LangSmith** - LLM observability and tracing
  - SDK/Client: Built into langchain via environment variables
  - Auth: `LANGSMITH_API_KEY` env var
  - Endpoint: `LANGSMITH_ENDPOINT` (`https://api.smith.langchain.com`)
  - Project: `LANGSMITH_PROJECT` (`code_monkey`)
  - Enabled: `LANGSMITH_TRACING=true`

## Data Storage

**Databases:**
- None currently detected (in-memory only)

**File Storage:**
- Local filesystem only
- No cloud storage integration

**Caching:**
- In-memory checkpointer: `langgraph.checkpoint.memory.InMemorySaver`
  - Used in `code_monkey/agents/web_researcher/web_researcher.py` for agent state
- Planned cache: `.codemonkey/file-hashes`, `.codemonkey/code-context`, `.codemonkey/project-context`

## Authentication & Identity

**Auth Provider:**
- API key-based authentication via environment variables
- No OAuth or user authentication system

**Auth Variables:**
- `ANTHROPIC_API_KEY` - Anthropic/MiniMax API key
- `SERPER_API_KEY` - Serper API key
- `LANGSMITH_API_KEY` - LangSmith API key
- `OPENAI_API_KEY` - OpenAI API key (not set)

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
| Variable | Purpose | Status |
|----------|---------|--------|
| `ANTHROPIC_API_KEY` | Anthropic/MiniMax API key | Set |
| `ANTHROPIC_BASE_URL` | Anthropic endpoint | Set |
| `ANTHROPIC_MODEL` | Model name | Set |
| `SERPER_API_KEY` | Google search | Set |
| `LANGSMITH_API_KEY` | Tracing | Set |
| `LANGSMITH_TRACING` | Enable tracing | Set |
| `LANGSMITH_PROJECT` | LangSmith project | Set |
| `OPENAI_API_KEY` | OpenAI API | Not set |

**Secrets location:**
- `.env` file in project root
- Gitignored

**Configuration approach:**
- `dotenv` loads `.env` in `code_monkey/main.py`
- `load_dotenv(override=True)` allows environment to override file

## Webhooks & Callbacks

**Incoming:**
- None currently configured

**Outgoing:**
- `LANGSMITH_ENDPOINT` - LangSmith API calls
- `api.minimax.io/anthropic` - Anthropic/MiniMax API calls
- `google.serper.dev` - Serper API calls

---

*Integration audit: 2026-01-31*
