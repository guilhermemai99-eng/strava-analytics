"""Add token_version and updated_at for Strava token encryption.

Revision ID: 0004_token_encryption_ready
Revises: 0003_strava_id_bigint
Create Date: 2026-08-29

Schema-only. Existing rows stay token_version=0 (plaintext dual-read).
New writes encrypt and set token_version=1. Bulk encrypt via
scripts/encrypt_strava_tokens.py — not inside this migration.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_token_encryption_ready"
down_revision: Union[str, Sequence[str], None] = "0003_strava_id_bigint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "strava_auth",
        sa.Column(
            "token_version",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "strava_auth",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("strava_auth", "updated_at")
    op.drop_column("strava_auth", "token_version")
