import logging
import os
import sys
from logging import Logger

from dotenv import load_dotenv

load_dotenv(override=True)


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

_log_level_str = os.getenv("LOG_LEVEL", "WARNING").upper()
_resolved = getattr(logging, _log_level_str, None)
if not isinstance(_resolved, int):
    print(
        f"WARNING: Unrecognized LOG_LEVEL value '{_log_level_str}', defaulting to WARNING.",
        file=sys.stderr,
    )
    _resolved = logging.WARNING
LOG_LEVEL: int = _resolved


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
