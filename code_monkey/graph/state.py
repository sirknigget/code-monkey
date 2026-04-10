import operator
from typing import Annotated

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict

from code_monkey.agents.tester.tester import TesterResult


class ChatbotState(TypedDict):
    # Append-only message history. operator.add concatenates new messages
    # onto the existing list; nodes must NEVER replace this field wholesale.
    messages: Annotated[list[BaseMessage], operator.add]

    # Feedback text set by verifier_node on rejection; cleared (set to None)
    # when the verifier approves. agent_node reads this to revise its answer.
    review_feedback: str | None

    # Number of complete agent→verifier cycles in the current user turn.
    # Incremented by agent_node at entry. Checked in the verifier routing
    # function to enforce the max_iterations ceiling.
    iteration_count: int

    # When True, the graph routes through map_project_node before the
    # orchestrator so the project context is refreshed first.
    needs_mapping: bool

    # Running summary of older history. Persists in checkpoint.
    chat_summary: str

    # Recent user+assistant messages (from last user request onward).
    # Replace semantics (no operator.add annotation). Updated by the summarizer each cycle.
    last_messages: list[BaseMessage]

    # Index into the filtered message list (HumanMessage + text AIMessage only)
    # up to which history has already been summarized.
    chat_summary_span: int

    # Structured outcome set by the tester node. Reset to None each turn.
    tester_result: TesterResult | None

    # Number of orchestrator→tester cycles completed in the current user turn.
    # Reset to 0 each turn.
    tester_iteration_count: int

    # Whether the graph should route back to the orchestrator after review routing.
    # Set by review_router_node and reset each turn.
    retry_review: bool
