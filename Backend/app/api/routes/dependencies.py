from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.dependency_service import DependencyService
from app.repositories.dependency import DependencyRepository
from app.schemas.dependency import (
    DependencyCreate,
    DependenciesListResponse,
    DependencyResponse,
)

router = APIRouter(prefix="/cards", tags=["dependencies"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/{card_id}/dependencies", status_code=status.HTTP_201_CREATED)
async def create_dependency(
    card_id: int,
    payload: DependencyCreate,
    db: DbSession
) -> dict:
    """
    Create a dependency: card_id depends on upstream_card_id

    Example:
    - "Follow-up with Neurology" (card_id) depends on "Complete MRI" (upstream_card_id)
    """
    try:
        service = DependencyService(db)
        await service.create_dependency(
            dependent_card_id=card_id,
            upstream_card_id=payload.upstream_card_id,
            reason=payload.reason
        )
        await db.commit()
        return {"success": True, "message": "Dependency created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{card_id}/dependencies", response_model=DependenciesListResponse)
async def get_dependencies(card_id: int, db: DbSession) -> DependenciesListResponse:
    """
    Get all dependencies for a card, including risk status.
    """
    try:
        service = DependencyService(db)
        repo = DependencyRepository(db)

        # Get dependency list with card info
        dependencies = await repo.get_with_card_info(card_id)

        # Check if at risk
        is_at_risk, reason = await service.check_card_at_risk(card_id)

        return DependenciesListResponse(
            dependencies=dependencies,
            is_at_risk=is_at_risk,
            at_risk_reason=reason
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{card_id}/dependencies/{upstream_card_id}")
async def delete_dependency(
    card_id: int,
    upstream_card_id: int,
    db: DbSession
) -> dict:
    """Delete a dependency link"""
    try:
        service = DependencyService(db)
        await service.delete_dependency(card_id, upstream_card_id)
        await db.commit()
        return {"success": True, "message": "Dependency deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))