from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.card import CardStatus, CardType


class CardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    note_id: int
    type: CardType
    description: str
    description_plain: str | None = None
    status: CardStatus
    risk_reason: str | None = None
    due_at: datetime | None = None
    patient_id: int | None = None
    created_at: datetime
