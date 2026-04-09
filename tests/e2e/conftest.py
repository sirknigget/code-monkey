"""Shared fixtures and helpers for e2e tests.

All e2e tests call setup() from main.py with:
  - MockUI: captures all UI calls and provides finite inputs
  - A SQLite checkpointer factory pointed at tmp_path (avoids ~/.codemonkey)
  - FakeModelConfig: returns deterministic fake LLMs that emit real tool calls

DefaultNodesProvider runs as-is (including Playwright). Only the LLMs are faked;
the tool calls they emit are executed by the real ToolNode against the real filesystem.
"""

from pathlib import Path
from typing import Any

import aiosqlite
import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import PrivateAttr

from code_monkey.graph.checkpointer import CheckpointerResult
from code_monkey.main import setup
from code_monkey.models.model_config import ModelConfig
from code_monkey.ui.protocol import InputEvent


# ---------------------------------------------------------------------------
# Fake LLM
# ---------------------------------------------------------------------------


class FakeChatModel(BaseChatModel):
    """Cycles through a list of AIMessage (or str) responses deterministically.

    bind_tools() delegates to Runnable.bind() so the real tool schema is preserved
    in kwargs — the model simply ignores it and returns its preset response.
    """

    responses: list[Any]
    _call_count: int = PrivateAttr(default=0)

    def bind_tools(self, tools, **kwargs):
        return self.bind(tools=tools, **kwargs)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        idx = self._call_count % len(self.responses)
        self._call_count += 1
        response = self.responses[idx]
        if isinstance(response, str):
            response = AIMessage(content=response)
        return ChatResult(generations=[ChatGeneration(message=response)])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._generate(messages, stop, run_manager, **kwargs)

    @property
    def _llm_type(self) -> str:
        return "fake"


# ---------------------------------------------------------------------------
# Tool call constructors
# ---------------------------------------------------------------------------


def write_file_call(file_path: str, text: str, call_id: str = "c1") -> AIMessage:
    """AIMessage that triggers a real write_file tool call."""
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "write_file",
                "args": {"file_path": file_path, "text": text},
                "id": call_id,
                "type": "tool_call",
            }
        ],
    )


def read_file_call(file_path: str, call_id: str = "c1") -> AIMessage:
    """AIMessage that triggers a real read_file tool call."""
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "read_file",
                "args": {"file_path": file_path},
                "id": call_id,
                "type": "tool_call",
            }
        ],
    )


def web_search_call(query: str, call_id: str = "c1") -> AIMessage:
    """AIMessage that triggers a real web_search tool call (via WebResearcher)."""
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "web_search",
                "args": {"query": query, "thread_id": ""},
                "id": call_id,
                "type": "tool_call",
            }
        ],
    )


# ---------------------------------------------------------------------------
# Fake ModelConfig
# ---------------------------------------------------------------------------


class FakeModelConfig(ModelConfig):
    """Injects FakeChatModel for all model roles.

    Args:
        orchestrator_responses: Responses the orchestrator returns in order.
            Typically alternates tool_call → final_text → tool_call → final_text…
    """

    def __init__(self, orchestrator_responses: list | None = None) -> None:
        self._orchestrator_responses: list = orchestrator_responses or [
            "Task completed."
        ]

    def orchestrator_model(self) -> BaseChatModel:
        return FakeChatModel(responses=self._orchestrator_responses)

    def summarizer_model(self) -> BaseChatModel:
        return FakeChatModel(responses=["Module summary."])

    def web_researcher_model(self) -> BaseChatModel:
        # Returns text directly so WebResearcher terminates without Playwright calls.
        return FakeChatModel(responses=["Web research results."])


# ---------------------------------------------------------------------------
# Mock UI
# ---------------------------------------------------------------------------


class MockUI:
    """Test double for ChatbotUI. Records all calls; finite inputs cause clean exit."""

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

    def assistant_messages(self) -> list[str]:
        return [content for kind, content in self.messages if kind == "assistant"]

    def system_messages(self) -> list[str]:
        return [content for kind, content in self.messages if kind == "system"]


# ---------------------------------------------------------------------------
# Session runner
# ---------------------------------------------------------------------------


def make_sqlite_checkpointer_factory(db_path: Path):
    """Return a CheckpointerFactory backed by AsyncSqliteSaver at db_path."""

    async def factory() -> CheckpointerResult:
        conn = await aiosqlite.connect(str(db_path))
        saver = AsyncSqliteSaver(conn)
        await saver.setup()
        return CheckpointerResult(checkpointer=saver)

    return factory


async def run_session(
    project_root: Path,
    inputs: list[InputEvent],
    db_path: Path,
    model_config: ModelConfig | None = None,
) -> MockUI:
    """Run one setup() session and return the MockUI with all recorded messages."""
    ui = MockUI(inputs)
    await setup(
        project_root=str(project_root),
        ui=ui,
        checkpointer_factory=make_sqlite_checkpointer_factory(db_path),
        model_config=model_config or FakeModelConfig(),
    )
    return ui


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """A temporary directory representing the project root under test."""
    d = tmp_path / "project"
    d.mkdir()
    return d


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Path to the SQLite checkpoint database for a test."""
    return tmp_path / "checkpoints.db"
