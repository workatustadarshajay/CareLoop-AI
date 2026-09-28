from datetime import date, datetime, timezone

from sqlalchemy import desc, select, update
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
        due_date: date | None = None,
    ) -> Card:
        card = Card(
            note_id=note_id,
            type=card_type,
            description=description,
            due_date=due_date,
            status=CardStatus.OPEN,
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

    async def list_all(self) -> list[Card]:
        result = await self.session.execute(
            select(Card).order_by(desc(Card.created_at), desc(Card.id))
        )
        return list(result.scalars().all())

    async def list_for_note(self, note_id: int) -> list[Card]:
        result = await self.session.execute(
            select(Card)
            .where(Card.note_id == note_id)
            .order_by(Card.id)
        )
        return list(result.scalars().all())

    async def list_open(self) -> list[Card]:
        result = await self.session.execute(
            select(Card)
            .where(Card.status == CardStatus.OPEN)
            .order_by(Card.created_at, Card.id)
        )
        return list(result.scalars().all())

    async def list_due_through(self, cutoff: date) -> list[Card]:
        result = await self.session.execute(
            select(Card)
            .where(
                Card.status == CardStatus.OPEN,
                Card.due_date.is_not(None),
                Card.due_date <= cutoff,
            )
            .order_by(Card.due_date, Card.id)
        )
        return list(result.scalars().all())

    async def verify_closed(self, card_id: int, *, note_id: int) -> Card | None:
        result = await self.session.execute(
            update(Card)
            .where(Card.id == card_id, Card.status == CardStatus.OPEN)
            .values(
                status=CardStatus.VERIFIED_CLOSED,
                verified_at=datetime.now(timezone.utc),
                verified_by_note_id=note_id,
            )
            .returning(Card)
        )
        card = result.scalar_one_or_none()
        if card is not None:
            return card

        result = await self.session.execute(select(Card).where(Card.id == card_id))
        existing_card = result.scalar_one_or_none()
        if existing_card is not None and existing_card.status == CardStatus.VERIFIED_CLOSED:
            return existing_card
        return None

    async def list_verified_by_note(self, note_id: int) -> list[Card]:
        result = await self.session.execute(
            select(Card)
            .where(Card.verified_by_note_id == note_id)
            .order_by(Card.id)
        )
        return list(result.scalars().all())
