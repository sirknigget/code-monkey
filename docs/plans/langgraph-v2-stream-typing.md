# Plan: LangGraph v2 stream typing upgrade

## Context

We want to upgrade LangGraph in `/Users/omergilad/workspace/AI/code-monkey` to a version that exposes the official v2 stream-part typing, then replace the current tuple-based stream handling in `code_monkey/graph/agent_graph.py` with the official typed stream shape. The current repo is locked to `langgraph==1.0.5`, and local verification showed that this installed version does **not** export `StreamPart` / `UpdatesStreamPart` / `CustomStreamPart` from `langgraph.types`, so the docs-only migration is not safe without a dependency upgrade.

The intended outcome is:
1. upgrade to a LangGraph version that actually supports official v2 stream-part typing,
2. refactor `AgentGraph.astream()` to use that official API,
3. keep the app-facing `StreamChunk` behavior unchanged.

Implementation should resume from a clean working tree.

## Recommended approach

1. **Upgrade the LangGraph family together**
   - Update `/Users/omergilad/workspace/AI/code-monkey/pyproject.toml` from `langgraph>=1.0.5` to a version range that includes the v2 stream typing support, e.g. `langgraph>=1.1,<2`.
   - Regenerate `/Users/omergilad/workspace/AI/code-monkey/uv.lock` so these resolve together:
     - `langgraph`
     - `langgraph-prebuilt`
     - `langgraph-checkpoint`
     - `langgraph-checkpoint-sqlite`
   - Reuse the existing dependency tooling already documented in the repo (`uv lock`, `uv sync`).

2. **Verify the upgraded package exposes the expected official types**
   - Confirm the installed `langgraph.types` exports the stream-part types needed for the refactor.
   - Confirm `CompiledStateGraph.astream(...)` accepts `version="v2"` and works with `stream_mode=["updates", "custom"]`.

3. **Refactor the stream adapter in `AgentGraph`**
   - Modify `/Users/omergilad/workspace/AI/code-monkey/code_monkey/graph/agent_graph.py`.
   - Replace the current tuple-based handling:
     - `cast(AsyncIterator[tuple[str, object]], ...)`
     - `async for mode, data in stream`
   - Switch to the official v2 stream-part envelope:
     - call `self._graph.astream(..., stream_mode=["updates", "custom"], version="v2")`
     - branch on `part["type"]`
     - read payload from `part["data"]`
   - Preserve the public behavior of `AgentGraph.astream()` by continuing to yield the same `StreamChunk` values in the same order.

4. **Keep local typing only for app-specific payloads if needed**
   - Reuse the existing local `StreamChunk` dataclass in `/Users/omergilad/workspace/AI/code-monkey/code_monkey/graph/agent_graph.py`.
   - If LangGraph only types the stream envelope and not the custom tester payload, keep a small local `TypedDict` only for the custom `{"kind": ..., "content": ...}` payload.
   - Avoid broad `Any` or new `# type: ignore` comments.

5. **Check secondary compatibility points after the upgrade**
   - Inspect these files for any LangGraph typing or API fallout:
     - `/Users/omergilad/workspace/AI/code-monkey/code_monkey/graph/nodes_provider.py`
     - `/Users/omergilad/workspace/AI/code-monkey/code_monkey/graph/default_nodes_provider.py`
     - `/Users/omergilad/workspace/AI/code-monkey/code_monkey/graph/nodes/tester_node.py`
     - `/Users/omergilad/workspace/AI/code-monkey/code_monkey/graph/checkpointer.py`
     - `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/web_researcher.py`
   - Specifically verify `StreamWriter`, `AsyncSqliteSaver`, `InMemorySaver`, and the checkpointer methods currently used by `AgentGraph` (`aget_tuple`, `aget`, `adelete_thread`).

6. **Resume implementation from a clean baseline**
   - After saving this plan, revert the temporary local edits from this session so the repository is left clean except for this plan file.

## Critical files

- `/Users/omergilad/workspace/AI/code-monkey/pyproject.toml`
- `/Users/omergilad/workspace/AI/code-monkey/uv.lock`
- `/Users/omergilad/workspace/AI/code-monkey/code_monkey/graph/agent_graph.py`
- `/Users/omergilad/workspace/AI/code-monkey/code_monkey/graph/nodes_provider.py`
- `/Users/omergilad/workspace/AI/code-monkey/code_monkey/graph/default_nodes_provider.py`
- `/Users/omergilad/workspace/AI/code-monkey/code_monkey/graph/nodes/tester_node.py`
- `/Users/omergilad/workspace/AI/code-monkey/code_monkey/graph/checkpointer.py`
- `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/web_researcher.py`
- `/Users/omergilad/workspace/AI/code-monkey/tests/graph/test_agent_graph.py`
- `/Users/omergilad/workspace/AI/code-monkey/tests/controller/test_controller.py`

## Verification

When implementation resumes:
1. `uv lock`
2. `uv sync`
3. verify the new installed `langgraph.types` exports the official stream-part types
4. `uv run pyright /Users/omergilad/workspace/AI/code-monkey/code_monkey/graph/agent_graph.py`
5. `uv run ruff check /Users/omergilad/workspace/AI/code-monkey/code_monkey/graph/agent_graph.py`
6. `uv run pytest /Users/omergilad/workspace/AI/code-monkey/tests/graph/test_agent_graph.py -v`
7. `uv run pytest /Users/omergilad/workspace/AI/code-monkey/tests/controller/test_controller.py -v`
8. if checkpoint APIs or persistence behavior change, run the focused persistence/conversation-history tests that cover graph checkpoint restore and history retrieval

## Risks to watch

- The docs describe `version="v2"`, but the installed package must be verified locally before coding against it.
- The official LangGraph typing may cover the stream envelope but not the app-specific custom payload shape.
- Upgrading LangGraph may also shift `langgraph-prebuilt` and checkpoint package behavior, so the graph/checkpointer integration is the main regression risk outside of `AgentGraph.astream()`.
- The app-level contract should remain `StreamChunk`; tests should continue to validate normalized output rather than raw LangGraph events.
