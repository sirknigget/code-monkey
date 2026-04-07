import logging
import sys
from logging import Logger


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[36m",  # cyan
        logging.INFO: "\033[32m",  # green
        logging.WARNING: "\033[33m",  # yellow
        logging.ERROR: "\033[31m",  # red
        logging.CRITICAL: "\033[1;31m",  # bold red
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"


LOG_HANDLER = logging.StreamHandler(stream=sys.stdout)
LOG_HANDLER.setLevel(logging.DEBUG)
LOG_HANDLER.setFormatter(ColorFormatter("%(levelname)s: %(name)s: %(message)s"))

LOG_LEVEL = logging.DEBUG


def get_formatted_logger(name: str) -> Logger:
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.addHandler(LOG_HANDLER)
    logger.setLevel(LOG_LEVEL)
    return logger


def suppress_noisy_loggers():
    import logging

    # Suppress low-level HTTP transport noise during tests
    for _noisy_logger in (
        "httpx",
        "httpcore",
        "urllib3",
        "openai._base_client",
        "langsmith",
        "aiosqlite",
        "asyncio",
    ):
        logging.getLogger(_noisy_logger).setLevel(logging.WARNING)


def logging_basic_config():
    logging.basicConfig(
        stream=sys.stdout,
    )
