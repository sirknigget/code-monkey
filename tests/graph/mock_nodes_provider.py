from langchain_core.messages import AIMessage

from code_monkey.graph.nodes_provider import NodesProvider
from code_monkey.graph.state import ChatbotState


class MockNodesProvider(NodesProvider):
    def __init__(self, emit_tool_call: bool = False) -> None:
        self._emit_tool_call = emit_tool_call
        self._tool_call_emitted = False

    async def map_project_node(self, state: ChatbotState) -> dict:
        return {
            "messages": [AIMessage(content="[mock] project mapped")],
            "needs_mapping": False,
        }

    async def orchestrator_node(self, state: ChatbotState) -> dict:
        if self._emit_tool_call and not self._tool_call_emitted:
            self._tool_call_emitted = True
            return {
                "messages": [
                    AIMessage(
                        content="[mock] tool call",
                        tool_calls=[
                            {
                                "name": "some_tool",
                                "args": {},
                                "id": "call_1",
                                "type": "tool_call",
                            }
                        ],
                    )
                ]
            }
        return {"messages": [AIMessage(content="[mock] orchestrator decision")]}

    async def tool_node(self, state: ChatbotState) -> dict:
        return {"messages": [AIMessage(content="[mock] tool result")]}
