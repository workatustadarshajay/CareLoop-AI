from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.card import CardType
from app.models.review_flag import ReviewFlagKind, ReviewFlagStatus


class ReviewFlagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    note_id: int
    kind: ReviewFlagKind
    status: ReviewFlagStatus
    reason: str
    diagnosis: str | None
    item_label: str | None
    card_type: CardType | None
    card_description: str | None
    created_at: datetime
