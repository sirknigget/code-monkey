# ADR-0001: CLI Chatbot LangGraph Architecture

**Status**: Proposed
**Date**: 2026-03-11
**Deciders**: Engineering team

---

## Background

The project currently has two agents: `web_researcher` (LangGraph-based) and `project_librarian` (direct orchestrator, no graph). The `web_researcher` uses `create_agent` from LangChain — a thin ReAct wrapper around a single LLM + tool loop with no inter-node routing, no verification step, and no human-in-the-loop capability.

A CLI chatbot requires qualitatively different behavior:

1. **Output verification** — agent responses must be reviewed before being shown to the user; a verifier node must be able to reject and send feedback back to the agent.
2. **Human clarification** — the agent must be able to pause mid-turn, ask the user a question, and resume with the answer without losing accumulated state.
3. **Bounded iteration** — without a cycle guard, the agent/verifier feedback loop could run indefinitely; a configurable `max_iterations` ceiling is required.
4. **Testability of individual concerns** — verifier logic must be independently injectable and mockable, which is not possible with a monolithic `create_agent` wrapper.

These requirements cannot be satisfied by `create_agent` alone. A custom `StateGraph` with multiple named nodes and conditional routing is the appropriate abstraction.

---

## Options

### Option A: Extend `create_agent` with post-processing

**Overview**: Wrap the existing `create_agent` output in a Python function that runs a second LLM call (the verifier) synchronously after the graph returns.

**Benefits**:
- Minimal new LangGraph surface area; reuses existing patterns.
- Simplest code change — verifier is just a function call.

**Drawbacks**:
- Verifier lives outside the graph; cannot route back to the agent as a graph edge. Feedback loops require an outer Python `while` loop that bypasses LangGraph's built-in state management and checkpointing.
- `interrupt()` for human clarification cannot be placed inside `create_agent`'s internal nodes; the only legal interrupt location would be before invocation or after return, making mid-turn clarification impossible.
- State (iteration count, review feedback) must be tracked in ad-hoc Python variables instead of the persisted graph state, breaking resumability.
- The `max_iterations` guard must be reimplemented every time the pattern is reused.

**Effort**: 1–2 days (initial), but accumulates maintenance debt rapidly.

---

### Option B: Custom `StateGraph` with named nodes and conditional edges (selected)

**Overview**: Define a `StateGraph` with three nodes — `agent_node`, `verifier_node`, `tools_node` — connected by conditional edges. State is a `TypedDict` with an `operator.add`-reduced `messages` list, plus `review_feedback` and `iteration_count` fields. The verifier node routes to `END` on approval or back to `agent_node` on rejection. The `interrupt()` function is called inside `agent_node` for human clarification.

**Benefits**:
- Each concern (agent logic, tool execution, verification, routing) lives in a discrete, testable unit.
- Verifier is injected at graph construction time — any callable matching the interface can be substituted (LLM-based, rule-based, or a `MagicMock` in tests).
- `interrupt()` + `Command(resume=...)` is the officially supported LangGraph pattern for mid-node pauses; it works correctly with the `InMemorySaver` checkpointer already used in the project.
- `max_iterations` is expressed as a graph-level constraint, visible in the routing function and enforced uniformly.
- Full compatibility with LangGraph's time-travel and persistence features.

**Drawbacks**:
- More files and types than a single-function approach.
- Developers unfamiliar with LangGraph's state-reducer contract may initially find `Annotated[list[BaseMessage], operator.add]` surprising.
- `interrupt()` must be called before any tool dispatch in the same node invocation to avoid double-execution on graph resume (documented constraint).

**Effort**: 3–4 days implementation, 1 day testing.

---

### Option C: Separate graph per turn, stateless across turns

**Overview**: Build a fresh `StateGraph` per user input, run it to completion, extract the final message, and maintain conversation history in a plain Python list outside any graph.

**Benefits**:
- No inter-turn state leakage; every graph run is isolated and trivially restartable.
- No checkpointer required, reducing operational complexity.

**Drawbacks**:
- Human clarification interrupts cannot span a graph boundary; an `interrupt()` inside a fresh graph instance cannot be resumed because no persisted checkpoint exists when the CLI prompts the user.
- Multi-turn context passed as a growing list risks prompt-length issues with no natural truncation hook inside the graph.
- Every turn re-reads all prior conversation from the state initializer — there is no incremental accumulation.
- Breaks the LangGraph programming model: graph construction overhead per turn, no benefit from the checkpoint infrastructure.

**Effort**: 2 days, but leaves the interrupt requirement unimplemented.

---

## Comparison

| Evaluation Axis | Option A (wrap create_agent) | Option B (custom StateGraph) | Option C (stateless per-turn) |
|---|---|---|---|
| Verifier as a graph node | No | Yes | No |
| Feedback loop via graph edges | No (outer while-loop) | Yes | No |
| mid-turn `interrupt()` support | No | Yes | No |
| `max_iterations` expressed in graph | No | Yes | No |
| Verifier is injectable / mockable | No | Yes | Partial |
| Resumable after interrupt | No | Yes | No |
| Consistent with LangGraph patterns | No | Yes | Partial |
| Implementation effort | 1–2 days + debt | 3–4 days | 2 days + gaps |
| Aligns with existing `InMemorySaver` | No | Yes | No |

---

## Decision

**Option B** is selected: a custom `StateGraph` with `agent_node`, `verifier_node`, and `tools_node` connected by conditional edges.

The decision is driven by three non-negotiable requirements that Option A and Option C cannot satisfy without abandoning the LangGraph programming model entirely:

1. The verifier must be a first-class graph node so that feedback routing is expressed as a graph edge rather than an outer control loop.
2. `interrupt()` must be callable inside a live node to support mid-turn clarification; this requires a checkpointed graph that persists state while the CLI prompts the user.
3. The feedback-loop ceiling (`max_iterations`) must live inside the graph's routing function so it is uniformly enforced and visible in the graph definition.

Accepting the additional upfront file count is the correct trade-off against ongoing maintenance burden and feature gaps.

---

## Consequences

### Benefits
- Agent, verifier, and tool execution are each independently testable by injecting mocks at construction time.
- The `InMemorySaver` checkpointer (already present in the project) provides interrupt resumability at no additional infrastructure cost.
- Adding new nodes (e.g., a formatter node, a memory node) is an additive graph change, not a modification of existing nodes.
- Conditional routing functions are pure Python and trivially unit-tested without a running LLM.

### Trade-offs and Risks
- **Double-execution risk on resume**: If `interrupt()` is called after a tool has already dispatched, graph resume will re-execute the same node from its beginning, causing the tool to be called twice. The design document mandates that all `interrupt()` calls occur at the top of `agent_node`, before any tool dispatch or LLM invocation. This constraint must be communicated in code comments and enforced in code review.
- **`operator.add` reducer semantics**: The `messages` field uses `operator.add` (list concatenation), which means nodes must always append to `messages` rather than replacing the entire list. Replacing the list is a silent bug — the state appears correct within a turn but drops history on the next turn. Tests must assert on the full accumulated message sequence.
- **InMemorySaver is process-local**: Checkpoints do not survive process restart. For a CLI chatbot with a single session per process lifetime, this is acceptable. If multi-session persistence is later required, swapping in a `SqliteSaver` or `PostgresSaver` is a drop-in change at graph construction time; the graph nodes are unaffected.
- **Verifier LLM cost**: The verifier adds one LLM call per agent response. With the default `max_iterations=3`, the worst case is three agent calls plus three verifier calls before the guard forces termination. Configuring a smaller or cheaper model for the verifier is the primary cost mitigation lever.

---

## Implementation Guidelines

- Depend on `BaseChatModel` from `langchain_core.language_models`, not on `ChatOpenAI` or `ChatAnthropic` directly, so the model is injectable.
- Inject the verifier callable at `build_graph()` call time; the default should be an LLM-based verifier constructed from the project's model factory.
- Express `max_iterations` as a parameter of `build_graph()` with a default of `3`.
- Use `langgraph.types.interrupt` and `langgraph.types.Command` — do not use the deprecated `NodeInterrupt` exception.
- Register `InMemorySaver` as the checkpointer when constructing the graph; every `invoke` or `stream` call must pass a `configurable={"thread_id": <id>}` config.
- Node factory functions (`make_agent_node`, `make_verifier_node`) must return callables that accept `(state: ChatbotState)` and return a `dict` of state updates, not a modified copy of the full state.

---

## Common ADR Relationships

No common ADRs exist in this repository at the time of writing. If logging conventions or error-handling patterns are standardized across agents in future, those decisions should be recorded in `ADR-COMMON-*` documents and referenced here.

---

## References

- [LangGraph Interrupts — Official Documentation](https://docs.langchain.com/oss/python/langgraph/interrupts) — canonical reference for `interrupt()` and `Command(resume=...)` usage
- [Making it easier to build human-in-the-loop agents with interrupt — LangChain Blog](https://blog.langchain.com/making-it-easier-to-build-human-in-the-loop-agents-with-interrupt/) — rationale for the `interrupt()` API design
- [Interrupts and Commands in LangGraph — DEV Community](https://dev.to/jamesbmour/interrupts-and-commands-in-langgraph-building-human-in-the-loop-workflows-4ngl) — worked examples of interrupt/Command patterns
- [Advanced LangGraph: Conditional Edges and Tool-Calling Agents — DEV Community](https://dev.to/jamesli/advanced-langgraph-implementing-conditional-edges-and-tool-calling-agents-3pdn) — conditional edge patterns and ToolNode integration
- [Mastering LangGraph State Management in 2025 — Sparkco AI](https://sparkco.ai/blog/mastering-langgraph-state-management-in-2025) — `operator.add` reducer and `Annotated` field patterns
- [LangGraph Workflows and Agents — Official Documentation](https://docs.langchain.com/oss/python/langgraph/workflows-agents) — ToolNode and agent loop design patterns
