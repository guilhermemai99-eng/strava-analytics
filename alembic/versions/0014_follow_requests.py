"""Pending follow requests for private profiles."""

from alembic import op
import sqlalchemy as sa

revision = "0014_follow_requests"
down_revision = "0013_activity_social"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "follow_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("requester_id", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "requester_id <> target_id",
            name="ck_follow_requests_no_self",
        ),
        sa.ForeignKeyConstraint(
            ["requester_id"], ["athletes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_id"], ["athletes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "requester_id",
            "target_id",
            name="uq_follow_requests_requester_target",
        ),
    )
    op.create_index(
        "ix_follow_requests_requester_id",
        "follow_requests",
        ["requester_id"],
    )
    op.create_index(
        "ix_follow_requests_target_id",
        "follow_requests",
        ["target_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_follow_requests_target_id", table_name="follow_requests")
    op.drop_index(
        "ix_follow_requests_requester_id", table_name="follow_requests"
    )
    op.drop_table("follow_requests")
