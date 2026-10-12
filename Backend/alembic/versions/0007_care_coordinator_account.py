"""seed care coordinator account

The care coordinator role (``accounts.role = 'care_coordinator'``) needs no schema
change: ``role`` is a plain varchar(16) and the longest role value fits. This
migration only adds the demo login so the role is reachable from the sign-in screen.

Revision ID: 0007_care_coordinator
Revises: 0006_admin_account
Create Date: 2026-10-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.services.auth import hash_password


revision: str = "0007_care_coordinator"
down_revision: Union[str, Sequence[str], None] = "0006_admin_account"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Test care coordinator (password "password"): chooses any patient, adds the
    # follow-up notes and updates cards. No clinical recommendations, no admin.
    op.bulk_insert(
        sa.table(
            "accounts",
            sa.column("username", sa.String),
            sa.column("password_hash", sa.String),
            sa.column("role", sa.String),
            sa.column("patient_id", sa.Integer),
        ),
        [{"username": "coordinator", "password_hash": hash_password("password"), "role": "care_coordinator", "patient_id": None}],
    )


def downgrade() -> None:
    op.execute("DELETE FROM accounts WHERE username = 'coordinator'")
