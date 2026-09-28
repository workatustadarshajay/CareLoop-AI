from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.card import Card, CardStatus
from app.models.reminder import Reminder

CLOSED = (CardStatus.DONE, CardStatus.VERIFIED_CLOSED)


def reminder_message(card: Card, now: datetime) -> str:
    what = card.description
    when = card.due_at.strftime("%b %d")
    return f"Overdue: {what} (was due {when})." if card.due_at < now else f"Coming up: {what} (due {when})."


async def generate_reminders(db: AsyncSession, patient_id: int | None = None) -> None:
    """Write a reminder for every open card due within the window that has none yet."""
    now = datetime.now(timezone.utc)
    query = (
        select(Card)
        .outerjoin(Reminder, Reminder.card_id == Card.id)
        .where(
            Reminder.id.is_(None),
            Card.status.not_in(CLOSED),
            Card.due_at.is_not(None),
            Card.due_at <= now + timedelta(days=get_settings().reminder_days),
        )
    )
    if patient_id is not None:
        query = query.where(Card.patient_id == patient_id)
    cards = (await db.execute(query)).scalars().all()
    db.add_all(Reminder(card_id=card.id, message=reminder_message(card, now)) for card in cards)
    await db.commit()


async def list_reminders(db: AsyncSession, patient_id: int | None = None) -> list[Reminder]:
    """Reminders whose card is still open; closed cards drop out automatically."""
    await generate_reminders(db, patient_id)
    query = select(Reminder).join(Card).where(Card.status.not_in(CLOSED)).order_by(Card.due_at)
    if patient_id is not None:
        query = query.where(Card.patient_id == patient_id)
    return list((await db.execute(query)).scalars().all())
