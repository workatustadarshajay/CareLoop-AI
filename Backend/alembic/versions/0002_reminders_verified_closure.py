"""add reminders and verified closure

Revision ID: 0002_reminders_verified_closure
Revises: 0001_create_notes_and_cards
Create Date: 2026-09-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_reminders_verified_closure"
down_revision: Union[str, Sequence[str], None] = "0001_create_notes_and_cards"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE card_status ADD VALUE IF NOT EXISTS 'verified_closed'")
    op.add_column("cards", sa.Column("due_date", sa.Date(), nullable=True))
    op.add_column(
        "cards",
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "cards",
        sa.Column("verified_by_note_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_cards_verified_by_note_id_notes",
        "cards",
        "notes",
        ["verified_by_note_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_cards_status_due_date",
        "cards",
        ["status", "due_date"],
        unique=False,
    )


def downgrade() -> None:
    op.execute("UPDATE cards SET status = 'done' WHERE status = 'verified_closed'")
    op.drop_index("ix_cards_status_due_date", table_name="cards")
    op.drop_constraint(
        "fk_cards_verified_by_note_id_notes",
        "cards",
        type_="foreignkey",
    )
    op.drop_column("cards", "verified_by_note_id")
    op.drop_column("cards", "verified_at")
    op.drop_column("cards", "due_date")
    op.execute("ALTER TABLE cards ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE cards ALTER COLUMN status TYPE VARCHAR USING status::text"
    )
    op.execute("DROP TYPE card_status")
    op.execute("CREATE TYPE card_status AS ENUM ('open', 'done')")
    op.execute(
        "ALTER TABLE cards ALTER COLUMN status TYPE card_status "
        "USING status::card_status"
    )
    op.execute(
        "ALTER TABLE cards ALTER COLUMN status SET DEFAULT 'open'::card_status"
    )
