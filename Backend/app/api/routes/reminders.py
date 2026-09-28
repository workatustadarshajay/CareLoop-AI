from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.account import Role
from app.models.reminder import Reminder
from app.services.auth import CurrentAccount
from app.services.reminders import list_reminders

router = APIRouter(prefix="/reminders", tags=["reminders"])


class ReminderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    card_id: int
    message: str
    created_at: datetime


@router.get("", response_model=list[ReminderRead])
async def list_my_reminders(
    account: CurrentAccount,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Reminder]:
    patient_id = account.patient_id if account.role == Role.PATIENT else None
    return await list_reminders(db, patient_id)
