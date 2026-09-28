from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.card import Card, CardStatus
from app.models.dependency import CardDependency


class DependencyService:
    """Business logic for card dependencies and risk detection"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_dependency(
        self,
        dependent_card_id: int,
        upstream_card_id: int,
        reason: str | None = None
    ) -> CardDependency:
        """Create a new dependency link"""
        # Validate both cards exist
        dependent = await self.db.get(Card, dependent_card_id)
        upstream = await self.db.get(Card, upstream_card_id)

        if not dependent or not upstream:
            raise ValueError("One or both cards not found")

        if dependent_card_id == upstream_card_id:
            raise ValueError("A card cannot depend on itself")

        # Check if dependency already exists
        existing = await self.db.execute(
            select(CardDependency).where(
                CardDependency.dependent_card_id == dependent_card_id,
                CardDependency.upstream_card_id == upstream_card_id
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("This dependency already exists")

        # Create dependency
        new_dep = CardDependency(
            dependent_card_id=dependent_card_id,
            upstream_card_id=upstream_card_id,
            reason=reason
        )
        self.db.add(new_dep)
        await self.db.flush()

        # Update risk status
        await self._update_risk_status(dependent_card_id)

        return new_dep

    async def get_dependencies_for_card(self, card_id: int) -> list[CardDependency]:
        """Get all upstream dependencies for a card"""
        result = await self.db.execute(
            select(CardDependency).where(
                CardDependency.dependent_card_id == card_id
            )
        )
        return result.scalars().all()

    async def delete_dependency(
        self,
        dependent_card_id: int,
        upstream_card_id: int
    ) -> bool:
        """Delete a dependency and re-check risk status"""
        result = await self.db.execute(
            select(CardDependency).where(
                CardDependency.dependent_card_id == dependent_card_id,
                CardDependency.upstream_card_id == upstream_card_id
            )
        )
        dep = result.scalar_one_or_none()

        if not dep:
            raise ValueError("Dependency not found")

        await self.db.delete(dep)
        await self.db.flush()

        # Re-check risk status
        await self._update_risk_status(dependent_card_id)

        return True

    async def check_card_at_risk(
        self, card_id: int
    ) -> tuple[bool, str | None]:
        """
        Check if a card is at risk due to incomplete upstream dependencies.

        Returns: (is_at_risk: bool, reason: str | None)
        """
        # Get all upstream dependencies
        deps = await self.get_dependencies_for_card(card_id)

        for dep in deps:
            upstream_card = await self.db.get(Card, dep.upstream_card_id)

            # If upstream card is NOT completed, this card is at risk
            if upstream_card.status not in [
                CardStatus.DONE,
                CardStatus.VERIFIED_CLOSED
            ]:
                return True, f"Depends on '{upstream_card.description}' (status: {upstream_card.status})"

        return False, None

    async def _update_risk_status(self, card_id: int) -> None:
        """
        Auto-update card's status and risk_reason based on dependencies.
        Called after dependency creation/deletion.
        """
        card = await self.db.get(Card, card_id)
        if not card:
            return

        is_at_risk, reason = await self.check_card_at_risk(card_id)

        if is_at_risk:
            # Only update if not already in a terminal state
            if card.status not in [CardStatus.DONE, CardStatus.VERIFIED_CLOSED]:
                card.status = CardStatus.AT_RISK
                card.risk_reason = reason
        else:
            # If it was at risk and now isn't, revert to OPEN
            if card.status == CardStatus.AT_RISK:
                card.status = CardStatus.OPEN
                card.risk_reason = None

        await self.db.flush()

    async def propagate_risk_updates(self, completed_card_id: int) -> None:
        """
        When a card is marked as DONE/VERIFIED_CLOSED,
        re-check all cards that depend on it.
        """
        # Find all cards that depend on this card
        result = await self.db.execute(
            select(CardDependency).where(
                CardDependency.upstream_card_id == completed_card_id
            )
        )
        dependents = result.scalars().all()

        for dep in dependents:
            await self._update_risk_status(dep.dependent_card_id)