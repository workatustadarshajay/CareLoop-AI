from typing import Any

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agents.context import ProcessingContext
from app.agents.tools import save_card
from app.core.config import Settings


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
            tools=[save_card],
            context_schema=ProcessingContext,
            system_prompt=(
                "You extract actionable items from a doctor's note. "
                "Call save_card exactly once for every distinct actionable item "
                "you find, and do not combine multiple items into one call. "
                "Use only these types: medication, test, referral, next_visit, or general_task. "
                "Keep each description short and faithful to the note. "
                "Do not invent details, and do not return an extracted list instead of calling the tool. "
                "When the cards are saved, finish with a brief confirmation."
            ),
        )

    async def process(self, note_text: str, context: ProcessingContext) -> None:
        await self._agent.ainvoke(
            {"messages": [{"role": "user", "content": note_text}]},
            context=context,
            config={"recursion_limit": 50},
        )
