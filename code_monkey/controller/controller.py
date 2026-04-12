"""Controller: owns the CLI run loop and wires ChatbotUI to AgentGraph."""

from __future__ import annotations

from code_monkey.graph.agent_graph import AgentGraph
from code_monkey.ui.protocol import ChatbotUI, Command
from code_monkey.utils.log_utils import get_formatted_logger

logger = get_formatted_logger(__name__)


class Controller:
    def __init__(self, ui: ChatbotUI, graph: AgentGraph) -> None:
        self._ui = ui
        self._graph = graph

    async def _replay_history(self) -> None:
        logger.debug("Replaying conversation history...")
        async for role, content in self._graph.aget_history():
            if role == "user":
                self._ui.user_message(content)
            else:
                self._ui.assistant_message(content)
        self._ui.system_message("Resuming previous session.")

    async def run(self) -> None:
        """Run the CLI loop until the user signals exit."""
        logger.debug("Checking for existing session...")
        if await self._graph.ahas_checkpoint():
            await self._replay_history()

        while True:
            try:
                event = self._ui.get_input("You: ")
            except SystemExit:
                logger.info("Exit command received. Shutting down.")
                return

            if event.command == Command.CLEAR:
                await self._graph.aclear()
                self._ui.system_message("Session cleared.")
                continue

            if event.command == Command.MAP:
                await self._graph.trigger_mapping()
                self._ui.system_message("Project mapping scheduled for next message.")
                continue

            if event.command == Command.EXIT:
                return

            if not event.text.strip():
                continue

            try:
                async for chunk in self._graph.astream(event.text):
                    if chunk.kind == "warning":
                        self._ui.system_message(chunk.content)
                    else:
                        self._ui.assistant_message(chunk.content)
            except Exception as e:
                logger.exception("Error processing turn")
                self._ui.show_error(f"Error: {e}")
