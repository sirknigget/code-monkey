from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic


def get_openai_model(model: str = "gpt-4o") -> ChatOpenAI:
    """Return a predefined OpenAI model."""
    return ChatOpenAI(model=model)


def get_minimax_model() -> ChatAnthropic:
    """Return the MiniMax model with custom Anthropic API endpoint."""
    return ChatAnthropic(
        model="MiniMax-M2.1",
        anthropic_api_url="https://api.minimax.io/anthropic",
    )
