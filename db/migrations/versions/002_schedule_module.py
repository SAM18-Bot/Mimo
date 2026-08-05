"""Add flexible schedule onboarding tables.

Revision ID: 002
Revises: 001
Create Date: 2026-08-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schedule_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("timezone", sa.String(80), server_default="local"),
        sa.Column("wake_time", sa.String(5), nullable=False),
        sa.Column("sleep_time", sa.String(5), nullable=False),
        sa.Column("school_start", sa.String(5)),
        sa.Column("school_end", sa.String(5)),
        sa.Column("study_goal_minutes", sa.Integer(), server_default="120"),
        sa.Column("session_minutes", sa.Integer(), server_default="50"),
        sa.Column("break_minutes", sa.Integer(), server_default="10"),
        sa.Column("active", sa.Boolean(), server_default="1"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("ix_schedule_profiles_active", "schedule_profiles", ["active"])

    op.create_table(
        "schedule_blocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("schedule_profiles.id"), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("block_date", sa.Date()),
        sa.Column("start_time", sa.String(5), nullable=False),
        sa.Column("end_time", sa.String(5), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("subject", sa.String(100)),
        sa.Column("flexibility", sa.String(20), server_default="movable"),
        sa.Column("source", sa.String(30), server_default="onboarding"),
        sa.Column("priority", sa.String(20), server_default="medium"),
        sa.Column("status", sa.String(20), server_default="planned"),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_schedule_blocks_profile_day", "schedule_blocks", ["profile_id", "day_of_week"])


def downgrade() -> None:
    op.drop_table("schedule_blocks")
    op.drop_table("schedule_profiles")
