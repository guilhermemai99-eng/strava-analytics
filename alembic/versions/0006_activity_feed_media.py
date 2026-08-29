"""Add feed media fields on activities: polyline + Strava photo URL.

Revision ID: 0006_activity_feed_media
Revises: 0005_pulse_profile_fields
Create Date: 2026-08-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0006_activity_feed_media"
down_revision = "0005_pulse_profile_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "activities",
        sa.Column("summary_polyline", sa.Text(), nullable=True),
    )
    op.add_column(
        "activities",
        sa.Column("photo_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "activities",
        sa.Column("photo_count", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("activities", "photo_count")
    op.drop_column("activities", "photo_url")
    op.drop_column("activities", "summary_polyline")
