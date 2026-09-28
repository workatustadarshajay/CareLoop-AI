"""seed administrator account

Revision ID: 0006_admin_account
Revises: 0005_accounts_reminders
Create Date: 2026-09-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.services.auth import hash_password


revision: str = "0006_admin_account"
down_revision: Union[str, Sequence[str], None] = "0005_accounts_reminders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Test administrator (password "password"): can do everything a doctor can, plus create patients.
    op.bulk_insert(
        sa.table(
            "accounts",
            sa.column("username", sa.String),
            sa.column("password_hash", sa.String),
            sa.column("role", sa.String),
        ),
        [{"username": "admin", "password_hash": hash_password("password"), "role": "admin"}],
    )


def downgrade() -> None:
    op.execute("DELETE FROM accounts WHERE username = 'admin'")
