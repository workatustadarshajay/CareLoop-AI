from pydantic import BaseModel, Field


class DependencyCreate(BaseModel):
    """Request to create a dependency"""
    upstream_card_id: int = Field(..., gt=0)
    reason: str | None = Field(None, max_length=500)


class CardInfoForDependency(BaseModel):
    """Minimal card info for dependency response"""
    id: int
    description: str
    status: str
    type: str

    class Config:
        from_attributes = True


class DependencyResponse(BaseModel):
    """Single dependency in response"""
    upstream_card_id: int
    upstream_card: CardInfoForDependency
    reason: str | None

    class Config:
        from_attributes = True


class DependenciesListResponse(BaseModel):
    """Response for GET /cards/{id}/dependencies"""
    dependencies: list[DependencyResponse]
    is_at_risk: bool = Field(False)
    at_risk_reason: str | None = Field(None)