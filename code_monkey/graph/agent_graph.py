from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, cast

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.constants import END
from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from code_monkey.graph.debug_callback import DebugCallbackHandler
from code_monkey.graph.default_nodes_provider import DefaultNodesProvider
from code_monkey.graph.nodes.tester_node import MAX_REVIEW_CYCLES
from code_monkey.graph.nodes_provider import NodesProvider
from code_monkey.graph.state import ChatbotState
from code_monkey.models.model_config import ModelConfig
from code_monkey.utils.log_utils import get_formatted_logger

logger = get_formatted_logger(__name__)

DEBUG = False


@dataclass
class StreamChunk:
    content: str
    kind: Literal["assistant", "warning"] = "assistant"


def _is_text_ai_message(msg: BaseMessage) -> bool:
    """Return True for AIMessages that carry visible text (no tool calls)."""
    return isinstance(msg, AIMessage) and bool(msg.content) and not msg.tool_calls


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
        thread_id: str = "session",
    ) -> "AgentGraph":
        """Async factory: creates all nodes and tools, returns AgentGraph."""
        nodes_provider = await DefaultNodesProvider.create(project_root, model_config)
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
        async for mode, data in self._graph.astream(  # type: ignore[misc]
            state,
            config=self._run_config(),
            stream_mode=["updates", "custom"],
        ):
            chunk_data: dict = data  # type: ignore[assignment]
            if mode == "custom":
                yield StreamChunk(content=chunk_data["content"], kind=chunk_data["kind"])
            elif mode == "updates":
                for _node, node_update in chunk_data.items():
                    for msg in node_update.get("messages", []):
                        if _is_text_ai_message(msg):
                            yield StreamChunk(content=msg.content, kind="assistant")

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
            elif _is_text_ai_message(msg) and isinstance(msg.content, str):
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
        }
        if is_new_session:
            state["needs_mapping"] = True
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
        graph.add_conditional_edges(
            "tester_node",
            lambda state: (
                END
                if (
                    (cast(ChatbotState, state)["tester_result"] or {}).get("status") == "passed"
                    or cast(ChatbotState, state)["tester_iteration_count"] >= MAX_REVIEW_CYCLES
                )
                else "orchestrator_node"
            ),
        )

        return graph.compile(checkpointer=checkpointer)
