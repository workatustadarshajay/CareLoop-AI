import asyncio
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class ProcessingContext:
    session: AsyncSession
    note_id: int
    write_lock: asyncio.Lock
    patient_id: int | None = None
    closed_card_ids: list[int] = field(default_factory=list)
