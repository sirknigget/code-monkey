import os
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

GPT_4O = "gpt-4o"
GPT_4O_MINI = "gpt-4o-mini"
GPT_4_1 = "gpt-4.1"
MINIMAX_M2 = "MiniMax-M2.1"
OLLAMA_DEFAULT_MODEL = "qwen2.5:1.5b"


def _default_ollama_base_url() -> str:
    # Inside Docker containers /.dockerenv always exists
    if Path("/.dockerenv").exists():
        return "http://host.docker.internal:11434/v1"
    return "http://localhost:11434/v1"


_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL") or _default_ollama_base_url()


def get_openai_model(model: str = GPT_4O_MINI) -> ChatOpenAI:
    """Return a predefined OpenAI model."""
    return ChatOpenAI(model=model)


def get_ollama_model(model: str = OLLAMA_DEFAULT_MODEL) -> ChatOpenAI:
    """Return a local Ollama model via its OpenAI-compatible API."""
    return ChatOpenAI(model=model, base_url=_OLLAMA_BASE_URL, api_key="ollama")


def get_minimax_model() -> ChatAnthropic:
    """Return the MiniMax model with custom Anthropic API endpoint."""
    return ChatAnthropic(
        model=MINIMAX_M2,
        anthropic_api_url="https://api.minimax.io/anthropic",
    )
