from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Enum, ForeignKey, String, func, select
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from app.db.base import Base


class CardType(StrEnum):
    MEDICATION = "medication"
    TEST = "test"
    REFERRAL = "referral"
    NEXT_VISIT = "next_visit"
    GENERAL_TASK = "general_task"


class CardStatus(StrEnum):
    OPEN = "open"
    DONE = "done"
    AT_RISK = "at_risk"              
    BLOCKED = "blocked"               
    VERIFIED_CLOSED = "verified_closed"


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[CardType] = mapped_column(
        Enum(
            CardType,
            name="card_type",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    description_plain: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[CardStatus] = mapped_column(
        Enum(
            CardStatus,
            name="card_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        default=CardStatus.OPEN,
        server_default=CardStatus.OPEN.value,
        nullable=False,
    )
    risk_reason: Mapped[str | None] = mapped_column(
        String(500), 
        nullable=True,
        comment="Reason why this card is at risk"
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    note: Mapped["Note"] = relationship(back_populates="cards")


from app.models.note import Note

# Ownership comes from the note; loaded with every card row so no lazy-load in async code.
Card.patient_id = column_property(
    select(Note.patient_id).where(Note.id == Card.note_id).scalar_subquery()
)
