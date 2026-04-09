import operator
from typing import Annotated, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel
from typing_extensions import TypedDict


class TesterResult(BaseModel):
    status: Literal["passed", "failed"]
    reason: str = ""


TESTER_SYSTEM_PROMPT = """You are a software tester verifying that the assistant completed the requested task correctly.

Run bash commands to verify the work (run tests, check files, etc.), then return your verdict."""


class TesterState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    test_output: TesterResult | None


class Tester:
    def __init__(self, model: BaseChatModel, bash_tool: BaseTool) -> None:
        self._model = model
        self._bash_tool = bash_tool
        self._subgraph = self._build_subgraph(model, bash_tool)

    async def run(
        self,
        project_context: str | None,
        chat_summary: str,
        last_messages: list[BaseMessage],
    ) -> TesterResult:
        """Run the tester subgraph and return a structured result."""
        system_content = TESTER_SYSTEM_PROMPT
        if project_context:
            system_content += f"\n\n## Project Context\n\n{project_context}"
        if chat_summary:
            system_content += f"\n\n## Conversation Summary\n\n{chat_summary}"

        transcript_lines = []
        for msg in last_messages:
            if isinstance(msg, HumanMessage):
                transcript_lines.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                transcript_lines.append(f"Assistant: {msg.content}")
        if transcript_lines:
            system_content += "\n\n## Recent Conversation\n\n" + "\n\n".join(transcript_lines)

        final_state = await self._subgraph.ainvoke(
            {"messages": [SystemMessage(content=system_content)], "test_output": None}
        )
        return final_state["test_output"]

    def _build_subgraph(self, model: BaseChatModel, bash_tool: BaseTool):
        bound_model = model.bind_tools([bash_tool], response_format=TesterResult)

        async def tester_llm(state: TesterState) -> dict:
            response = await bound_model.ainvoke(state["messages"])
            return {"messages": [response]}

        async def extract_result(state: TesterState) -> dict:
            last = state["messages"][-1]
            return {"test_output": TesterResult.model_validate_json(str(last.content))}

        def should_continue(state: TesterState) -> str:
            last = state["messages"][-1]
            if isinstance(last, AIMessage) and last.tool_calls:
                return "tester_tools"
            return "extract_result"

        graph = StateGraph(TesterState)
        graph.add_node("tester_llm", tester_llm)
        graph.add_node("tester_tools", ToolNode([bash_tool]))
        graph.add_node("extract_result", extract_result)

        graph.set_entry_point("tester_llm")
        graph.add_conditional_edges("tester_llm", should_continue)
        graph.add_edge("tester_tools", "tester_llm")
        graph.add_edge("extract_result", END)

        return graph.compile()
