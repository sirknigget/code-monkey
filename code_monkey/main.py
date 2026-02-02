import logging

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

load_dotenv(override=True)


def main():
    logger.info("Hello from code-monkey!")


if __name__ == "__main__":
    main()
