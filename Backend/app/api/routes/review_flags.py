from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.review_flags import ReviewFlagRepository
from app.schemas.card import CardRead
from app.schemas.review_flag import ReviewFlagRead
from app.services.review_flags import PendingFlagNotFound, ReviewFlagService

router = APIRouter(prefix="/review-flags", tags=["review flags"])

DbSession = Annotated[AsyncSession, Depends(get_db)]

NOT_PENDING = "No pending flag with this id."


@router.get("", response_model=list[ReviewFlagRead])
async def list_pending_flags(db: DbSession) -> list[ReviewFlagRead]:
    return await ReviewFlagRepository(db).list_pending()


@router.post("/{flag_id}/approve", response_model=CardRead, status_code=status.HTTP_201_CREATED)
async def approve_flag(flag_id: int, db: DbSession) -> CardRead:
    try:
        return await ReviewFlagService(db).approve(flag_id)
    except PendingFlagNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_PENDING) from None


@router.post("/{flag_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_flag(flag_id: int, db: DbSession) -> None:
    try:
        await ReviewFlagService(db).dismiss(flag_id)
    except PendingFlagNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_PENDING) from None
