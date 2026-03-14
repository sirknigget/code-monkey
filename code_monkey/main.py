import asyncio
import logging
import os

from dotenv import load_dotenv

from code_monkey.controller.controller import Controller
from code_monkey.graph.agent_graph import AgentGraph
from code_monkey.graph.checkpointer import DEFAULT_THREAD_ID, make_checkpointer
from code_monkey.ui.impl.cli_simple import SimpleCliChatbotUI
from code_monkey.utils.log_utils import suppress_noisy_loggers

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
suppress_noisy_loggers()

load_dotenv(override=True)


async def _main() -> None:
    graph = await AgentGraph.create(
        checkpointer=make_checkpointer(),
        project_root=os.getcwd(),
        thread_id=DEFAULT_THREAD_ID,
    )
    Controller(SimpleCliChatbotUI(), graph).run()


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
