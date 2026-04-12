from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import StreamWriter

from code_monkey.agents.tester.tester import TesterResult
from code_monkey.graph.nodes.review_router_node import make_review_router_node
from code_monkey.graph.nodes_provider import NodesProvider
from code_monkey.graph.state import ChatbotState


class MockNodesProvider(NodesProvider):
    def __init__(
        self,
        emit_tool_call: bool = False,
        orchestrator_responses: list[str] | None = None,
        tester_fails_times: int = 0,
    ) -> None:
        self._emit_tool_call = emit_tool_call
        self._tool_call_emitted = False
        self._orchestrator_responses = orchestrator_responses or []
        self._orchestrator_call_count = 0
        self._tester_call_count = 0
        self._tester_fails_times = tester_fails_times
        self._review_router_node = make_review_router_node()

    async def map_project_node(
        self, state: ChatbotState, config: RunnableConfig
    ) -> dict:
        return {
            "messages": [AIMessage(content="[mock] project mapped")],
            "needs_mapping": False,
        }

    async def orchestrator_node(
        self, state: ChatbotState, config: RunnableConfig
    ) -> dict:
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
        if self._orchestrator_responses:
            idx = min(self._orchestrator_call_count, len(self._orchestrator_responses) - 1)
            response = self._orchestrator_responses[idx]
            self._orchestrator_call_count += 1
            return {"messages": [AIMessage(content=response)]}
        return {"messages": [AIMessage(content="[mock] orchestrator decision")]}

    async def tool_node(self, state: ChatbotState) -> dict:
        return {"messages": [AIMessage(content="[mock] tool result")]}

    async def summarizer_node(
        self, state: ChatbotState, config: RunnableConfig
    ) -> dict:
        return {
            "chat_summary": state.get("chat_summary", ""),
            "last_messages": [m for m in state.get("messages", []) if isinstance(m, HumanMessage)],
            "chat_summary_span": state.get("chat_summary_span", 0),
        }

    async def tester_node(
        self, state: ChatbotState, config: RunnableConfig, *, writer: StreamWriter
    ) -> dict:
        self._tester_call_count += 1
        if self._tester_call_count <= self._tester_fails_times:
            result = TesterResult(status="failed", reason="Mock tester failure.")
        else:
            result = TesterResult(status="passed", reason="")
        return {
            "tester_result": result,
            "review_feedback": result.reason if result.status == "failed" else None,
        }

    async def review_router_node(
        self, state: ChatbotState, config: RunnableConfig, *, writer: StreamWriter
    ) -> dict:
        return await self._review_router_node(state, config, writer=writer)
