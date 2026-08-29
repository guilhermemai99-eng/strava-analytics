"""Add athletes, sessions, oauth_states and athlete FKs.

Revision ID: 0002_athletes_sessions_oauth
Revises: 0001_baseline
Create Date: 2026-08-29

Creates identity/session tables for Foundation V2 without changing the
runtime auth cookie flow yet (that is Phase C/D).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


revision: str = "0002_athletes_sessions_oauth"
down_revision: Union[str, Sequence[str], None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "athletes",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("firstname", sa.String(), nullable=True),
        sa.Column("lastname", sa.String(), nullable=True),
        sa.Column("sex", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("profile", sa.String(), nullable=True),
        sa.Column("profile_medium", sa.String(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column(
            "is_profile_public",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_athletes_id"),
        "athletes",
        ["id"],
        unique=False,
    )

    conn = op.get_bind()

    orphan_activities = conn.execute(
        text("SELECT COUNT(*) FROM activities WHERE athlete_id IS NULL")
    ).scalar()

    if orphan_activities:
        raise RuntimeError(
            "Cannot upgrade to 0002: found "
            f"{orphan_activities} activities with athlete_id IS NULL. "
            "Backfill or delete them before applying this migration."
        )

    orphan_auth = conn.execute(
        text("SELECT COUNT(*) FROM strava_auth WHERE athlete_id IS NULL")
    ).scalar()

    if orphan_auth:
        raise RuntimeError(
            "Cannot upgrade to 0002: found "
            f"{orphan_auth} strava_auth rows with athlete_id IS NULL. "
            "Backfill or delete them before applying this migration."
        )

    # Backfill athletes from known athlete ids (profile fields filled later
    # by OAuth callback in Phase D).
    conn.execute(
        text(
            """
            INSERT INTO athletes (id, is_profile_public, created_at, updated_at)
            SELECT DISTINCT athlete_id, false, NOW(), NOW()
            FROM (
                SELECT athlete_id FROM strava_auth WHERE athlete_id IS NOT NULL
                UNION
                SELECT athlete_id FROM activities WHERE athlete_id IS NOT NULL
            ) AS known_athletes
            ON CONFLICT (id) DO NOTHING
            """
        )
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sessions_athlete_id"),
        "sessions",
        ["athlete_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sessions_id"),
        "sessions",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sessions_token_hash"),
        "sessions",
        ["token_hash"],
        unique=True,
    )

    op.create_table(
        "oauth_states",
        sa.Column("state", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("state"),
    )

    op.alter_column(
        "activities",
        "athlete_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_activities_athlete_id_athletes",
        "activities",
        "athletes",
        ["athlete_id"],
        ["id"],
    )

    op.alter_column(
        "strava_auth",
        "athlete_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_strava_auth_athlete_id_athletes",
        "strava_auth",
        "athletes",
        ["athlete_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_strava_auth_athlete_id_athletes",
        "strava_auth",
        type_="foreignkey",
    )
    op.alter_column(
        "strava_auth",
        "athlete_id",
        existing_type=sa.Integer(),
        nullable=True,
    )

    op.drop_constraint(
        "fk_activities_athlete_id_athletes",
        "activities",
        type_="foreignkey",
    )
    op.alter_column(
        "activities",
        "athlete_id",
        existing_type=sa.Integer(),
        nullable=True,
    )

    op.drop_table("oauth_states")

    op.drop_index(op.f("ix_sessions_token_hash"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_id"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_athlete_id"), table_name="sessions")
    op.drop_table("sessions")

    op.drop_index(op.f("ix_athletes_id"), table_name="athletes")
    op.drop_table("athletes")
