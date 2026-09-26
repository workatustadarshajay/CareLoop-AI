from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_flag import ReviewFlag, ReviewFlagStatus


class ReviewFlagRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_all(self, flags: list[ReviewFlag]) -> None:
        self.session.add_all(flags)
        await self.session.flush()

    async def list_pending(self) -> list[ReviewFlag]:
        result = await self.session.execute(
            select(ReviewFlag)
            .where(ReviewFlag.status == ReviewFlagStatus.PENDING)
            .order_by(ReviewFlag.created_at.desc(), ReviewFlag.id.desc())
        )
        return list(result.scalars().all())

    async def get_pending_for_update(self, flag_id: int) -> ReviewFlag | None:
        result = await self.session.execute(
            select(ReviewFlag)
            .where(ReviewFlag.id == flag_id, ReviewFlag.status == ReviewFlagStatus.PENDING)
            .with_for_update()
        )
        return result.scalar_one_or_none()
