import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.context import ProcessingContext
from app.agents.note_agent import NoteAgent
from app.care_gaps.pipeline import run_care_gap_check
from app.repositories.cards import CardRepository
from app.repositories.notes import NoteRepository
from app.schemas.note import NoteProcessResponse


class NoteProcessingService:
    def __init__(self, session: AsyncSession, agent: NoteAgent) -> None:
        self.session = session
        self.agent = agent
        self.notes = NoteRepository(session)
        self.cards = CardRepository(session)

    async def process(self, note_text: str) -> NoteProcessResponse:
        async with self.session.begin():
            note = await self.notes.create(note_text)
            await self.agent.process(
                note_text,
                ProcessingContext(
                    session=self.session,
                    note_id=note.id,
                    write_lock=asyncio.Lock(),
                ),
            )
            note_id = note.id

        cards = await self.cards.list_for_note(note_id)
        await run_care_gap_check(note_id, note_text, cards)
        return NoteProcessResponse(
            note_id=note_id,
            cards=cards,
        )
