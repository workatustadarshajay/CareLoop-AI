from typing import Any

from langchain.agents import create_agent

from app.agents.context import ProcessingContext
from app.agents.tools import close_card, save_card
from app.core.config import Settings
from app.core.llm import build_chat_model
from app.prompts import load_prompt


class NoteAgent:
    def __init__(self, settings: Settings) -> None:
        self._agent = create_agent(
            model=build_chat_model(settings),
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
