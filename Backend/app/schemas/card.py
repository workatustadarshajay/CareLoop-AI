from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.card import CardStatus, CardType


class CardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    note_id: int
    type: CardType
    description: str
    due_date: date | None
    status: CardStatus
    created_at: datetime
    verified_at: datetime | None
    verified_by_note_id: int | None
