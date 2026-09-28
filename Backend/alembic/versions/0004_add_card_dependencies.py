"""add card dependencies and risk flags

Revision ID: 0003_add_card_dependencies
Revises: 0002_create_review_flags
Create Date: 2026-09-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_add_card_dependencies"
down_revision: Union[str, Sequence[str], None] = "0002_create_review_flags"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add risk_reason column to cards table
    op.add_column(
        'cards',
        sa.Column('risk_reason', sa.String(500), nullable=True)
    )

    # Drop the default first
    op.execute("ALTER TABLE cards ALTER COLUMN status DROP DEFAULT")

    # Create the new card_status enum with all values
    op.execute("CREATE TYPE card_status_new AS ENUM ('open', 'done', 'at_risk', 'blocked', 'verified_closed')")

    # Alter the column type
    op.execute("ALTER TABLE cards ALTER COLUMN status TYPE card_status_new USING status::text::card_status_new")

    # Add the default back
    op.execute("ALTER TABLE cards ALTER COLUMN status SET DEFAULT 'open'::card_status_new")

    # Drop the old enum
    op.execute("DROP TYPE card_status")

    # Rename the new enum to the old name
    op.execute("ALTER TYPE card_status_new RENAME TO card_status")

    # Create card_dependencies table
    op.create_table(
        'card_dependencies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dependent_card_id', sa.Integer(), nullable=False),
        sa.Column('upstream_card_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['dependent_card_id'], ['cards.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['upstream_card_id'], ['cards.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dependent_card_id', 'upstream_card_id',
                            name='uq_card_dependency_pair')
    )

    op.create_index(
        'ix_card_dependencies_dependent_card_id',
        'card_dependencies',
        ['dependent_card_id']
    )
    op.create_index(
        'ix_card_dependencies_upstream_card_id',
        'card_dependencies',
        ['upstream_card_id']
    )
def downgrade() -> None:
    op.drop_index("ix_card_dependencies_upstream_card_id")
    op.drop_index("ix_card_dependencies_dependent_card_id")
    op.drop_table("card_dependencies")

    op.execute(
        "UPDATE cards SET status = 'open' WHERE status IN ('at_risk', 'blocked')"
    )
    op.execute("UPDATE cards SET status = 'done' WHERE status = 'verified_closed'")
    op.execute("ALTER TABLE cards ALTER COLUMN status DROP DEFAULT")
    sa.Enum("open", "done", name="card_status_old").create(op.get_bind())
    op.execute(
        "ALTER TABLE cards ALTER COLUMN status TYPE card_status_old "
        "USING status::text::card_status_old"
    )
    op.execute("DROP TYPE card_status")
    op.execute("ALTER TYPE card_status_old RENAME TO card_status")
    op.execute(
        "ALTER TABLE cards ALTER COLUMN status SET DEFAULT 'open'::card_status"
    )
    op.drop_column("cards", "risk_reason")
