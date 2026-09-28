from typing import Any

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agents.context import ProcessingContext
from app.agents.tools import close_card, save_card
from app.core.config import Settings
from app.prompts import load_prompt


class AgentConfigurationError(RuntimeError):
    pass


class NoteAgent:
    def __init__(self, settings: Settings) -> None:
        if not settings.api_key:
            raise AgentConfigurationError(
                "Set GEMINI_API_KEY or GOOGLE_API_KEY in Backend/.env before processing a note."
            )

        model = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            api_key=settings.api_key,
            temperature=0,
            max_retries=2,
        )
        self._agent = create_agent(
            model=model,
            tools=[save_card, close_card],
            context_schema=ProcessingContext,
            system_prompt=load_prompt("note_agent"),
        )

    async def process(self, note_text: str, context: ProcessingContext) -> None:
        await self._agent.ainvoke(
            {"messages": [{"role": "user", "content": note_text}]},
            context=context,
            config={"recursion_limit": 50},
        )
