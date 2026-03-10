from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

GPT_4O = "gpt-4o"
GPT_4O_MINI = "gpt-4o-mini"
MINIMAX_M2 = "MiniMax-M2.1"


def get_openai_model(model: str = GPT_4O) -> ChatOpenAI:
    """Return a predefined OpenAI model."""
    return ChatOpenAI(model=model)


def get_minimax_model() -> ChatAnthropic:
    """Return the MiniMax model with custom Anthropic API endpoint."""
    return ChatAnthropic(
        model=MINIMAX_M2,
        anthropic_api_url="https://api.minimax.io/anthropic",
    )
