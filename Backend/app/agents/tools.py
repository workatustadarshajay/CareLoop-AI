from datetime import date

from langchain.tools import ToolRuntime, tool

from app.agents.context import ProcessingContext
from app.models.card import CardType
from app.repositories.cards import CardRepository
from app.services.dependency_service import DependencyService


@tool
async def save_card(
    type: CardType,
    description: str,
    due_date: date | None,
    runtime: ToolRuntime[ProcessingContext, dict[str, object]],
) -> str:
    """Save one actionable item from the note as a card in the database."""
    cleaned_description = description.strip()
    if not cleaned_description:
        raise ValueError("Card description cannot be empty")
    if len(cleaned_description) > 500:
        raise ValueError("Card description cannot exceed 500 characters")

    context = runtime.context
    async with context.write_lock:
        card = await CardRepository(context.session).create(
            note_id=context.note_id,
            card_type=type,
            description=cleaned_description,
            due_date=due_date,
        )

    return f"Saved card {card.id}."


@tool
async def verify_card_completed(
    card_id: int,
    runtime: ToolRuntime[ProcessingContext, dict[str, object]],
) -> str:
    """Mark an open card verified closed when the new note confirms it happened."""
    context = runtime.context
    if card_id not in context.open_card_ids:
        raise ValueError(f"Card {card_id} is not an available open card")

    async with context.write_lock:
        card = await CardRepository(context.session).verify_closed(
            card_id,
            note_id=context.note_id,
        )
        if card is not None:
            await DependencyService(context.session).propagate_risk_updates(card.id)

    if card is None:
        raise ValueError(f"Card {card_id} is no longer open")
    if card.verified_by_note_id != context.note_id:
        return f"Card {card.id} was already verified closed."
    return f"Verified card {card.id} closed."
