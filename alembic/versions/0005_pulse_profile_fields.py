"""Add Pulse-owned profile fields: display_name, handle, avatar blob.

Revision ID: 0005_pulse_profile_fields
Revises: 0004_token_encryption_ready
Create Date: 2026-08-29

Keeps Strava columns (username, profile, profile_medium) intact.
handle is Pulse-owned and unique when set (not overwritten by OAuth).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_pulse_profile_fields"
down_revision: Union[str, Sequence[str], None] = "0004_token_encryption_ready"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "athletes",
        sa.Column("display_name", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "athletes",
        sa.Column("handle", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "athletes",
        sa.Column("avatar_data", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "athletes",
        sa.Column("avatar_content_type", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_athletes_handle",
        "athletes",
        ["handle"],
        unique=True,
        postgresql_where=sa.text("handle IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_athletes_handle", table_name="athletes")
    op.drop_column("athletes", "avatar_content_type")
    op.drop_column("athletes", "avatar_data")
    op.drop_column("athletes", "handle")
    op.drop_column("athletes", "display_name")
