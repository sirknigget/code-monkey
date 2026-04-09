import argparse
import asyncio
import os
import sys
import traceback
from typing import Protocol

from dotenv import load_dotenv

from code_monkey.controller.controller import Controller
from code_monkey.graph.agent_graph import AgentGraph
from code_monkey.graph.checkpointer import CheckpointerResult, make_checkpointer
from code_monkey.models.model_config import ModelConfig
from code_monkey.ui.impl.cli_simple import SimpleCliChatbotUI
from code_monkey.ui.protocol import ChatbotUI
from code_monkey.utils.log_utils import get_formatted_logger, suppress_noisy_loggers

load_dotenv(override=True)

suppress_noisy_loggers()
logger = get_formatted_logger(__name__)


class CheckpointerFactory(Protocol):
    async def __call__(self) -> CheckpointerResult: ...


async def setup(
    project_root: str,
    ui: ChatbotUI,
    checkpointer_factory: CheckpointerFactory,
    model_config: ModelConfig,
) -> None:
    logger.info(
        "Starting code-monkey CLI assistant with project root: %s", project_root
    )

    logger.debug("Initializing checkpointer...")
    result = await checkpointer_factory()
    for error in result.errors:
        ui.show_error(error)
    if result.checkpointer is None:
        return

    thread_id = os.path.abspath(project_root)
    logger.debug("Creating agent graph...")
    graph = await AgentGraph.create(
        checkpointer=result.checkpointer,
        project_root=project_root,
        model_config=model_config,
        thread_id=thread_id,
    )
    try:
        logger.debug("Running controller...")
        await Controller(ui, graph).run()
    except Exception as e:
        logger.exception("Fatal error in main loop")
        ui.show_error(f"Fatal error: {e}")
    finally:
        logger.debug("Shutting down...")
        ui.system_message("Shutting down...")
        await graph.teardown()
        await result.checkpointer.conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="code-monkey CLI assistant")
    parser.add_argument(
        "--path",
        default=None,
        help="Project root directory (default: current working directory)",
    )
    args = parser.parse_args()

    project_root = args.path if args.path is not None else os.getcwd()
    if not os.path.isdir(project_root):
        print(
            f"Error: --path '{project_root}' is not an existing directory.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    try:
        asyncio.run(
            setup(
                project_root=project_root,
                ui=SimpleCliChatbotUI(),
                checkpointer_factory=make_checkpointer,
                model_config=ModelConfig(),
            )
        )
    except SystemExit:
        raise
    except BaseException:
        msg = traceback.format_exc()
        print(f"Fatal error:\n{msg}", file=sys.stderr, flush=True)
        logger.error("Fatal error:\n%s", msg)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
