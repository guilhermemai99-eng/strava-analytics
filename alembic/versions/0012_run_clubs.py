"""Run clubs and club members."""

from alembic import op
import sqlalchemy as sa

revision = "0012_run_clubs"
down_revision = "0011_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "run_clubs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location_name", sa.String(length=200), nullable=True),
        sa.Column("cover_url", sa.String(length=500), nullable=True),
        sa.Column("visibility", sa.String(length=16), server_default="public", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "visibility IN ('public', 'private')",
            name="ck_run_clubs_visibility",
        ),
        sa.ForeignKeyConstraint(["creator_id"], ["athletes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_run_clubs_creator_id", "run_clubs", ["creator_id"])

    op.create_table(
        "club_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("club_id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), server_default="member", nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ('owner', 'admin', 'member')",
            name="ck_club_members_role",
        ),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["run_clubs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("club_id", "athlete_id", name="uq_club_members_club_athlete"),
    )
    op.create_index("ix_club_members_club_id", "club_members", ["club_id"])
    op.create_index("ix_club_members_athlete_id", "club_members", ["athlete_id"])

    op.create_foreign_key(
        "fk_runs_club_id_run_clubs",
        "runs",
        "run_clubs",
        ["club_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_runs_club_id_run_clubs", "runs", type_="foreignkey")
    op.drop_index("ix_club_members_athlete_id", table_name="club_members")
    op.drop_index("ix_club_members_club_id", table_name="club_members")
    op.drop_table("club_members")
    op.drop_index("ix_run_clubs_creator_id", table_name="run_clubs")
    op.drop_table("run_clubs")
