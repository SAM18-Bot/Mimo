"""Add account auth, device linking, and parent access tables.

Revision ID: 003
Revises: 002
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="student"),
        sa.Column("display_name", sa.String(120)),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("device_name", sa.String(120), nullable=False),
        sa.Column("device_type", sa.String(30), nullable=False),
        sa.Column("platform", sa.String(80)),
        sa.Column("status", sa.String(20), server_default="linked"),
        sa.Column("linked_at", sa.DateTime()),
        sa.Column("last_seen_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_devices_user_id", "devices", ["user_id"])

    op.create_table(
        "parent_invites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("code", sa.String(12), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_parent_invites_code", "parent_invites", ["code"], unique=True)

    op.create_table(
        "parent_student_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_parent_student_links_parent_id", "parent_student_links", ["parent_id"])
    op.create_index("ix_parent_student_links_student_id", "parent_student_links", ["student_id"])


def downgrade() -> None:
    op.drop_table("parent_student_links")
    op.drop_table("parent_invites")
    op.drop_table("devices")
    op.drop_table("users")
