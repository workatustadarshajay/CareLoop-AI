from datetime import date, timedelta
from typing import Protocol

from app.models.card import Card
from app.schemas.reminder import ReminderRead

REMINDER_WINDOW_DAYS = 7


class ReminderCardRepository(Protocol):
    async def list_due_through(self, cutoff: date) -> list[Card]: ...


def reminder_message(card: Card, today: date) -> str:
    if card.due_date is None:
        raise ValueError("A reminder requires a due date")

    days_until_due = (card.due_date - today).days
    formatted_due_date = card.due_date.strftime("%b %d").replace(" 0", " ")
    if days_until_due < 0:
        return f"{card.description} was due {formatted_due_date}."
    if days_until_due == 0:
        return f"{card.description} is due today."
    if days_until_due == 1:
        return f"{card.description} is due tomorrow."
    return f"{card.description} is due {formatted_due_date}."


class ReminderService:
    def __init__(self, cards: ReminderCardRepository) -> None:
        self.cards = cards

    async def list_upcoming(self, today: date) -> list[ReminderRead]:
        cards = await self.cards.list_due_through(
            today + timedelta(days=REMINDER_WINDOW_DAYS)
        )
        return [
            ReminderRead(
                card_id=card.id,
                type=card.type,
                message=reminder_message(card, today),
                due_date=card.due_date,
            )
            for card in cards
            if card.due_date is not None
        ]
