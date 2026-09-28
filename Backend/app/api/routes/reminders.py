from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.cards import CardRepository
from app.schemas.reminder import ReminderRead
from app.services.reminders import ReminderService

router = APIRouter(prefix="/reminders", tags=["reminders"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[ReminderRead])
async def list_reminders(db: DbSession) -> list[ReminderRead]:
    today = datetime.now(timezone.utc).date()
    return await ReminderService(CardRepository(db)).list_upcoming(today)
