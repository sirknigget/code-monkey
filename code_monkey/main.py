import logging

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

load_dotenv(override=True)


def main():
    from code_monkey.controller.controller import Controller
    from code_monkey.ui.impl.cli import CliChatbotUI

    Controller(CliChatbotUI()).run()


if __name__ == "__main__":
    main()
