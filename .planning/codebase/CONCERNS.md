# Codebase Concerns

## Technical Debt

### Incomplete Implementation
- **Main entry point is stub**: `main.py` only prints "Hello from code-monkey!" - the multi-agent orchestration is not wired up
- **Project Librarian agent incomplete**: Only utilities exist (`file_discovery.py`, `code_parser.py`, `hash_utils.py`), no actual agent implementation
- **Lead Developer agent missing**: No implementation exists despite being planned
- **Cache infrastructure not implemented**: `.codemonkey/` directories for file-hashes, code-context, and project-context are planned but not created

### API Concerns
- **`create_agent` import may be incorrect**: `web_researcher.py` imports from `langchain.agents import create_agent` - this function may not exist in recent langchain versions (typically `create_react_agent` or similar)
- **Message attribute access**: `langchain_utils.py` uses `.text` attribute on messages; should be `.content` for LangChain messages

### Code Quality
- **Minimal error handling**: Most functions have no try/catch blocks (except `code_parser.py`)
- **No logging**: Project has no logging infrastructure
- **Generic type hints missing**: `json_utils.py` uses `object` parameter without type hints
- **Inconsistent async patterns**: Mix of sync/async without clear conventions

## Known Issues

### API/Integration Risks
- **GoogleSerperAPIWrapper dependency**: Requires `SERPER_API_KEY` environment variable - no validation or fallback
- **MiniMax model config**: Custom Anthropic API endpoint (`api.minimax.io`) - non-standard integration that may break
- **Playwright browser management**: No connection pooling or resource limits for browser instances

### Test Gaps
- **Integration tests hit real APIs**: `test_web_researcher.py` makes real API calls to MiniMax and Serper - expensive and flaky
- **No mocking infrastructure**: Tests don't mock external services
- **Missing unit tests for edge cases**: Code parser doesn't test malformed files beyond syntax errors

## Security Concerns

### Environment Variables
- `.env` file exists in project root (454 bytes) - not checked into git but presence suggests secrets exist locally
- No `.env.example` template for developers
- API keys required: `SERPER_API_KEY`, `ANTHROPIC_API_KEY`/`MINIMAX_API_KEY`, potentially `OPENAI_API_KEY`

### Input Validation
- **No sanitization on search queries**: User input passed directly to Google search and Playwright
- **File path handling**: `hash_utils.py` accepts arbitrary paths without validation - potential path traversal
- **No rate limiting**: Unbounded API calls could lead to cost issues or abuse

### Browser Security
- Playwright runs browser instances - potential for XSS if navigating to malicious URLs
- No sandboxing configuration for browser

## Performance Concerns

### Resource Management
- **Playwright lifecycle**: Browser instance created per `WebResearcher` - no pooling or reuse
- **InMemorySaver for checkpoints**: Won't scale - checkpoints lost on restart
- **File globbing**: `discover_python_files` scans entire directory tree - could be slow on large repos

### Scalability Issues
- No async batching for file hash computation
- No caching layer for parsed code structures
- No pagination for search results or file discovery

## Fragile Areas

### Tightly Coupled Components
- `WebResearcher.create()` factory couples Playwright lifecycle with agent creation
- Tool definitions inline with agent setup - hard to test independently

### Missing Defensive Code
- `last_message_content()` assumes messages exist and have `.text` - will crash on empty state
- `compute_file_hash()` will raise raw `OSError` on missing files
- No graceful degradation if external services unavailable

### Configuration
- Hardcoded values: `NUM_GOOGLE_RESULTS = 10`, headless defaults
- No config file or environment-based configuration system
- Model selection (`get_minimax_model`, `get_openai_model`) hardcoded

## Recommended Priorities

1. **Critical**: Fix `create_agent` import and `.text` vs `.content` issues
2. **High**: Add environment variable validation on startup
3. **High**: Implement missing agents (Project Librarian, Lead Developer)
4. **Medium**: Add proper error handling and logging
5. **Medium**: Create mock infrastructure for tests
6. **Low**: Add configuration management system
