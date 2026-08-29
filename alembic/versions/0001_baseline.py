"""Baseline schema: activities and strava_auth.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-08-29

Captures the schema that previously relied on Base.metadata.create_all.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "activities",
        sa.Column("athlete_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("strava_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("sport_type", sa.String(), nullable=True),
        sa.Column("distance_m", sa.Float(), nullable=True),
        sa.Column("moving_time_s", sa.Integer(), nullable=True),
        sa.Column("elapsed_time_s", sa.Integer(), nullable=True),
        sa.Column("elevation_gain_m", sa.Float(), nullable=True),
        sa.Column("elev_high", sa.Float(), nullable=True),
        sa.Column("elev_low", sa.Float(), nullable=True),
        sa.Column("average_speed_m_s", sa.Float(), nullable=True),
        sa.Column("max_speed_m_s", sa.Float(), nullable=True),
        sa.Column("start_date", sa.String(), nullable=True),
        sa.Column("start_date_local", sa.String(), nullable=True),
        sa.Column("timezone", sa.String(), nullable=True),
        sa.Column("device_name", sa.String(), nullable=True),
        sa.Column("kudos_count", sa.Integer(), nullable=True),
        sa.Column("achievement_count", sa.Integer(), nullable=True),
        sa.Column("average_temp", sa.Float(), nullable=True),
        sa.Column("has_heartrate", sa.Boolean(), nullable=True),
        sa.Column("start_lat", sa.Float(), nullable=True),
        sa.Column("start_lng", sa.Float(), nullable=True),
        sa.Column("end_lat", sa.Float(), nullable=True),
        sa.Column("end_lng", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_activities_athlete_id"),
        "activities",
        ["athlete_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_activities_id"),
        "activities",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_activities_strava_id"),
        "activities",
        ["strava_id"],
        unique=True,
    )

    op.create_table(
        "strava_auth",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=True),
        sa.Column("access_token", sa.String(), nullable=True),
        sa.Column("refresh_token", sa.String(), nullable=True),
        sa.Column("expires_at", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_strava_auth_athlete_id"),
        "strava_auth",
        ["athlete_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_strava_auth_athlete_id"),
        table_name="strava_auth",
    )
    op.drop_table("strava_auth")
    op.drop_index(
        op.f("ix_activities_strava_id"),
        table_name="activities",
    )
    op.drop_index(
        op.f("ix_activities_id"),
        table_name="activities",
    )
    op.drop_index(
        op.f("ix_activities_athlete_id"),
        table_name="activities",
    )
    op.drop_table("activities")
