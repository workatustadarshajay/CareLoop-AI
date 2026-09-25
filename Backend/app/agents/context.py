import asyncio
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class ProcessingContext:
    session: AsyncSession
    note_id: int
    write_lock: asyncio.Lock
