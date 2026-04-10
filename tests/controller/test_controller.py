"""Tests for the Controller CLI loop."""

from collections.abc import AsyncIterator

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from langchain_core.runnables import RunnableConfig
from langgraph.types import StreamWriter

from code_monkey.agents.tester.tester import TesterResult
from code_monkey.controller.controller import Controller
from code_monkey.graph.agent_graph import AgentGraph, StreamChunk
from code_monkey.graph.nodes.review_router_node import make_review_router_node
from code_monkey.graph.nodes_provider import NodesProvider
from code_monkey.graph.state import ChatbotState
from code_monkey.ui.protocol import Command, InputEvent


class _MockNodesProvider(NodesProvider):
    def __init__(self) -> None:
        self._review_router_node = make_review_router_node()

    async def map_project_node(
        self, state: ChatbotState, config: RunnableConfig
    ) -> dict:
        return {
            "messages": [AIMessage(content="[mock] project mapped")],
            "needs_mapping": False,
        }

    async def orchestrator_node(
        self, state: ChatbotState, config: RunnableConfig
    ) -> dict:
        return {"messages": [AIMessage(content="[mock] orchestrator decision")]}

    async def tool_node(self, state: ChatbotState) -> dict:
        return {"messages": [AIMessage(content="[mock] tool result")]}

    async def summarizer_node(
        self, state: ChatbotState, config: RunnableConfig
    ) -> dict:
        return {
            "chat_summary": state.get("chat_summary", ""),
            "last_messages": state.get("messages", []),
            "chat_summary_span": state.get("chat_summary_span", 0),
        }

    async def tester_node(
        self, state: ChatbotState, config: RunnableConfig, *, writer: StreamWriter
    ) -> dict:
        return {
            "tester_result": TesterResult(status="passed", reason=""),
            "review_feedback": None,
        }

    async def review_router_node(
        self, state: ChatbotState, config: RunnableConfig, *, writer: StreamWriter
    ) -> dict:
        return await self._review_router_node(state, config, writer=writer)


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
async def test_map_command_shows_scheduled_message():
    ui = await _run([InputEvent("/map", Command.MAP)])
    assert ("system", "Project mapping scheduled for next message.") in ui.messages


@pytest.mark.asyncio
async def test_map_then_message_triggers_remapping():
    ui = await _run(
        [InputEvent("hello"), InputEvent("/map", Command.MAP), InputEvent("remap me")]
    )
    assistant_messages = [
        content for kind, content in ui.messages if kind == "assistant"
    ]
    assert assistant_messages == [
        "[mock] project mapped",
        "[mock] orchestrator decision",
        "[mock] project mapped",
        "[mock] orchestrator decision",
    ]


@pytest.mark.asyncio
async def test_clear_then_restart_starts_fresh():
    shared = MemorySaver()
    await _run(
        [InputEvent("hello"), InputEvent("/clear", Command.CLEAR)], checkpointer=shared
    )

    ui2 = _MockUI([])
    await Controller(ui2, _make_graph(shared)).run()
    assert all(content != "Resuming previous session." for _, content in ui2.messages)


@pytest.mark.asyncio
async def test_warning_chunk_calls_system_message_not_assistant_message():
    async def _warning_astream(message: str) -> AsyncIterator[StreamChunk]:
        yield StreamChunk(content="Max review cycles reached.", kind="warning")

    graph = _make_graph()
    graph.astream = _warning_astream  # type: ignore[method-assign]

    ui = _MockUI([InputEvent("hello")])
    await Controller(ui, graph).run()

    assert ("system", "Max review cycles reached.") in ui.messages
    assert all(kind != "assistant" for kind, _ in ui.messages)
