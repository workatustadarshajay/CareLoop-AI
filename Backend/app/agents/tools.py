from langchain.tools import ToolRuntime, tool

from app.models.card import CardType
from app.repositories.cards import CardRepository


@tool
async def save_card(
    type: CardType,
    description: str,
    runtime: ToolRuntime,
) -> str:
    """Save one actionable item from the note as a card in the database."""
    cleaned_description = description.strip()
    if not cleaned_description:
        raise ValueError("Card description cannot be empty")

    context = runtime.context
    async with context.write_lock:
        card = await CardRepository(context.session).create(
            note_id=context.note_id,
            card_type=type,
            description=cleaned_description,
        )

    return f"Saved card {card.id}."
