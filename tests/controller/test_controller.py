"""Tests for the Controller CLI loop."""

import sqlite3

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from code_monkey.controller.controller import Controller
from code_monkey.graph.agent_graph import AgentGraph
from code_monkey.graph.nodes_provider import NodesProvider
from code_monkey.graph.state import ChatbotState
from code_monkey.ui.protocol import Command, InputEvent


class _MockNodesProvider(NodesProvider):
    def map_project_node(self, state: ChatbotState) -> dict:
        return {
            "messages": [AIMessage(content="[mock] project mapped")],
            "needs_mapping": False,
        }

    def orchestrator_node(self, state: ChatbotState) -> dict:
        return {"messages": [AIMessage(content="[mock] orchestrator decision")]}

    def tool_node(self, state: ChatbotState) -> dict:
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


def _make_graph(db_path: str) -> AgentGraph:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()
    return AgentGraph(
        _MockNodesProvider(), checkpointer=checkpointer, thread_id="session"
    )


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "checkpoints.db")


def _run(db_path: str, inputs: list[InputEvent]) -> _MockUI:
    ui = _MockUI(inputs)
    Controller(ui, _make_graph(db_path)).run()
    return ui


def test_user_input_produces_assistant_response(db_path):
    ui = _run(db_path, [InputEvent("hello")])
    assert [content for kind, content in ui.messages if kind == "assistant"] == [
        "[mock] project mapped",
        "[mock] orchestrator decision",
    ]


def test_empty_input_reprompts_without_invoking_graph(db_path):
    ui = _run(db_path, [InputEvent(""), InputEvent("   ")])
    assert all(kind != "assistant" for kind, _ in ui.messages)


def test_exit_signal_exits_cleanly(db_path):
    _run(db_path, [])  # no inputs → immediate SystemExit; must not raise


def test_clear_shows_session_cleared_message(db_path):
    ui = _run(db_path, [InputEvent("/clear", Command.CLEAR)])
    assert ("system", "Session cleared.") in ui.messages


def test_clear_then_message_still_produces_response(db_path):
    ui = _run(db_path, [InputEvent("/clear", Command.CLEAR), InputEvent("hello")])
    assert [content for kind, content in ui.messages if kind == "assistant"] == [
        "[mock] project mapped",
        "[mock] orchestrator decision",
    ]


def test_session_persists_across_restart(db_path):
    _run(db_path, [InputEvent("hello")])

    ui2 = _MockUI([])
    Controller(ui2, _make_graph(db_path)).run()
    assert ("system", "Resuming previous session.") in ui2.messages


def test_clear_then_restart_starts_fresh(db_path):
    _run(db_path, [InputEvent("hello"), InputEvent("/clear", Command.CLEAR)])

    ui2 = _MockUI([])
    Controller(ui2, _make_graph(db_path)).run()
    assert all(content != "Resuming previous session." for _, content in ui2.messages)
