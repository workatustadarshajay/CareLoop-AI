# Run: uv run python -m tests.test_llm_factory
from app.core.config import Settings
from app.core.llm import AgentConfigurationError, build_chat_model


def demo() -> None:
    keys = {"gemini_api_key": "k", "anthropic_api_key": "k", "openai_api_key": "k"}
    assert type(build_chat_model(Settings(llm_provider="gemini", **keys))).__name__ == "ChatGoogleGenerativeAI"
    assert type(build_chat_model(Settings(llm_provider="anthropic", **keys))).__name__ == "ChatAnthropic"
    assert type(build_chat_model(Settings(llm_provider="openai", **keys))).__name__ == "ChatOpenAI"
    try:
        build_chat_model(Settings(llm_provider="openai", openai_api_key=None))
    except AgentConfigurationError:
        pass
    else:
        raise AssertionError("missing OPENAI_API_KEY should raise")
    print("llm factory ok")


if __name__ == "__main__":
    demo()
