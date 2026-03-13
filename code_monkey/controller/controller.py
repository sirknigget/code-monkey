"""Controller: owns the CLI run loop and wires ChatbotUI to AgentGraph."""

from __future__ import annotations

import os
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from code_monkey.graph.agent_graph import AgentGraph
from code_monkey.graph.nodes_provider import DefaultNodesProvider
from code_monkey.ui.protocol import ChatbotUI, Command

_DEFAULT_DB_PATH = ".codemonkey/checkpoints.db"
_THREAD_ID = "session"


def _make_checkpointer() -> SqliteSaver:
    db_path = os.environ.get("CODEMONKEY_DB_PATH", _DEFAULT_DB_PATH)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()
    return checkpointer


class Controller:
    def __init__(self, ui: ChatbotUI) -> None:
        self._ui = ui
        self._checkpointer = _make_checkpointer()
        self._graph = AgentGraph(
            DefaultNodesProvider(),
            checkpointer=self._checkpointer,
            thread_id=_THREAD_ID,
        )
        if self._graph.has_checkpoint():
            self._ui.system_message("Resuming previous session.")

    def run(self) -> None:
        """Run the CLI loop until the user signals exit."""
        while True:
            try:
                event = self._ui.get_input("You: ")
            except SystemExit:
                return

            if event.command == Command.CLEAR:
                self._checkpointer.delete_thread(_THREAD_ID)
                self._ui.system_message("Session cleared.")
                continue

            if not event.text.strip():
                continue

            result = self._graph.invoke(event.text)
            last_message = result["messages"][-1]
            self._ui.assistant_message(last_message.content)
