"""Add idempotency receipts for mobile sync retries.

Revision ID: 005
Revises: 004
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sync_receipts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("sync_id", sa.String(64), nullable=False),
        sa.Column("summary_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime()),
        sa.UniqueConstraint("user_id", "sync_id", name="uq_sync_receipts_user_sync"),
    )
    op.create_index("ix_sync_receipts_user_id", "sync_receipts", ["user_id"])


def downgrade() -> None:
    op.drop_table("sync_receipts")
