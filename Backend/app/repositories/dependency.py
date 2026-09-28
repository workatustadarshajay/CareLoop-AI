from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.dependency import CardDependency
from app.models.card import Card
from app.schemas.dependency import CardInfoForDependency, DependencyResponse


class DependencyRepository:
    """Data access layer for dependencies"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_with_card_info(
        self, card_id: int
    ) -> list[DependencyResponse]:
        """Get all dependencies with upstream card info"""
        result = await self.db.execute(
            select(CardDependency).where(
                CardDependency.dependent_card_id == card_id
            )
        )
        dependencies = result.scalars().all()

        responses = []
        for dep in dependencies:
            upstream_card = await self.db.get(Card, dep.upstream_card_id)
            if upstream_card:
                responses.append(
                    DependencyResponse(
                        upstream_card_id=dep.upstream_card_id,
                        upstream_card=CardInfoForDependency(
                            id=upstream_card.id,
                            description=upstream_card.description,
                            status=upstream_card.status.value,
                            type=upstream_card.type.value
                        ),
                        reason=dep.reason
                    )
                )

        return responses