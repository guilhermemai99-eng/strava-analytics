"""Runs and run participants."""

from alembic import op
import sqlalchemy as sa

revision = "0011_runs"
down_revision = "0010_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column("club_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location_name", sa.String(length=200), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("meeting_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("pace_min_sec", sa.Float(), nullable=True),
        sa.Column("pace_max_sec", sa.Float(), nullable=True),
        sa.Column("run_type", sa.String(length=32), server_default="easy", nullable=False),
        sa.Column("max_participants", sa.Integer(), nullable=True),
        sa.Column("visibility", sa.String(length=32), server_default="everyone", nullable=False),
        sa.Column("route_data", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="scheduled", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("distance_km > 0", name="ck_runs_distance_positive"),
        sa.CheckConstraint(
            "status IN ('scheduled', 'cancelled', 'completed')",
            name="ck_runs_status",
        ),
        sa.CheckConstraint(
            "visibility IN ('everyone', 'followers', 'invite_only')",
            name="ck_runs_visibility",
        ),
        sa.ForeignKeyConstraint(["creator_id"], ["athletes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_runs_creator_id", "runs", ["creator_id"])
    op.create_index("ix_runs_meeting_time", "runs", ["meeting_time"])
    op.create_index("ix_runs_status", "runs", ["status"])
    op.create_index("ix_runs_club_id", "runs", ["club_id"])

    op.create_table(
        "run_participants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="going", nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('going', 'left')",
            name="ck_run_participants_status",
        ),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "athlete_id", name="uq_run_participants_run_athlete"),
    )
    op.create_index("ix_run_participants_run_id", "run_participants", ["run_id"])
    op.create_index("ix_run_participants_athlete_id", "run_participants", ["athlete_id"])


def downgrade() -> None:
    op.drop_index("ix_run_participants_athlete_id", table_name="run_participants")
    op.drop_index("ix_run_participants_run_id", table_name="run_participants")
    op.drop_table("run_participants")
    op.drop_index("ix_runs_club_id", table_name="runs")
    op.drop_index("ix_runs_status", table_name="runs")
    op.drop_index("ix_runs_meeting_time", table_name="runs")
    op.drop_index("ix_runs_creator_id", table_name="runs")
    op.drop_table("runs")
