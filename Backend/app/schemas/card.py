from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.card import CardStatus, CardType


class CardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    note_id: int
    type: CardType
    description: str
    status: CardStatus
    created_at: datetime
