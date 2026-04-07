import asyncio
import logging
import os
import sys
import traceback

from dotenv import load_dotenv

from code_monkey.controller.controller import Controller
from code_monkey.graph.agent_graph import AgentGraph
from code_monkey.graph.checkpointer import DEFAULT_THREAD_ID, make_checkpointer
from code_monkey.models.model_config import ModelConfig
from code_monkey.ui.impl.cli_simple import SimpleCliChatbotUI
from code_monkey.utils.log_utils import suppress_noisy_loggers

logging.basicConfig(
    level=logging.DEBUG, format="%(levelname)s: %(message)s", stream=sys.stdout
)
logger = logging.getLogger(__name__)
suppress_noisy_loggers()

load_dotenv(override=True)


async def _main() -> None:
    ui = SimpleCliChatbotUI()

    result = await make_checkpointer()
    for error in result.errors:
        ui.show_error(error)
    if result.checkpointer is None:
        return

    graph = await AgentGraph.create(
        checkpointer=result.checkpointer,
        project_root=os.getcwd(),
        model_config=ModelConfig(),
        thread_id=DEFAULT_THREAD_ID,
    )
    try:
        await Controller(ui, graph).run()
    finally:
        await graph.teardown()
        await result.checkpointer.conn.close()


def main() -> None:
    try:
        asyncio.run(_main())
    except SystemExit:
        raise
    except BaseException:
        msg = traceback.format_exc()
        print(f"Fatal error:\n{msg}", file=sys.stderr, flush=True)
        logger.error("Fatal error:\n%s", msg)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
