from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Role(StrEnum):
    PATIENT = "patient"  # read-only: sees their own cards and reminders
    CARE_COORDINATOR = "care_coordinator"  # works on any patient's plan, but makes no clinical calls
    DOCTOR = "doctor"
    ADMIN = "admin"  # everything a doctor can do, plus managing patients/accounts


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    # length=16: the longest role value ("care_coordinator") must fit the column.
    role: Mapped[Role] = mapped_column(
        Enum(Role, native_enum=False, length=16, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    # Set only for patient accounts: which patient this login belongs to.
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    # ponytail: single bearer token per account, no expiry; add a sessions table if multi-device login matters.
    token: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
