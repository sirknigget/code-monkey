from typing import Any

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.types import CustomStreamPart, StreamPart, UpdatesStreamPart

from code_monkey.graph.stream_types import StreamChunk


def is_visible_ai_message(msg: BaseMessage) -> bool:
    """Return True for AIMessages that carry visible text (no tool calls)."""
    return (
        isinstance(msg, AIMessage)
        and isinstance(msg.content, str)
        and bool(msg.content)
        and not msg.tool_calls
    )


def stream_chunks_from_part(part: StreamPart[Any, Any]) -> list[StreamChunk]:
    if part["type"] == "custom":
        custom_chunk = custom_stream_chunk(part)
        return [] if custom_chunk is None else [custom_chunk]
    if part["type"] == "updates":
        return assistant_chunks_from_updates(part)
    return []


def assistant_chunks_from_updates(part: UpdatesStreamPart) -> list[StreamChunk]:
    chunks: list[StreamChunk] = []
    for node_update in part["data"].values():
        if not isinstance(node_update, dict):
            continue
        for msg in node_update.get("messages", []):
            if is_visible_ai_message(msg):
                chunks.append(StreamChunk(content=msg.content, kind="assistant"))
    return chunks


def custom_stream_chunk(part: CustomStreamPart) -> StreamChunk | None:
    if not isinstance(part["data"], dict):
        return None
    content = part["data"].get("content")
    kind = part["data"].get("kind")
    if not isinstance(content, str) or kind not in ("assistant", "warning"):
        return None
    return StreamChunk(content=content, kind=kind)
