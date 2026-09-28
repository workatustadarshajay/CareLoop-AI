import asyncio
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.context import ProcessingContext
from app.agents.note_agent import NoteAgent
from app.care_gaps.pipeline import run_care_gap_check
from app.models.card import Card
from app.repositories.cards import CardRepository
from app.repositories.notes import NoteRepository
from app.schemas.note import NoteProcessResponse


def build_agent_input(note_text: str, open_cards: list[Card]) -> str:
    """The note plus what the agent needs to date items and recognise completed cards."""
    lines = [f"Today is {date.today().isoformat()}."]
    if open_cards:
        lines.append("Open cards for this patient (id: description):")
        lines += [f"- {card.id}: {card.description} [{card.type.value}]" for card in open_cards]
    lines += ["", "Note:", note_text]
    return "\n".join(lines)


class NoteProcessingService:
    def __init__(self, session: AsyncSession, agent: NoteAgent) -> None:
        self.session = session
        self.agent = agent
        self.notes = NoteRepository(session)
        self.cards = CardRepository(session)

    async def process(self, note_text: str, patient_id: int | None = None) -> NoteProcessResponse:
        async with self.session.begin():
            note = await self.notes.create(note_text, patient_id)
            open_cards = await self.cards.list_open_for_patient(patient_id) if patient_id else []
            context = ProcessingContext(
                session=self.session,
                note_id=note.id,
                write_lock=asyncio.Lock(),
                patient_id=patient_id,
            )
            await self.agent.process(build_agent_input(note_text, open_cards), context)
            note_id = note.id

        cards = await self.cards.list_for_note(note_id)
        await run_care_gap_check(note_id, note_text, cards)
        return NoteProcessResponse(
            note_id=note_id,
            cards=cards,
            closed_card_ids=context.closed_card_ids,
        )
