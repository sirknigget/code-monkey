from code_monkey.graph.state import ChatbotState


def tool_node(state: ChatbotState) -> dict:
    """Execute tool calls from the last AI message."""
    print("[tool_node] executing tools")
    return {}
