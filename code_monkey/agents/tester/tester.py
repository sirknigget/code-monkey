from typing import Literal

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel


class TesterResult(BaseModel):
    status: Literal["passed", "failed"]
    reason: str = ""


_SYSTEM_PROMPT = (
    "You are a software tester verifying that the assistant completed the requested task correctly. "
    "Run bash commands to verify the work (run tests, check files, etc.); bash commands run in the project working directory by default. "
    "Then return your verdict."
)


class Tester:
    def __init__(self, model: BaseChatModel, bash_tool: BaseTool) -> None:
        self._agent = create_agent(
            model=model,
            tools=[bash_tool],
            system_prompt=_SYSTEM_PROMPT,
            response_format=TesterResult,
        )

    async def run(
        self,
        project_context: str | None,
        chat_summary: str,
        last_messages: list[BaseMessage],
    ) -> TesterResult:
        """Run the tester agent and return a structured result."""
        lines: list[str] = []
        if project_context:
            lines.append(f"## Project Context\n\n{project_context}")
        if chat_summary:
            lines.append(f"## Conversation Summary\n\n{chat_summary}")
        transcript = [
            f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
            for m in last_messages
            if isinstance(m, (HumanMessage, AIMessage))
        ]
        if transcript:
            lines.append("## Recent Conversation\n\n" + "\n\n".join(transcript))

        prompt = "\n\n".join(lines)
        result = await self._agent.ainvoke({"messages": [HumanMessage(content=prompt)]})
        return result["structured_response"]
