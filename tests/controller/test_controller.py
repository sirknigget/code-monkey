"""Tests for the Controller CLI loop."""

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from langchain_core.runnables import RunnableConfig

from code_monkey.controller.controller import Controller
from code_monkey.graph.agent_graph import AgentGraph
from code_monkey.graph.nodes_provider import NodesProvider
from code_monkey.graph.state import ChatbotState
from code_monkey.ui.protocol import Command, InputEvent


class _MockNodesProvider(NodesProvider):
    async def map_project_node(
        self, state: ChatbotState, config: RunnableConfig
    ) -> dict:
        return {
            "messages": [AIMessage(content="[mock] project mapped")],
            "needs_mapping": False,
        }

    async def orchestrator_node(self, state: ChatbotState) -> dict:
        return {"messages": [AIMessage(content="[mock] orchestrator decision")]}

    async def tool_node(self, state: ChatbotState) -> dict:
        return {"messages": [AIMessage(content="[mock] tool result")]}


class _MockUI:
    def __init__(self, inputs: list[InputEvent]) -> None:
        self._inputs = iter(inputs)
        self.messages: list[tuple[str, str]] = []

    def get_input(self, prompt: str) -> InputEvent:
        try:
            return next(self._inputs)
        except StopIteration:
            raise SystemExit

    def user_message(self, content: str) -> None:
        self.messages.append(("user", content))

    def assistant_message(self, content: str) -> None:
        self.messages.append(("assistant", content))

    def system_message(self, content: str) -> None:
        self.messages.append(("system", content))

    def show_error(self, text: str) -> None:
        self.messages.append(("error", text))


def _make_graph(checkpointer: MemorySaver | None = None) -> AgentGraph:
    return AgentGraph(
        _MockNodesProvider(),
        checkpointer=checkpointer or MemorySaver(),
        thread_id="session",
    )


async def _run(
    inputs: list[InputEvent], checkpointer: MemorySaver | None = None
) -> _MockUI:
    ui = _MockUI(inputs)
    await Controller(ui, _make_graph(checkpointer)).run()
    return ui


@pytest.mark.asyncio
async def test_user_input_produces_assistant_response():
    ui = await _run([InputEvent("hello")])
    assert [content for kind, content in ui.messages if kind == "assistant"] == [
        "[mock] project mapped",
        "[mock] orchestrator decision",
    ]


@pytest.mark.asyncio
async def test_empty_input_reprompts_without_invoking_graph():
    ui = await _run([InputEvent(""), InputEvent("   ")])
    assert all(kind != "assistant" for kind, _ in ui.messages)


@pytest.mark.asyncio
async def test_exit_signal_exits_cleanly():
    await _run([])  # no inputs → immediate SystemExit; must not raise


@pytest.mark.asyncio
async def test_clear_shows_session_cleared_message():
    ui = await _run([InputEvent("/clear", Command.CLEAR)])
    assert ("system", "Session cleared.") in ui.messages


@pytest.mark.asyncio
async def test_clear_then_message_still_produces_response():
    ui = await _run([InputEvent("/clear", Command.CLEAR), InputEvent("hello")])
    assert [content for kind, content in ui.messages if kind == "assistant"] == [
        "[mock] project mapped",
        "[mock] orchestrator decision",
    ]


@pytest.mark.asyncio
async def test_session_persists_across_restart():
    shared = MemorySaver()
    await _run([InputEvent("hello")], checkpointer=shared)

    ui2 = _MockUI([])
    await Controller(ui2, _make_graph(shared)).run()
    assert ("system", "Resuming previous session.") in ui2.messages


@pytest.mark.asyncio
async def test_clear_then_restart_starts_fresh():
    shared = MemorySaver()
    await _run(
        [InputEvent("hello"), InputEvent("/clear", Command.CLEAR)], checkpointer=shared
    )

    ui2 = _MockUI([])
    await Controller(ui2, _make_graph(shared)).run()
    assert all(content != "Resuming previous session." for _, content in ui2.messages)
