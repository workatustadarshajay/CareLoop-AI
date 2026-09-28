from datetime import datetime, timezone

from langchain.tools import ToolRuntime, tool

from app.models.card import Card, CardStatus, CardType
from app.repositories.cards import CardRepository
from app.services.dependency_service import DependencyService


def _parse_due(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        due = datetime.fromisoformat(value)
    except ValueError:
        return None
    return due if due.tzinfo else due.replace(tzinfo=timezone.utc)


@tool
async def save_card(
    type: CardType,
    description: str,
    runtime: ToolRuntime,
    due_date: str | None = None,
) -> str:
    """Save one actionable item from the note as a card in the database.

    due_date: ISO date (YYYY-MM-DD) when the item should be done, if the note says
    or clearly implies one (e.g. "next week", "in two weeks"); otherwise omit it.
    """
    cleaned_description = description.strip()
    if not cleaned_description:
        raise ValueError("Card description cannot be empty")

    context = runtime.context
    async with context.write_lock:
        card = await CardRepository(context.session).create(
            note_id=context.note_id,
            card_type=type,
            description=cleaned_description,
            due_at=_parse_due(due_date),
        )

    return f"Saved card {card.id}."


@tool
async def close_card(card_id: int, evidence: str, runtime: ToolRuntime) -> str:
    """Mark an existing open card as verified closed because the note confirms it was completed.

    Use only for cards listed as open for this patient. evidence: the phrase from the
    note that confirms completion (e.g. "MRI completed on Monday").
    """
    context = runtime.context
    async with context.write_lock:
        card = await context.session.get(Card, card_id)
        if card is None or card.patient_id != context.patient_id:
            return f"Card {card_id} is not one of this patient's cards; nothing closed."
        if card.status in (CardStatus.DONE, CardStatus.VERIFIED_CLOSED):
            return f"Card {card_id} was already closed."
        card.status = CardStatus.VERIFIED_CLOSED
        card.risk_reason = None
        await context.session.flush()
        # Same signal a manual status change sends: let dependent cards re-check their risk.
        await DependencyService(context.session).propagate_risk_updates(card.id)
        context.closed_card_ids.append(card.id)

    return f"Closed card {card_id} (verified by: {evidence.strip()})."
