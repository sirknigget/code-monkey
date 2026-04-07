from collections.abc import Callable, Coroutine
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from code_monkey.graph.state import ChatbotState


def make_orchestrator_node(
    model: BaseChatModel,
    tools: list[BaseTool],
) -> Callable[[ChatbotState], Coroutine[Any, Any, dict]]:
    """Return an async LangGraph node function that invokes *model* on each turn."""

    bound_model = model.bind_tools(tools)

    async def orchestrator_node(state: ChatbotState) -> dict:
        response = await bound_model.ainvoke(state["messages"])
        return {"messages": [response]}

    return orchestrator_node
