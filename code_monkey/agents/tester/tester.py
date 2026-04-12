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
    "You are a software tester verifying that the assistant completed the user's request correctly. "
    "Your job is to evaluate whether the assistant did what the user actually asked for, not to force code or shell-based testing when it is unnecessary. "
    "If the user asked only for a clarification, explanation, or other conversational help, verify that the assistant provided the needed response. "
    "Use bash commands only when they are genuinely useful for checking the assistant's work, such as running relevant tests or inspecting files. "
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
        project_context: str,
        chat_summary: str,
        last_messages: list[BaseMessage],
    ) -> TesterResult:
        """Run the tester agent and return a structured result."""
        lines = [f"## Project Context\n\n{project_context}"]
        if chat_summary:
            lines.append(f"## Conversation Summary\n\n{chat_summary}")
        transcript = [
            f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
            for m in last_messages
            if isinstance(m, (HumanMessage, AIMessage))
        ]
        lines.append("## Recent Conversation\n\n" + "\n\n".join(transcript))

        prompt = "\n\n".join(lines)
        result = await self._agent.ainvoke({"messages": [HumanMessage(content=prompt)]})
        return result["structured_response"]
