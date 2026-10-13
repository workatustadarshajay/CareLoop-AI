from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.core.config import Settings


class AgentConfigurationError(RuntimeError):
    pass


def _require(key: str | None, env_name: str) -> str:
    if not key:
        raise AgentConfigurationError(f"Set {env_name} in Backend/.env to use this LLM provider.")
    return key


def build_chat_model(settings: Settings) -> BaseChatModel:
    """Factory: returns the chat model for LLM_PROVIDER (gemini by default)."""
    if settings.llm_provider == "anthropic":
        return ChatAnthropic(
            model=settings.anthropic_model,
            api_key=_require(settings.anthropic_api_key, "ANTHROPIC_API_KEY"),
            temperature=0,
            max_retries=2,
        )
    if settings.llm_provider == "openai":
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=_require(settings.openai_api_key, "OPENAI_API_KEY"),
            temperature=0,
            max_retries=2,
        )
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        api_key=_require(settings.gemini_api_key or settings.google_api_key, "GEMINI_API_KEY or GOOGLE_API_KEY"),
        temperature=0,
        max_retries=2,
    )
