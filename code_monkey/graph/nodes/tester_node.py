from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.types import StreamWriter

from code_monkey.agents.tester.tester import Tester, TesterResult
from code_monkey.graph.state import ChatbotState
from code_monkey.utils.log_utils import get_formatted_logger

logger = get_formatted_logger(__name__)


def make_tester_node(tester: Tester) -> Any:
    async def tester_node(
        state: ChatbotState, config: RunnableConfig, *, writer: StreamWriter
    ) -> dict:
        project_mapper = (config.get("configurable") or {}).get("project_mapper")
        project_context = project_mapper.get_project_context() if project_mapper else None
        logger.debug(
            "Running tester with %s last messages",
            len(state.get("last_messages", [])),
        )
        result: TesterResult = await tester.run(
            project_context,
            state.get("chat_summary", ""),
            state.get("last_messages", []),
        )
        logger.debug("Tester result=%s", result.status)
        return {
            "tester_result": result,
            "review_feedback": result.reason if result.status == "failed" else None,
        }

    return tester_node
