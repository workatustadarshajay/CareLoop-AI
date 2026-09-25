from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.cards import CardRepository
from app.schemas.card import CardRead

router = APIRouter(prefix="/cards", tags=["cards"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[CardRead])
async def list_cards(db: DbSession) -> list[CardRead]:
    return await CardRepository(db).list_all()
