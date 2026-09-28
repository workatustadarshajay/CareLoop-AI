from datetime import date

from pydantic import BaseModel

from app.models.card import CardType


class ReminderRead(BaseModel):
    card_id: int
    type: CardType
    message: str
    due_date: date
