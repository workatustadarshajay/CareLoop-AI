from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card, CardStatus, CardType


class CardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        note_id: int,
        card_type: CardType,
        description: str,
        due_at: datetime | None = None,
    ) -> Card:
        card = Card(
            note_id=note_id,
            type=card_type,
            description=description,
            status=CardStatus.OPEN,
            due_at=due_at,
        )
        self.session.add(card)
        await self.session.flush()
        return card

    async def create_many(
        self,
        *,
        note_id: int,
        items: list[tuple[CardType, str]],
    ) -> list[Card]:
        cards = [
            Card(
                note_id=note_id,
                type=card_type,
                description=description,
                status=CardStatus.OPEN,
            )
            for card_type, description in items
        ]
        self.session.add_all(cards)
        await self.session.flush()
        return cards

    async def list_all(self, patient_id: int | None = None) -> list[Card]:
        query = select(Card).order_by(desc(Card.created_at), desc(Card.id))
        if patient_id is not None:
            query = query.where(Card.patient_id == patient_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_open_for_patient(self, patient_id: int) -> list[Card]:
        result = await self.session.execute(
            select(Card)
            .where(
                Card.patient_id == patient_id,
                Card.status.not_in([CardStatus.DONE, CardStatus.VERIFIED_CLOSED]),
            )
            .order_by(Card.id)
        )
        return list(result.scalars().all())

    async def list_for_note(self, note_id: int) -> list[Card]:
        result = await self.session.execute(
            select(Card)
            .where(Card.note_id == note_id)
            .order_by(Card.id)
        )
        return list(result.scalars().all())
