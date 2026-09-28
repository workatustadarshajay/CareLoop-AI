from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.account import Role
from app.models.card import Card, CardStatus
from app.repositories.cards import CardRepository
from app.schemas.card import CardRead
from app.services.auth import CurrentAccount, DoctorAccount
from app.services.dependency_service import DependencyService

router = APIRouter(prefix="/cards", tags=["cards"])

DbSession = Annotated[AsyncSession, Depends(get_db)]

CLOSED = (CardStatus.DONE, CardStatus.VERIFIED_CLOSED)


class CardUpdate(BaseModel):
    status: CardStatus | None = None
    due_at: datetime | None = None


@router.get("", response_model=list[CardRead])
async def list_cards(account: CurrentAccount, db: DbSession) -> list[CardRead]:
    # Patients see their own cards; doctors/admins see everyone's.
    patient_id = account.patient_id if account.role == Role.PATIENT else None
    return await CardRepository(db).list_all(patient_id)


@router.patch("/{card_id}", response_model=CardRead)
async def update_card(card_id: int, payload: CardUpdate, _: DoctorAccount, db: DbSession) -> CardRead:
    """Manual status/due-date change. Closing a card re-checks anything that depends on it."""
    card = await db.get(Card, card_id)
    if card is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Card not found.")
    if "due_at" in payload.model_fields_set:
        card.due_at = payload.due_at
    if payload.status is not None:
        card.status = payload.status
        if payload.status in CLOSED:
            card.risk_reason = None
            await db.flush()
            await DependencyService(db).propagate_risk_updates(card.id)
    await db.commit()
    await db.refresh(card)
    return card
