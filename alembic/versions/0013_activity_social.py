"""Activity likes, comments, hide, privacy, reports."""

from alembic import op
import sqlalchemy as sa

revision = "0013_activity_social"
down_revision = "0012_run_clubs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "activities",
        sa.Column(
            "visibility",
            sa.String(length=16),
            server_default="public",
            nullable=False,
        ),
    )
    op.add_column("activities", sa.Column("caption", sa.Text(), nullable=True))
    op.add_column(
        "activities",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_activities_visibility",
        "activities",
        "visibility IN ('public', 'followers', 'private')",
    )

    op.create_table(
        "activity_likes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "activity_id", "athlete_id", name="uq_activity_likes_activity_athlete"
        ),
    )
    op.create_index("ix_activity_likes_activity_id", "activity_likes", ["activity_id"])
    op.create_index("ix_activity_likes_athlete_id", "activity_likes", ["athlete_id"])

    op.create_table(
        "activity_comments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_activity_comments_activity_id", "activity_comments", ["activity_id"]
    )
    op.create_index(
        "ix_activity_comments_athlete_id", "activity_comments", ["athlete_id"]
    )

    op.create_table(
        "hidden_activities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "athlete_id", "activity_id", name="uq_hidden_activities_athlete_activity"
        ),
    )
    op.create_index(
        "ix_hidden_activities_athlete_id", "hidden_activities", ["athlete_id"]
    )
    op.create_index(
        "ix_hidden_activities_activity_id", "hidden_activities", ["activity_id"]
    )

    op.create_table(
        "activity_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.Column("reporter_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_id"], ["athletes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "activity_id", "reporter_id", name="uq_activity_reports_activity_reporter"
        ),
    )
    op.create_index(
        "ix_activity_reports_activity_id", "activity_reports", ["activity_id"]
    )
    op.create_index(
        "ix_activity_reports_reporter_id", "activity_reports", ["reporter_id"]
    )


def downgrade() -> None:
    op.drop_table("activity_reports")
    op.drop_table("hidden_activities")
    op.drop_table("activity_comments")
    op.drop_table("activity_likes")
    op.drop_constraint("ck_activities_visibility", "activities", type_="check")
    op.drop_column("activities", "deleted_at")
    op.drop_column("activities", "caption")
    op.drop_column("activities", "visibility")
