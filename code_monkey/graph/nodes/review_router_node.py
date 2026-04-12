from collections.abc import Callable, Coroutine
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.types import StreamWriter

from code_monkey.graph.review_policy import MAX_REVIEW_CYCLES
from code_monkey.graph.state import ChatbotState


def make_review_router_node(
    max_review_cycles: int = MAX_REVIEW_CYCLES,
) -> Callable[..., Coroutine[Any, Any, dict]]:
    async def review_router_node(
        state: ChatbotState, config: RunnableConfig, *, writer: StreamWriter
    ) -> dict:
        result = state["tester_result"]
        assert result is not None, "tester_result must be set before review routing"
        if result.status == "passed":
            return {"retry_review": False}

        new_count = state["tester_iteration_count"] + 1
        if new_count >= max_review_cycles:
            writer(
                {
                    "kind": "warning",
                    "content": (
                        f"Max review cycles ({max_review_cycles}) reached without passing. "
                        f"Stopping.\nLast failure: {result.reason}"
                    ),
                }
            )
            return {
                "tester_iteration_count": new_count,
                "retry_review": False,
            }

        return {
            "tester_iteration_count": new_count,
            "retry_review": True,
        }

    return review_router_node
