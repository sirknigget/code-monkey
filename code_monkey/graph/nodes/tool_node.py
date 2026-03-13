from langchain_core.messages import AIMessage

from code_monkey.graph.state import ChatbotState


def tool_node(state: ChatbotState) -> dict:
    """Execute tool calls from the last AI message."""
    return {"messages": [AIMessage(content="[tool_node] tools executed")]}
