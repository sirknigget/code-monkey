from code_monkey.graph.state import ChatbotState


def orchestrator_node(state: ChatbotState) -> dict:
    """Route or coordinate between other nodes."""
    print("[orchestrator_node] orchestrating")
    return {}
