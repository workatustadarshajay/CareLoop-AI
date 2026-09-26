from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.review_flag import ReviewFlag, ReviewFlagKind, ReviewFlagStatus
from app.repositories.cards import CardRepository
from app.repositories.review_flags import ReviewFlagRepository


class PendingFlagNotFound(Exception):
    pass


class ReviewFlagService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.flags = ReviewFlagRepository(session)

    async def approve(self, flag_id: int) -> Card:
        async with self.session.begin():
            flag = await self._pending(flag_id)
            if flag.kind is not ReviewFlagKind.MISSING_ITEM or flag.card_type is None or not flag.card_description:
                raise PendingFlagNotFound(flag_id)
            card = await CardRepository(self.session).create(
                note_id=flag.note_id,
                card_type=flag.card_type,
                description=flag.card_description,
            )
            await self.session.refresh(card)
            self._resolve(flag, ReviewFlagStatus.APPROVED)
            flag.created_card_id = card.id
        return card

    async def dismiss(self, flag_id: int) -> None:
        async with self.session.begin():
            self._resolve(await self._pending(flag_id), ReviewFlagStatus.DISMISSED)

    async def _pending(self, flag_id: int) -> ReviewFlag:
        flag = await self.flags.get_pending_for_update(flag_id)
        if flag is None:
            raise PendingFlagNotFound(flag_id)
        return flag

    @staticmethod
    def _resolve(flag: ReviewFlag, status: ReviewFlagStatus) -> None:
        flag.status = status
        flag.resolved_at = datetime.now(UTC)
