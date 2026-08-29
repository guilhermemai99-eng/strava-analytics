"""Add coach_messages for Pulse AI Coach chat history.

Revision ID: 0007_coach_messages
Revises: 0006_activity_feed_media
Create Date: 2026-08-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0007_coach_messages"
down_revision = "0006_activity_feed_media"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coach_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "athlete_id",
            sa.Integer(),
            sa.ForeignKey("athletes.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_coach_messages_athlete_created",
        "coach_messages",
        ["athlete_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_coach_messages_athlete_created", table_name="coach_messages")
    op.drop_table("coach_messages")
