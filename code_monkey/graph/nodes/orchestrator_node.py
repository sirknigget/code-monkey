from collections.abc import Callable, Coroutine
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool

from code_monkey.agents.project_librarian.project_mapper import ProjectMapper
from code_monkey.graph.state import ChatbotState

_ROLE_DESCRIPTION = (
    "You are a safe and helpful coding assistant. "
    "You help users understand, navigate, and perform end-to-end tasks in their codebase."
    "Your initial shell terminal is inside the root of the codebase."
)


def build_system_prompt(project_context: str | None, review_feedback: str | None = None) -> str:
    """Build the system prompt from role description, optional project context, and review feedback."""
    prompt = _ROLE_DESCRIPTION
    if project_context:
        prompt += f"\n\n## Project Context\n\n{project_context}"
    if review_feedback:
        prompt += f"\n\n## Previous Attempt Failed\n\n{review_feedback}"
    return prompt


def make_orchestrator_node(
    model: BaseChatModel,
    tools: list[BaseTool],
) -> Callable[[ChatbotState, RunnableConfig], Coroutine[Any, Any, dict]]:
    """Return an async LangGraph node function that invokes *model* on each turn."""

    bound_model = model.bind_tools(tools)

    async def orchestrator_node(state: ChatbotState, config: RunnableConfig) -> dict:
        project_mapper: ProjectMapper | None = (config.get("configurable") or {}).get(
            "project_mapper"
        )
        project_context = (
            project_mapper.get_project_context() if project_mapper else None
        )
        review_feedback = state.get("review_feedback")
        system_prompt = build_system_prompt(project_context, review_feedback)
        messages = [SystemMessage(content=system_prompt), *state["messages"]]
        response = await bound_model.ainvoke(messages)
        return {"messages": [response]}

    return orchestrator_node
