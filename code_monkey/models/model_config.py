from langchain_core.language_models import BaseChatModel

from code_monkey.models.models import GPT_4O, GPT_4O_MINI, get_openai_model


class ModelConfig:
    """Provides the appropriate model for each agent task."""

    def web_researcher_model(self) -> BaseChatModel:
        return get_openai_model(GPT_4O_MINI)

    def summarizer_model(self) -> BaseChatModel:
        return get_openai_model(GPT_4O_MINI)

    def orchestrator_model(self) -> BaseChatModel:
        return get_openai_model(GPT_4O)
