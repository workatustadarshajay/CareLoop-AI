from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    VERIFIED_CLOSED = "verified_closed"


class Card(Base):
    __tablename__ = "cards"
    __table_args__ = (Index("ix_cards_status_due_date", "status", "due_date"),)

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
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    verified_by_note_id: Mapped[int | None] = mapped_column(
        ForeignKey("notes.id", ondelete="SET NULL"),
        nullable=True,
    )

    note: Mapped["Note"] = relationship(
        back_populates="cards",
        foreign_keys=[note_id],
    )


from app.models.note import Note
