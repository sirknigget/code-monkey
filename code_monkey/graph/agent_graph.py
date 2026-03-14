import logging
from collections.abc import Iterator
from typing import Any, cast

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.constants import END
from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from code_monkey.graph.nodes_provider import NodesProvider
from code_monkey.graph.state import ChatbotState

logger = logging.getLogger(__name__)

DEBUG = False


def _is_text_ai_message(msg: BaseMessage) -> bool:
    """Return True for AIMessages that carry visible text (no tool calls)."""
    return isinstance(msg, AIMessage) and bool(msg.content) and not msg.tool_calls


class _DebugCallbackHandler(BaseCallbackHandler):
    def on_chain_start(
        self, serialized: dict[str, Any] | None, inputs: dict[str, Any], **kwargs: Any
    ) -> None:
        name = (serialized or {}).get("name") or kwargs.get("name", "unknown")
        logger.debug("node start: %s | inputs: %s", name, inputs)

    def on_chain_end(self, outputs: dict[str, Any], **kwargs: Any) -> None:
        logger.debug("node end | outputs: %s", outputs)

    def on_chain_error(self, error: BaseException, **kwargs: Any) -> None:
        logger.debug("node error: %s", error)


class AgentGraph:
    def __init__(
        self,
        nodes_provider: NodesProvider,
        checkpointer: BaseCheckpointSaver,
        thread_id: str = "session",
    ) -> None:
        self._checkpointer = checkpointer
        self._thread_config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        self._graph = self._build(nodes_provider, checkpointer)

    def invoke(self, message: str, force_mapping: bool = False) -> dict:
        return self._graph.invoke(
            self._initial_state(message, force_mapping),
            config=self._run_config(),
        )

    def stream(self, message: str, force_mapping: bool = False) -> Iterator[str]:
        """Yield text content of each AI message as the graph runs node by node."""
        for update in self._graph.stream(
            self._initial_state(message, force_mapping),
            config=self._run_config(),
            stream_mode="updates",
        ):
            for _node, node_update in update.items():
                for msg in node_update.get("messages", []):
                    if _is_text_ai_message(msg):
                        yield msg.content

    def get_history(self) -> Iterator[tuple[str, str]]:
        """Yield (role, content) pairs from the persisted checkpoint.

        role is "user" for HumanMessages and "assistant" for text AIMessages.
        Tool-call AIMessages are omitted.
        """
        checkpoint = self._checkpointer.get(self._thread_config)
        if checkpoint is None:
            return
        for msg in checkpoint.get("channel_values", {}).get("messages", []):
            if isinstance(msg, HumanMessage) and msg.content:
                yield "user", msg.content
            elif _is_text_ai_message(msg):
                yield "assistant", msg.content

    def has_checkpoint(self) -> bool:
        """Return True if a persisted checkpoint exists for this thread."""
        return self._checkpointer.get(self._thread_config) is not None

    def get_mermaid_diagram(self) -> str:
        return self._graph.get_graph().draw_mermaid()

    def _initial_state(self, message: str, force_mapping: bool) -> ChatbotState:
        is_new_session = self._checkpointer.get(self._thread_config) is None
        return {
            "messages": [HumanMessage(content=message)],
            "needs_mapping": force_mapping or is_new_session,
            "review_feedback": None,
            "iteration_count": 0,
        }

    def _run_config(self) -> RunnableConfig:
        return {
            **self._thread_config,
            **({("callbacks"): [_DebugCallbackHandler()]} if DEBUG else {}),
        }

    @staticmethod
    def _build(
        nodes_provider: NodesProvider, checkpointer: BaseCheckpointSaver
    ) -> CompiledStateGraph:
        graph = StateGraph(ChatbotState)

        graph.add_node("map_project_node", nodes_provider.map_project_node)
        graph.add_node("orchestrator_node", nodes_provider.orchestrator_node)
        graph.add_node("tools", nodes_provider.tool_node)

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
                "tools" if cast(ChatbotState, state)["messages"][-1].tool_calls else END
            ),
        )
        graph.add_edge("tools", "orchestrator_node")

        return graph.compile(checkpointer=checkpointer)
