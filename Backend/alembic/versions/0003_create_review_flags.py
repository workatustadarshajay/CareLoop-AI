"""create review flags queue

Revision ID: 0002_create_review_flags
Revises: 0001_create_notes_and_cards
Create Date: 2026-09-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM


revision: str = "0002_create_review_flags"
down_revision: Union[str, Sequence[str], None] = "0001_create_notes_and_cards"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Existing enum from 0001; reused, never created or dropped here.
card_type = ENUM(name="card_type", create_type=False)


def upgrade() -> None:
    op.create_table(
        "review_flags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("note_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("diagnosis", sa.String(length=200), nullable=True),
        sa.Column("item_label", sa.String(length=200), nullable=True),
        sa.Column("card_type", card_type, nullable=True),
        sa.Column("card_description", sa.String(length=500), nullable=True),
        sa.Column("created_card_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_card_id"], ["cards.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_flags_note_id", "review_flags", ["note_id"], unique=False)
    op.create_index("ix_review_flags_status", "review_flags", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_review_flags_status", table_name="review_flags")
    op.drop_index("ix_review_flags_note_id", table_name="review_flags")
    op.drop_table("review_flags")
