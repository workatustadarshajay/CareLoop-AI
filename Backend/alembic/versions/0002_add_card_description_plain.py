"""add plain-language description to cards

Revision ID: 0002_add_card_description_plain
Revises: 0002_create_review_flags
Create Date: 2026-09-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_add_card_description_plain"
down_revision: Union[str, Sequence[str], None] = "0002_create_review_flags"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cards",
        sa.Column("description_plain", sa.String(length=1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cards", "description_plain")
