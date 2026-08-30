"""Club cover blobs and pending invites."""

from alembic import op
import sqlalchemy as sa

revision = "0015_club_covers_invites"
down_revision = "0014_follow_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "run_clubs",
        sa.Column("cover_data", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "run_clubs",
        sa.Column("cover_content_type", sa.String(length=64), nullable=True),
    )

    op.create_table(
        "club_invites",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("club_id", sa.Integer(), nullable=False),
        sa.Column("inviter_id", sa.Integer(), nullable=False),
        sa.Column("invitee_id", sa.Integer(), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'declined', 'cancelled', 'revoked')",
            name="ck_club_invites_status",
        ),
        sa.ForeignKeyConstraint(
            ["club_id"], ["run_clubs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["inviter_id"], ["athletes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["invitee_id"], ["athletes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_club_invites_token_hash"),
    )
    op.create_index("ix_club_invites_club_id", "club_invites", ["club_id"])
    op.create_index(
        "ix_club_invites_invitee_id", "club_invites", ["invitee_id"]
    )
    op.create_index(
        "ix_club_invites_inviter_id", "club_invites", ["inviter_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_club_invites_inviter_id", table_name="club_invites")
    op.drop_index("ix_club_invites_invitee_id", table_name="club_invites")
    op.drop_index("ix_club_invites_club_id", table_name="club_invites")
    op.drop_table("club_invites")
    op.drop_column("run_clubs", "cover_content_type")
    op.drop_column("run_clubs", "cover_data")
