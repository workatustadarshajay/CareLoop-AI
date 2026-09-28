from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note


class NoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, text: str, patient_id: int | None = None) -> Note:
        note = Note(text=text, patient_id=patient_id)
        self.session.add(note)
        await self.session.flush()
        return note
