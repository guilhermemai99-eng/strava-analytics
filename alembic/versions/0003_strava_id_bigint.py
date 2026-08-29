"""Widen activities.strava_id to BIGINT.

Revision ID: 0003_strava_id_bigint
Revises: 0002_athletes_sessions_oauth
Create Date: 2026-08-29

Strava activity IDs (e.g. 19937461614) exceed PostgreSQL INTEGER
(max 2147483647), which caused sync to fail with NumericValueOutOfRange.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_strava_id_bigint"
down_revision: Union[str, Sequence[str], None] = "0002_athletes_sessions_oauth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "activities",
        "strava_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "activities",
        "strava_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
