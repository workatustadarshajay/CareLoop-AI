"""accounts, patients, note ownership, card due dates, reminders

Merges the two previous heads (plain-language descriptions and card
dependencies) so `alembic upgrade head` is single-headed again.

Revision ID: 0005_accounts_reminders
Revises: 0002_add_card_description_plain, 0003_add_card_dependencies
Create Date: 2026-09-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.services.auth import hash_password


revision: str = "0005_accounts_reminders"
down_revision: Union[str, Sequence[str], None] = (
    "0002_add_card_description_plain",
    "0003_add_card_dependencies",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=True),
        sa.Column("token", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_accounts_token", "accounts", ["token"])

    op.add_column("notes", sa.Column("patient_id", sa.Integer(), nullable=True))
    op.create_foreign_key("notes_patient_id_fkey", "notes", "patients", ["patient_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_notes_patient_id", "notes", ["patient_id"])

    op.add_column("cards", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.String(600), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("card_id"),
    )

    # Test accounts (password for all: "password").
    op.bulk_insert(
        sa.table("patients", sa.column("id", sa.Integer), sa.column("name", sa.String)),
        [{"id": 1, "name": "Alice Johnson"}, {"id": 2, "name": "Bob Lee"}],
    )
    op.execute("SELECT setval('patients_id_seq', 2)")
    op.bulk_insert(
        sa.table(
            "accounts",
            sa.column("username", sa.String),
            sa.column("password_hash", sa.String),
            sa.column("role", sa.String),
            sa.column("patient_id", sa.Integer),
        ),
        [
            {"username": "dr_smith", "password_hash": hash_password("password"), "role": "doctor", "patient_id": None},
            {"username": "alice", "password_hash": hash_password("password"), "role": "patient", "patient_id": 1},
            {"username": "bob", "password_hash": hash_password("password"), "role": "patient", "patient_id": 2},
        ],
    )


def downgrade() -> None:
    op.drop_table("reminders")
    op.drop_column("cards", "due_at")
    op.drop_index("ix_notes_patient_id", table_name="notes")
    op.drop_constraint("notes_patient_id_fkey", "notes", type_="foreignkey")
    op.drop_column("notes", "patient_id")
    op.drop_index("ix_accounts_token", table_name="accounts")
    op.drop_table("accounts")
    op.drop_table("patients")
