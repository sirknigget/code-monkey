"""Unit tests for orchestrator_node helpers."""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from unittest.mock import AsyncMock, MagicMock

from code_monkey.agents.project_librarian.project_mapper import ProjectMapper
from code_monkey.graph.nodes.orchestrator_node import build_system_prompt, make_orchestrator_node
from code_monkey.graph.state import ChatbotState


# ---------------------------------------------------------------------------
# build_system_prompt
# ---------------------------------------------------------------------------


class TestBuildSystemPrompt:
    def test_includes_role_description_always(self) -> None:
        result = build_system_prompt(None)
        assert "safe and helpful coding assistant" in result

    def test_no_project_context_returns_role_only(self) -> None:
        result = build_system_prompt(None)
        assert "Project Context" not in result

    def test_project_context_appended_when_present(self) -> None:
        result = build_system_prompt("This project does X.")
        assert "safe and helpful coding assistant" in result
        assert "Project Context" in result
        assert "This project does X." in result


# ---------------------------------------------------------------------------
# make_orchestrator_node
# ---------------------------------------------------------------------------


def _make_state(messages: list) -> ChatbotState:
    return ChatbotState(
        messages=messages,
        needs_mapping=False,
        review_feedback=None,
        iteration_count=0,
    )


def _make_config(mapper: ProjectMapper | None) -> RunnableConfig:
    configurable = {}
    if mapper is not None:
        configurable["project_mapper"] = mapper
    return RunnableConfig(configurable=configurable)


class TestMakeOrchestratorNode:
    @pytest.mark.asyncio
    async def test_system_message_prepended_with_project_context(self) -> None:
        model = MagicMock()
        model.bind_tools.return_value = model
        model.ainvoke = AsyncMock(return_value=AIMessage(content="answer"))

        mapper = MagicMock(spec=ProjectMapper)
        mapper.get_project_context.return_value = "project summary here"

        node = make_orchestrator_node(model, [])
        state = _make_state([HumanMessage(content="hello")])
        config = _make_config(mapper)

        await node(state, config)

        call_messages = model.ainvoke.call_args[0][0]
        assert isinstance(call_messages[0], SystemMessage)
        assert "project summary here" in call_messages[0].content
        assert isinstance(call_messages[1], HumanMessage)

    @pytest.mark.asyncio
    async def test_system_message_without_project_context_when_no_mapper(self) -> None:
        model = MagicMock()
        model.bind_tools.return_value = model
        model.ainvoke = AsyncMock(return_value=AIMessage(content="answer"))

        node = make_orchestrator_node(model, [])
        state = _make_state([HumanMessage(content="hello")])
        config = _make_config(mapper=None)

        await node(state, config)

        call_messages = model.ainvoke.call_args[0][0]
        assert isinstance(call_messages[0], SystemMessage)
        assert "Project Context" not in call_messages[0].content

    @pytest.mark.asyncio
    async def test_system_message_without_project_context_when_mapper_returns_none(
        self,
    ) -> None:
        model = MagicMock()
        model.bind_tools.return_value = model
        model.ainvoke = AsyncMock(return_value=AIMessage(content="answer"))

        mapper = MagicMock(spec=ProjectMapper)
        mapper.get_project_context.return_value = None

        node = make_orchestrator_node(model, [])
        state = _make_state([HumanMessage(content="hello")])
        config = _make_config(mapper)

        await node(state, config)

        call_messages = model.ainvoke.call_args[0][0]
        assert isinstance(call_messages[0], SystemMessage)
        assert "Project Context" not in call_messages[0].content

    @pytest.mark.asyncio
    async def test_returns_model_response_in_messages(self) -> None:
        model = MagicMock()
        model.bind_tools.return_value = model
        model.ainvoke = AsyncMock(return_value=AIMessage(content="the response"))

        node = make_orchestrator_node(model, [])
        state = _make_state([HumanMessage(content="hi")])
        config = _make_config(mapper=None)

        result = await node(state, config)

        assert result == {"messages": [AIMessage(content="the response")]}
