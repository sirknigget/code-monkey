import operator
from typing import Annotated

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


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
