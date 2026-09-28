import asyncio
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class ProcessingContext:
    session: AsyncSession
    note_id: int
    open_card_ids: frozenset[int]
    write_lock: asyncio.Lock
