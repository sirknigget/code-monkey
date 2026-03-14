"""Controller: owns the CLI run loop and wires ChatbotUI to AgentGraph."""

from __future__ import annotations

from code_monkey.graph.agent_graph import AgentGraph
from code_monkey.ui.protocol import ChatbotUI, Command


class Controller:
    def __init__(self, ui: ChatbotUI, graph: AgentGraph) -> None:
        self._ui = ui
        self._graph = graph
        if self._graph.has_checkpoint():
            self._replay_history()

    def _replay_history(self) -> None:
        for role, content in self._graph.get_history():
            if role == "user":
                self._ui.user_message(content)
            else:
                self._ui.assistant_message(content)
        self._ui.system_message("Resuming previous session.")

    def run(self) -> None:
        """Run the CLI loop until the user signals exit."""
        while True:
            try:
                event = self._ui.get_input("You: ")
            except SystemExit:
                return

            if event.command == Command.CLEAR:
                self._graph.clear()
                self._ui.system_message("Session cleared.")
                continue

            if not event.text.strip():
                continue

            for content in self._graph.stream(event.text):
                self._ui.assistant_message(content)
