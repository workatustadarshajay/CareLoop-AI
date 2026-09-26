"""Attach plain-language generation to card creation without touching it.

How it works: a SQLAlchemy ``after_insert`` mapper event fires the moment a
Card row is flushed (i.e. right after a card is normally created). The
handler schedules a background asyncio task that calls the rewriter and
stores the result in ``cards.description_plain`` using its OWN database
session.

Nothing in the existing creation flow (agent tools, note processing
service, repositories) is modified or blocked: card creation stays
exactly as fast as before, and a rewrite failure never fails card
creation.
"""

import asyncio
import logging

from sqlalchemy import event, update
from sqlalchemy.orm import Mapper

from app.models.card import Card

logger = logging.getLogger(__name__)

_registered = False


async def _write_plain_description(card_id: int, plain_text: str) -> None:
    """Store the rewrite in its own short-lived session."""
    from app.db.session import async_session_factory

    try:
        async with async_session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    update(Card)
                    .where(Card.id == card_id)
                    .values(description_plain=plain_text)
                )
        if result.rowcount == 0:
            # Card row never committed (creation rolled back) — nothing to do.
            logger.info("plain-language update matched no card %s", card_id)
        else:
            logger.info("plain-language description saved for card %s", card_id)
    except Exception:
        logger.exception(
            "failed to save plain-language description for card %s", card_id
        )


async def generate_and_store_plain_description(
    card_id: int, description: str, card_type: str
) -> None:
    """Rewrite, then persist. Never raises."""
    from app.plain_language.rewriter import rewrite_card_description

    plain_text = await rewrite_card_description(description, card_type)
    if plain_text is None:
        return
    await _write_plain_description(card_id, plain_text)


def schedule_rewrite(card_id: int, description: str, card_type: str) -> None:
    """Schedule the rewrite as a background task; safe to call anywhere."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.warning(
            "no running event loop; skipping plain-language rewrite for card %s",
            card_id,
        )
        return
    loop.create_task(
        generate_and_store_plain_description(card_id, description, card_type)
    )


def _after_card_insert(
    mapper: Mapper,
    connection: object,
    target: Card,
) -> None:
    """Fires right after a Card row is flushed, inside its creation flow."""
    schedule_rewrite(target.id, target.description, target.type.value)


def register_listeners() -> None:
    global _registered
    if _registered:
        return
    event.listen(Card, "after_insert", _after_card_insert)
    _registered = True
    logger.info("plain-language listeners registered on Card")
