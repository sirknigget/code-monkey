"""Integration test — verifies that the local Ollama model is reachable and responds."""

import pytest
from langchain_core.messages import HumanMessage

from code_monkey.models.models import get_ollama_model


@pytest.mark.integration
def test_ollama_model_responds():
    model = get_ollama_model()
    response = model.invoke([HumanMessage(content="Say hello")])
    assert isinstance(response.content, str) and len(response.content) > 0
