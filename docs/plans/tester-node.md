# Plan: Tester Node + Chat Summarizer Node

## Context

The orchestrator currently ends the graph turn when it produces no tool calls. This plan adds two new nodes between the orchestrator's "done" exit and END:

1. **Summarizer node** — condenses prior conversation history so the tester has focused context without the full message history
2. **Tester node** — verifies the orchestrator's work by running bash commands and returning structured pass/fail feedback

If the tester fails, the graph routes back to the orchestrator with the failure injected as an AIMessage. A `MAX_REVIEW_CYCLES` ceiling prevents infinite loops. When it's crossed, a system warning is streamed to the CLI.

---

## Architecture Principles

- **Summarizer and Tester are self-contained components** with their own files and unit tests. They accept injected dependencies (LLM, tools) and receive only the data they need as arguments. The LangGraph nodes are thin wrappers that extract the relevant data from state and delegate to these components.
- **Tester is implemented as a LangGraph subgraph** with its own internal `MessagesState` (not persisted in the main graph checkpoint). This gives it a clean tool-call loop without polluting the main graph's message history.

---

## State Changes

### New fields in `ChatbotState` (`code_monkey/graph/state.py`)

```
chat_summary: str
    Running summary of older history. Persists in checkpoint. Default: "".

last_messages: list[BaseMessage]
    Recent user+assistant messages (from last user request onward). Replace semantics —
    no operator.add annotation. Updated by the summarizer each cycle.

chat_summary_span: int
    Index into the *filtered* message list (HumanMessage + text AIMessage only)
    up to which history has already been summarized. Initial value: 0.

tester_result: TesterResult | None
    Structured outcome set by the tester node. Reset to None each turn in _make_state.
    Contains status ("passed"/"failed") and reason (empty string when passed).
    Used by the graph routing function after tester_node.

tester_iteration_count: int
    Number of orchestrator→tester cycles completed in the current user turn.
    Reset to 0 each turn in _make_state.
```

`warning_message` state field is **not needed** — warnings are streamed inline (see below).

### `TesterResult` type

Define as a TypedDict in `code_monkey/graph/nodes/tester_node.py` (or a shared types file):

```python
class TesterResult(TypedDict):
    status: Literal["passed", "failed"]
    reason: str  # empty string when passed
```

### `_make_state` updates in `agent_graph.py`

Add to the per-turn reset: `tester_result: None`, `tester_iteration_count: 0`.
(`chat_summary`, `last_messages`, `chat_summary_span` persist from checkpoint — no reset needed.)

---

## Warning Streaming Design

LangGraph 1.x provides `StreamWriter` — the built-in mechanism for nodes to emit out-of-band data into the stream without touching message state. This is the correct tool here.

### How it works

The tester node declares a `writer: StreamWriter` keyword argument. When the cycle limit is hit, it calls:
```python
writer({"kind": "warning", "content": "Max review cycles (3) reached. Stopping."})
```

`astream` switches to multi-mode streaming:
```python
async for mode, data in self._graph.astream(
    state, config=self._run_config(), stream_mode=["updates", "custom"]
):
    if mode == "custom":
        yield StreamChunk(content=data["content"], kind=data["kind"])
    elif mode == "updates":
        for msg in _visible_messages(data):
            yield StreamChunk(content=msg.content, kind="assistant")
```

`StreamChunk` is a small dataclass:
```python
@dataclass
class StreamChunk:
    content: str
    kind: Literal["assistant", "warning"] = "assistant"
```

The controller destructures by kind:
```python
async for chunk in self._graph.astream(event.text):
    if chunk.kind == "warning":
        self._ui.system_message(chunk.content)
    else:
        self._ui.assistant_message(chunk.content)
```

**Advantages over SystemMessage approach**:
- Warnings never appear in `messages` state or conversation history
- No risk of the warning being re-fed into future LLM context
- `StreamWriter` is the LangGraph-native idiom for exactly this use case
- `warning_message` state field is not needed at all

---

## New Graph Flow

```
START → (needs_mapping?) → [map_project_node →] orchestrator_node ↔ tools
orchestrator_node (no tool calls) → summarizer_node → tester_node
tester_node → orchestrator_node  (if status="failed" AND tester_iteration_count < MAX_REVIEW_CYCLES)
tester_node → END                (if status="passed" OR tester_iteration_count >= MAX_REVIEW_CYCLES)
```

When the tester hits `MAX_REVIEW_CYCLES`, it emits a custom `StreamWriter` event which surfaces as a warning chunk to the controller. No message is appended to state.

---

## Tasks

### Task 1 — Extend `ChatbotState` and `_make_state`
**Files**: `code_monkey/graph/state.py`, `code_monkey/graph/agent_graph.py`

- Add `chat_summary`, `last_messages`, `chat_summary_span`, `tester_result`, `tester_iteration_count` to `ChatbotState`.
- Define `TesterResult` TypedDict (can live in `state.py` or `tester_node.py`; if in `tester_node.py`, import it into `state.py`).
- In `_make_state`: add `tester_result: None`, `tester_iteration_count: 0`.
- Define `StreamChunk` dataclass in `agent_graph.py` (or a small `code_monkey/graph/stream_chunk.py`).

**Testable outcome**: Existing tests continue to pass. No behavioral change yet.

---

### Task 2 — `ChatSummarizer` Component + Summarizer Node
**Files**:
- `code_monkey/agents/chat_summarizer/chat_summarizer.py` (new — self-contained component)
- `code_monkey/graph/nodes/summarizer_node.py` (new — thin node wrapper)
- `tests/agents/chat_summarizer/test_chat_summarizer.py` (new)

#### `ChatSummarizer` component

```python
class ChatSummarizer:
    def __init__(self, model: BaseChatModel) -> None: ...

    async def summarize(
        self,
        messages: list[BaseMessage],
        existing_summary: str,
        chat_summary_span: int,
    ) -> tuple[str, list[BaseMessage], int]:
        """
        Returns: (updated_summary, last_messages, new_chat_summary_span)
        """
```

Internal logic:
1. Filter `messages` → keep only `HumanMessage` and `AIMessage` with content and no tool_calls. Call this `filtered`.
2. Find `last_user_idx` = index of the last `HumanMessage` in `filtered`.
3. `last_messages` = `filtered[last_user_idx:]`
4. `to_summarize` = `filtered[chat_summary_span : last_user_idx]`
5. If `to_summarize` non-empty: call LLM with `(existing_summary, to_summarize)` → updated summary.
6. Otherwise: keep `existing_summary` unchanged.
7. Return `(updated_summary, last_messages, last_user_idx)`.

#### Summarizer node (wrapper)

```python
def make_summarizer_node(summarizer: ChatSummarizer):
    async def summarizer_node(state: ChatbotState, config: RunnableConfig) -> dict:
        summary, last_msgs, span = await summarizer.summarize(
            state["messages"], state.get("chat_summary", ""), state.get("chat_summary_span", 0)
        )
        return {"chat_summary": summary, "last_messages": last_msgs, "chat_summary_span": span}
    return summarizer_node
```

**Test scenarios** (against `ChatSummarizer` directly):
- First turn: no prior summary, only one user message → last_messages = [HumanMessage], span = 0, summary unchanged.
- Multi-turn: prior summary + messages to compress → LLM called, span advances.
- Nothing new to summarize (span already at last user message): LLM not called, last_messages + span updated.
- Tool call messages filtered out correctly.

---

### Task 3 — `Tester` Component + Tester Node
**Files**:
- `code_monkey/agents/tester/tester.py` (new — self-contained component + subgraph)
- `code_monkey/graph/nodes/tester_node.py` (new — thin node wrapper + `MAX_REVIEW_CYCLES` + `TesterResult`)
- `tests/agents/tester/test_tester.py` (new)

#### `MAX_REVIEW_CYCLES` and `TesterResult`

```python
MAX_REVIEW_CYCLES = 3

class TesterResult(TypedDict):
    status: Literal["passed", "failed"]
    reason: str
```

#### `TestOutput` Pydantic model (for LLM structured output)

```python
class TestOutput(BaseModel):
    test_result: Literal["passed", "failed"]
    reason: str
```

#### `Tester` component

Implemented as a LangGraph subgraph with its own internal `MessagesState`. The subgraph is not compiled with a checkpointer (in-memory only, not persisted).

```python
class Tester:
    def __init__(self, model: BaseChatModel, bash_tool: BaseTool) -> None:
        self._subgraph = self._build_subgraph(model, bash_tool)

    async def run(
        self,
        project_context: str | None,
        chat_summary: str,
        last_messages: list[BaseMessage],
    ) -> TesterResult:
        """Run the tester subgraph and return a structured result."""
```

Subgraph structure:
- State: `MessagesState` (LangGraph built-in — just `messages` with `operator.add`)
- Node `tester_llm`: invokes `model.bind_tools([bash_tool])` on current messages
- Node `tester_tools`: `ToolNode([bash_tool])`
- Edge: `tester_llm → tester_tools` if tool_calls, else `tester_llm → structured_output_node`
- Node `structured_output_node`: invokes `model.with_structured_output(TestOutput)` on accumulated messages → returns parsed `TestOutput`

The system prompt injected into the subgraph's initial messages includes: tester role/purpose, project context, `chat_summary`, and `last_messages` formatted as a readable transcript.

`run()` returns `TesterResult(status=..., reason=...)`.

#### Feedback to orchestrator via `review_feedback`

`ChatbotState` already has `review_feedback: str | None`, designed exactly for this: "feedback set by verifier on rejection; agent reads this to revise its answer." The tester is the verifier. Rather than injecting a fake AIMessage, the tester node sets `review_feedback` to the failure reason. The orchestrator node is updated to include it in the system prompt when present.

Update to `build_system_prompt` in `orchestrator_node.py`:
```python
def build_system_prompt(project_context: str | None, review_feedback: str | None = None) -> str:
    prompt = _ROLE_DESCRIPTION
    if project_context:
        prompt += f"\n\n## Project Context\n\n{project_context}"
    if review_feedback:
        prompt += f"\n\n## Previous Attempt Failed\n\n{review_feedback}"
    return prompt
```

`review_feedback` is already reset to `None` in `_make_state` each turn, so it won't leak between user messages.

#### Tester node (wrapper)

```python
from langgraph.types import StreamWriter

def make_tester_node(tester: Tester):
    async def tester_node(state: ChatbotState, config: RunnableConfig, *, writer: StreamWriter) -> dict:
        project_mapper = (config.get("configurable") or {}).get("project_mapper")
        project_context = project_mapper.get_project_context() if project_mapper else None
        result: TesterResult = await tester.run(
            project_context, state.get("chat_summary", ""), state.get("last_messages", [])
        )
        new_count = state.get("tester_iteration_count", 0) + 1
        if result["status"] == "failed" and new_count >= MAX_REVIEW_CYCLES:
            writer({"kind": "warning", "content": f"Max review cycles ({MAX_REVIEW_CYCLES}) reached without passing. Stopping.\nLast failure: {result['reason']}"})
        return {
            "tester_result": result,
            "tester_iteration_count": new_count,
            "review_feedback": result["reason"] if result["status"] == "failed" else None,
        }
    return tester_node
```

Single return, no branching. The graph edge function handles routing. The `review_feedback` field carries the failure reason to the orchestrator's next system prompt; no message history is polluted.

**Test scenarios** (against `Tester` component directly, with mock LLM at boundary):
- Passes immediately → `TesterResult(status="passed", reason="")`
- Runs bash tool then passes → bash tool called, structured output follows
- Fails → `TesterResult(status="failed", reason="<detail>")`

**Test scenarios** for tester node wrapper (mock `writer` callable):
- Pass → `review_feedback=None`, writer not called
- Fail under limit → `review_feedback=reason`, writer not called
- Fail at limit → `review_feedback=reason`, writer called with warning dict

---

### Task 4 — NodesProvider Interface + DefaultNodesProvider + ModelConfig
**Files**: `code_monkey/graph/nodes_provider.py`, `code_monkey/graph/default_nodes_provider.py`, `code_monkey/models/model_config.py`

- Add to `NodesProvider` ABC:
  ```python
  @abstractmethod
  async def summarizer_node(self, state, config) -> dict: ...
  @abstractmethod
  async def tester_node(self, state, config) -> dict: ...
  ```
- Add to `ModelConfig`:
  ```python
  def tester_model(self) -> BaseChatModel: return get_openai_model(GPT_4O)
  def chat_summarizer_model(self) -> BaseChatModel: return get_openai_model(GPT_4O_MINI)
  ```
- In `DefaultNodesProvider.create()`:
  - `tester_bash_tool = create_bash_tool(project_root)` (separate instance from orchestrator's)
  - `chat_summarizer = ChatSummarizer(model_config.chat_summarizer_model())`
  - `tester = Tester(model_config.tester_model(), tester_bash_tool)`
  - `summarizer_node_fn = make_summarizer_node(chat_summarizer)`
  - `tester_node_fn = make_tester_node(tester)`
  - Store and expose via the respective node methods
- `configurable_fields` unchanged (tester gets `project_mapper` from config the same way orchestrator does)

**Testable outcome**: `DefaultNodesProvider.create()` succeeds; existing tests pass.

---

### Task 5 — Graph Wiring + `StreamChunk`
**File**: `code_monkey/graph/agent_graph.py`

#### `StreamChunk` dataclass

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class StreamChunk:
    content: str
    kind: Literal["assistant", "warning"] = "assistant"
```

#### `astream` signature change

```python
async def astream(self, message: str) -> AsyncIterator[StreamChunk]:
```

Mapping in the stream loop:
- `AIMessage` with content and no tool_calls → `StreamChunk(content, kind="assistant")`
- `SystemMessage` → `StreamChunk(content, kind="warning")`

#### `_build` changes

1. Add nodes: `graph.add_node("summarizer_node", ...)`, `graph.add_node("tester_node", ...)`
2. Change orchestrator conditional: `"tools"` if tool_calls, else `"summarizer_node"` (was `END`)
3. Fixed edge: `summarizer_node → tester_node`
4. Tester conditional routing:
   ```python
   graph.add_conditional_edges(
       "tester_node",
       lambda state: (
           END
           if (
               cast(ChatbotState, state)["tester_result"]["status"] == "passed"
               or cast(ChatbotState, state)["tester_iteration_count"] >= MAX_REVIEW_CYCLES
           )
           else "orchestrator_node"
       ),
   )
   ```

#### `astream` change

Switch to `stream_mode=["updates", "custom"]` and yield `StreamChunk`:
```python
async for mode, data in self._graph.astream(..., stream_mode=["updates", "custom"]):
    if mode == "custom":
        yield StreamChunk(content=data["content"], kind=data["kind"])
    elif mode == "updates":
        for _node, node_update in data.items():
            for msg in node_update.get("messages", []):
                if _is_text_ai_message(msg):
                    yield StreamChunk(content=msg.content, kind="assistant")
```

**Testable outcome**: Mermaid diagram shows new nodes; routing integration tests pass; warning chunks emitted correctly.

---

### Task 6 — Controller Update
**File**: `code_monkey/controller/controller.py`
**Tests**: `tests/controller/test_controller.py`

```python
async for chunk in self._graph.astream(event.text):
    if chunk.kind == "warning":
        self._ui.system_message(chunk.content)
    else:
        self._ui.assistant_message(chunk.content)
```

**Testable outcome**: Warning appears as `[System] Max review cycles (3) reached...` in CLI.

---

### Task 7 — MockNodesProvider + Integration Tests
**Files**: `tests/graph/mock_nodes_provider.py`, `tests/graph/test_agent_graph.py`

- Add `summarizer_node` and `tester_node` to `MockNodesProvider`.
- Default mock summarizer: returns unchanged `chat_summary`, sets `last_messages` from state, advances `chat_summary_span`.
- Default mock tester: `tester_result = TesterResult(status="passed", reason="")`, increments `tester_iteration_count`.
- Constructor param `tester_fails_times: int = 0` — tester returns failed for the first N calls, then passes.
- New graph integration tests:
  - Orchestrator finishes → summarizer → tester passes → END (no warning chunk)
  - Tester fails once → failure AIMessage → routes back → orchestrator → tester passes
  - Tester fails `MAX_REVIEW_CYCLES` times → SystemMessage warning chunk streamed → END
  - Tool call path unaffected: orchestrator → tools → orchestrator → summarizer → tester

---

## Critical Files

| File | Action |
|------|--------|
| `code_monkey/graph/state.py` | Add 5 new fields + `TesterResult` TypedDict |
| `code_monkey/graph/agent_graph.py` | `StreamChunk`, `astream` change, `_build` rewire, `_make_state` |
| `code_monkey/agents/chat_summarizer/chat_summarizer.py` | **New** — `ChatSummarizer` component |
| `code_monkey/graph/nodes/summarizer_node.py` | **New** — thin node wrapper |
| `code_monkey/agents/tester/tester.py` | **New** — `Tester` component + subgraph |
| `code_monkey/graph/nodes/tester_node.py` | **New** — thin node wrapper + `MAX_REVIEW_CYCLES` |
| `code_monkey/graph/nodes_provider.py` | Add 2 abstract methods |
| `code_monkey/graph/default_nodes_provider.py` | Wire new components and nodes |
| `code_monkey/models/model_config.py` | Add `tester_model`, `chat_summarizer_model` |
| `code_monkey/graph/nodes/orchestrator_node.py` | Update `build_system_prompt` to include `review_feedback` |
| `code_monkey/controller/controller.py` | Handle `StreamChunk.kind` |
| `tests/graph/mock_nodes_provider.py` | Add new node mocks |
| `tests/graph/test_agent_graph.py` | Add routing integration tests |
| `tests/agents/chat_summarizer/test_chat_summarizer.py` | **New** — component unit tests |
| `tests/agents/tester/test_tester.py` | **New** — component unit tests |
| `tests/graph/nodes/test_tester_node.py` | **New** — node wrapper tests |
| `tests/controller/test_controller.py` | Add warning display test |

---

## Verification

1. `uv run pytest tests/agents/chat_summarizer/test_chat_summarizer.py -v`
2. `uv run pytest tests/agents/tester/test_tester.py tests/graph/nodes/test_tester_node.py -v`
3. `uv run pytest tests/graph/test_agent_graph.py -v`
4. `uv run pytest tests/controller/test_controller.py -v`
5. `uv run ruff check . && uv run pyright`
