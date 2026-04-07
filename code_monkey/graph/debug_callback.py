import logging
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)


class DebugCallbackHandler(BaseCallbackHandler):
    def on_chain_start(
        self, serialized: dict[str, Any] | None, inputs: dict[str, Any], **kwargs: Any
    ) -> None:
        name = (serialized or {}).get("name") or kwargs.get("name", "unknown")
        logger.debug("node start: %s | inputs: %s", name, inputs)

    def on_chain_end(self, outputs: dict[str, Any], **kwargs: Any) -> None:
        logger.debug("node end | outputs: %s", outputs)

    def on_chain_error(self, error: BaseException, **kwargs: Any) -> None:
        logger.debug("node error: %s", error)
