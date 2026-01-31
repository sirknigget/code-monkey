# External Integrations

**Analysis Date:** 2026-01-31

## APIs & External Services

**LLM Providers:**

- **OpenAI** - Primary LLM provider
  - Integration: `langchain_openai.ChatOpenAI`
  - Usage: `code_monkey/models/models.py` - `get_openai_model()`
  - Auth: `OPENAI_API_KEY` (env var)

- **Anthropic (via MiniMax endpoint)** - Secondary LLM provider
  - Integration: `langchain_anthropic.ChatAnthropic`
  - Custom endpoint: `https://api.minimax.io/anthropic`
  - Usage: `code_monkey/models/models.py` - `get_minimax_model()`
  - Model: MiniMax-M2.1
  - Auth: `ANTHROPIC_API_KEY` (env var)
  - Configuration: `ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL` (env vars)

**Web Research:**

- **Serper API** - Google search results
  - Integration: `langchain_community.utilities.GoogleSerperAPIWrapper`
  - Usage: `code_monkey/agents/web_researcher/tools.py` - `google_search_tool()`
  - Auth: `SERPER_API_KEY` (env var)
  - Returns: Top 10 organic search results with title, link, snippet

## Data Storage

**File Storage:**
- Local filesystem only for code and project files
- `.codemonkey/file-hashes` - File hash cache (planned)
- `.codemonkey/code-context` - Per-file summaries (planned)
- `.codemonkey/project-context` - Project context (planned)

**Caching:**
- In-memory checkpointer: `langgraph.checkpoint.memory.InMemorySaver`
  - Usage: `code_monkey/agents/web_researcher/web_researcher.py`
  - Purpose: LangGraph agent state persistence

## Authentication & Identity

**API Key Management:**
- All credentials via environment variables
- `.env` file loaded at application startup
- Secrets:
  - `LANGSMITH_API_KEY` - LangSmith tracing
  - `SERPER_API_KEY` - Serper search
  - `ANTHROPIC_API_KEY` - Anthropic/MiniMax
  - `OPENAI_API_KEY` - OpenAI

## Monitoring & Observability

**Tracing:**
- **LangSmith** - LLM application tracing and monitoring
  - Configuration: `LANGSMITH_TRACING=true`
  - Endpoint: `https://api.smith.langchain.com`
  - Project: `code_monkey`
  - Auth: `LANGSMITH_API_KEY` (env var)

## CI/CD & Deployment

**Development Workflow:**
- Local execution via `uv run python main.py`
- uv for dependency management and script execution

**Testing:**
- pytest runs via `uv run pytest`

## Environment Configuration

**Required env vars:**
- `ANTHROPIC_API_KEY` - Anthropic/MiniMax API access
- `ANTHROPIC_BASE_URL` - Custom Anthropic endpoint (MiniMax)
- `ANTHROPIC_MODEL` - Model name (MiniMax-M2.1)
- `OPENAI_API_KEY` - OpenAI API access
- `SERPER_API_KEY` - Google search via Serper
- `LANGSMITH_TRACING` - Enable LangSmith tracing (true/false)
- `LANGSMITH_API_KEY` - LangSmith credentials
- `LANGSMITH_ENDPOINT` - LangSmith server URL
- `LANGSMITH_PROJECT` - LangSmith project name

**Secrets location:**
- `.env` file in project root
- Loaded with `override=True` to take precedence

## Webhooks & Callbacks

**Incoming:**
- Not applicable - no HTTP server endpoints currently

**Outgoing:**
- OpenAI API: `https://api.openai.com/v1/chat/completions`
- Anthropic/MiniMax: `https://api.minimax.io/anthropic`
- LangSmith: `https://api.smith.langchain.com`
- Serper: `https://google.serper.io/search`

## Browser Automation

**Playwright:**
- Integration: `playwright.async_api` + `langchain_community.agent_toolkits.PlayWrightBrowserToolkit`
- Usage: `code_monkey/agents/web_researcher/tools.py` - `PlaywrightTools` class
- Browser: Chromium (configurable headless mode)
- Tools provided: navigate_browser, click, input, extract_page_content, etc.

---

*Integration audit: 2026-01-31*
