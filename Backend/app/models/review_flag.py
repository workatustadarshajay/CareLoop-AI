from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.card import CardType


class ReviewFlagKind(StrEnum):
    MISSING_ITEM = "missing_item"


class ReviewFlagStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DISMISSED = "dismissed"


def _values(enum: type[StrEnum]) -> list[str]:
    return [member.value for member in enum]


class ReviewFlag(Base):
    __tablename__ = "review_flags"

    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[ReviewFlagKind] = mapped_column(
        Enum(ReviewFlagKind, native_enum=False, length=32, values_callable=_values),
        nullable=False,
    )
    status: Mapped[ReviewFlagStatus] = mapped_column(
        Enum(ReviewFlagStatus, native_enum=False, length=16, values_callable=_values),
        default=ReviewFlagStatus.PENDING,
        server_default=ReviewFlagStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    # Suggested card for missing_item flags; other kinds may leave these empty.
    diagnosis: Mapped[str | None] = mapped_column(String(200))
    item_label: Mapped[str | None] = mapped_column(String(200))
    card_type: Mapped[CardType | None] = mapped_column(
        Enum(CardType, name="card_type", values_callable=_values),
    )
    card_description: Mapped[str | None] = mapped_column(String(500))
    created_card_id: Mapped[int | None] = mapped_column(ForeignKey("cards.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
