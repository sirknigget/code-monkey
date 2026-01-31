def last_message_content(state) -> str:
    return state["messages"][-1].text