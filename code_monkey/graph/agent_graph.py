from collections.abc import AsyncIterator
from typing import Any, cast

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.constants import END
from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StreamPart

from code_monkey.graph.debug_callback import DebugCallbackHandler
from code_monkey.graph.default_nodes_provider import DefaultNodesProvider
from code_monkey.graph.nodes_provider import NodesProvider
from code_monkey.graph.state import ChatbotState
from code_monkey.graph.stream_types import StreamChunk
from code_monkey.graph.streaming import is_visible_ai_message, stream_chunks_from_part
from code_monkey.mcp.loader import MCPServerSessionHandle
from code_monkey.models.model_config import ModelConfig
from code_monkey.utils.log_utils import get_formatted_logger

logger = get_formatted_logger(__name__)

DEBUG = False


class AgentGraph:
    def __init__(
        self,
        nodes_provider: NodesProvider,
        checkpointer: BaseCheckpointSaver,
        thread_id: str = "session",
    ) -> None:
        self._nodes_provider = nodes_provider
        self._checkpointer = checkpointer
        self._thread_id = thread_id
        self._thread_config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        self._graph = self._build(nodes_provider, checkpointer)

    @classmethod
    async def create(
        cls,
        checkpointer: BaseCheckpointSaver,
        project_root: str,
        model_config: ModelConfig,
        mcp_sessions: list[MCPServerSessionHandle] | None = None,
        thread_id: str = "session",
    ) -> "AgentGraph":
        """Async factory: creates all nodes and tools, returns AgentGraph."""
        nodes_provider = await DefaultNodesProvider.create(
            project_root,
            model_config,
            mcp_sessions=mcp_sessions,
        )
        return cls(nodes_provider, checkpointer, thread_id)

    async def teardown(self) -> None:
        """Release resources held by the graph (e.g. Playwright browser)."""
        await self._nodes_provider.teardown()

    async def trigger_mapping(self) -> None:
        """Update graph state to trigger project re-mapping on the next astream call."""
        await self._graph.aupdate_state(self._thread_config, {"needs_mapping": True})

    async def astream(self, message: str) -> AsyncIterator[StreamChunk]:
        """Stream visible AI messages and warning chunks as the graph runs."""
        is_new_session = (
            await self._checkpointer.aget_tuple(self._thread_config) is None
        )
        state = self._make_state(message, is_new_session)
        stream = cast(
            AsyncIterator[StreamPart[Any, Any]],
            self._graph.astream(
                state,
                config=self._run_config(),
                stream_mode=["updates", "custom"],
                version="v2",
            ),
        )
        async for part in stream:
            for chunk in stream_chunks_from_part(part):
                yield chunk

    async def aget_history(self) -> AsyncIterator[tuple[str, str]]:
        """Yield (role, content) pairs from the persisted checkpoint."""
        checkpoint = await self._checkpointer.aget(self._thread_config)
        if checkpoint is None:
            return
        for msg in checkpoint.get("channel_values", {}).get("messages", []):
            if (
                isinstance(msg, HumanMessage)
                and isinstance(msg.content, str)
                and msg.content
            ):
                yield "user", msg.content
            elif is_visible_ai_message(msg) and isinstance(msg.content, str):
                yield "assistant", msg.content

    async def ahas_checkpoint(self) -> bool:
        """Return True if a persisted checkpoint exists."""
        return await self._checkpointer.aget_tuple(self._thread_config) is not None

    async def aclear(self) -> None:
        """Delete the persisted checkpoint for this thread."""
        await self._checkpointer.adelete_thread(self._thread_id)

    def get_mermaid_diagram(self) -> str:
        return self._graph.get_graph().draw_mermaid()

    def _make_state(self, message: str, is_new_session: bool) -> dict:
        state: dict = {
            "messages": [HumanMessage(content=message)],
            "review_feedback": None,
            "iteration_count": 0,
            "tester_result": None,
            "tester_iteration_count": 0,
            "retry_review": False,
        }
        if is_new_session:
            state["needs_mapping"] = True
            state["chat_summary"] = ""
            state["last_messages"] = []
            state["chat_summary_span"] = 0
        return state

    def _run_config(self) -> RunnableConfig:
        config: RunnableConfig = {
            "recursion_limit": 100,
            "configurable": {
                "thread_id": self._thread_id,
                **self._nodes_provider.configurable_fields(),
            },
        }
        if DEBUG:
            config["callbacks"] = [DebugCallbackHandler()]
        return config

    @staticmethod
    def _build(
        nodes_provider: NodesProvider, checkpointer: BaseCheckpointSaver
    ) -> CompiledStateGraph:
        graph = StateGraph(ChatbotState)

        graph.add_node("map_project_node", nodes_provider.map_project_node)
        graph.add_node("orchestrator_node", nodes_provider.orchestrator_node)
        graph.add_node("tools", nodes_provider.tool_node)
        graph.add_node("summarizer_node", nodes_provider.summarizer_node)
        graph.add_node("tester_node", nodes_provider.tester_node)
        graph.add_node("review_router_node", nodes_provider.review_router_node)

        graph.add_conditional_edges(
            START,
            lambda state: (
                "map_project_node"
                if cast(ChatbotState, state)["needs_mapping"]
                else "orchestrator_node"
            ),
        )
        graph.add_edge("map_project_node", "orchestrator_node")
        graph.add_conditional_edges(
            "orchestrator_node",
            lambda state: (
                "tools"
                if cast(AIMessage, cast(ChatbotState, state)["messages"][-1]).tool_calls
                else "summarizer_node"
            ),
        )
        graph.add_edge("tools", "orchestrator_node")
        graph.add_edge("summarizer_node", "tester_node")
        graph.add_edge("tester_node", "review_router_node")

        graph.add_conditional_edges(
            "review_router_node",
            lambda state: (
                "orchestrator_node" if cast(ChatbotState, state)["retry_review"] else END
            ),
        )

        return graph.compile(checkpointer=checkpointer)
