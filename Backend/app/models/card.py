from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
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

    note: Mapped["Note"] = relationship(back_populates="cards")


from app.models.note import Note
