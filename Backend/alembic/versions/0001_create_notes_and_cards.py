"""create notes and cards

Revision ID: 0001_create_notes_and_cards
Revises:
Create Date: 2026-09-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM


revision: str = "0001_create_notes_and_cards"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


card_type = ENUM(
    "medication",
    "test",
    "referral",
    "next_visit",
    "general_task",
    name="card_type",
    create_type=False,
)
card_status = ENUM("open", "done", name="card_status", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    card_type.create(bind, checkfirst=True)
    card_status.create(bind, checkfirst=True)

    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("note_id", sa.Integer(), nullable=False),
        sa.Column("type", card_type, nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column(
            "status",
            card_status,
            server_default=sa.text("'open'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cards_note_id", "cards", ["note_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_cards_note_id", table_name="cards")
    op.drop_table("cards")
    op.drop_table("notes")
    card_status.drop(op.get_bind(), checkfirst=True)
    card_type.drop(op.get_bind(), checkfirst=True)
