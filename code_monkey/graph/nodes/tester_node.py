from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.types import StreamWriter

from code_monkey.agents.tester.tester import Tester, TesterResult
from code_monkey.graph.state import ChatbotState
from code_monkey.utils.log_utils import get_formatted_logger

logger = get_formatted_logger(__name__)

MAX_REVIEW_CYCLES = 3


def make_tester_node(tester: Tester) -> Any:
    async def tester_node(
        state: ChatbotState, config: RunnableConfig, *, writer: StreamWriter
    ) -> dict:
        project_mapper = (config.get("configurable") or {}).get("project_mapper")
        project_context = project_mapper.get_project_context() if project_mapper else None
        logger.debug(
            "Tester node: running review cycle %s with %s last messages",
            state.get("tester_iteration_count", 0) + 1,
            len(state.get("last_messages", [])),
        )
        result: TesterResult = await tester.run(
            project_context,
            state.get("chat_summary", ""),
            state.get("last_messages", []),
        )
        new_count = state.get("tester_iteration_count", 0) + 1
        logger.debug(
            "Tester node: result=%s at cycle=%s",
            result.status,
            new_count,
        )
        if result.status == "failed" and new_count >= MAX_REVIEW_CYCLES:
            logger.debug("Tester node: max review cycles reached, streaming warning")
            writer(
                {
                    "kind": "warning",
                    "content": (
                        f"Max review cycles ({MAX_REVIEW_CYCLES}) reached without passing. "
                        f"Stopping.\nLast failure: {result.reason}"
                    ),
                }
            )
        return {
            "tester_result": result,
            "tester_iteration_count": new_count,
            "review_feedback": result.reason if result.status == "failed" else None,
        }

    return tester_node
