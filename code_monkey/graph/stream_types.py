from dataclasses import dataclass
from typing import Literal


@dataclass
class StreamChunk:
    content: str
    kind: Literal["assistant", "warning"] = "assistant"
