import logging

from dotenv import load_dotenv

from code_monkey.ui.impl.cli_simple import SimpleCliChatbotUI
from code_monkey.utils.log_utils import suppress_noisy_loggers

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
suppress_noisy_loggers()

load_dotenv(override=True)


def main():

    from code_monkey.controller.controller import Controller

    Controller(SimpleCliChatbotUI()).run()


if __name__ == "__main__":
    main()
