from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage


_SYSTEM_PROMPT = (
    "You are a conversation summarizer. "
    "Given a running summary of earlier conversation history and a list of new messages, "
    "produce a concise updated summary that captures the key context needed to understand the conversation. "
    "Keep it brief and factual."
)


def _format_message(msg: BaseMessage) -> str:
    role = "User" if isinstance(msg, HumanMessage) else "Assistant"
    content = msg.content
    return f"{role}: {content if isinstance(content, str) else str(content)}"


def _is_plain_ai_message(msg: BaseMessage) -> bool:
    return (
        isinstance(msg, AIMessage)
        and bool(msg.content)
        and not getattr(msg, "tool_calls", None)
    )


class ChatSummarizer:
    def __init__(self, model: BaseChatModel) -> None:
        self._model = model

    async def summarize(
        self,
        messages: list[BaseMessage],
        existing_summary: str,
        chat_summary_span: int,
    ) -> tuple[str, list[BaseMessage], int]:
        """
        Returns: (updated_summary, last_messages, new_chat_summary_span)
        """
        filtered: list[BaseMessage] = [
            msg
            for msg in messages
            if isinstance(msg, HumanMessage) or _is_plain_ai_message(msg)
        ]

        human_indices = [i for i, msg in enumerate(filtered) if isinstance(msg, HumanMessage)]
        if not human_indices:
            return existing_summary, [], 0

        last_user_idx = human_indices[-1]
        last_messages: list[BaseMessage] = filtered[last_user_idx:]
        to_summarize: list[BaseMessage] = filtered[chat_summary_span:last_user_idx]

        if to_summarize:
            formatted_messages = "\n".join(_format_message(msg) for msg in to_summarize)
            prompt_text = (
                f"Existing summary:\n{existing_summary}\n\nNew messages to incorporate:\n{formatted_messages}"
                if existing_summary
                else f"Messages to summarize:\n{formatted_messages}"
            )
            llm_messages: list[BaseMessage] = [
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=prompt_text),
            ]
            response = await self._model.ainvoke(llm_messages)
            raw_content = response.content
            updated_summary: str = raw_content if isinstance(raw_content, str) else str(raw_content)
        else:
            updated_summary = existing_summary

        return updated_summary, last_messages, last_user_idx
