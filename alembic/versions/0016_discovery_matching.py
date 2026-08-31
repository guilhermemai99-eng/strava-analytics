"""Discovery swipes, matches, and preferences."""

from alembic import op
import sqlalchemy as sa

revision = "0016_discovery_matching"
down_revision = "0015_club_covers_invites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "discovery_preferences",
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("radius_km", sa.Integer(), server_default="25", nullable=False),
        sa.Column(
            "location_mode",
            sa.String(length=16),
            server_default="city",
            nullable=False,
        ),
        sa.Column("manual_city", sa.String(length=120), nullable=True),
        sa.Column("manual_country", sa.String(length=120), nullable=True),
        sa.Column("private_lat", sa.Float(), nullable=True),
        sa.Column("private_lng", sa.Float(), nullable=True),
        sa.Column("pace_min_sec", sa.Float(), nullable=True),
        sa.Column("pace_max_sec", sa.Float(), nullable=True),
        sa.Column("distance_min_km", sa.Float(), nullable=True),
        sa.Column("distance_max_km", sa.Float(), nullable=True),
        sa.Column("available_days", sa.String(length=64), nullable=True),
        sa.Column("goals", sa.String(length=256), nullable=True),
        sa.Column(
            "show_goals",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
        sa.Column(
            "show_availability",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
        sa.Column("discovery_bio", sa.String(length=280), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("athlete_id"),
    )
    op.create_table(
        "discovery_swipes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("from_athlete_id", sa.Integer(), nullable=False),
        sa.Column("to_athlete_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["from_athlete_id"], ["athletes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["to_athlete_id"], ["athletes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "from_athlete_id",
            "to_athlete_id",
            name="uq_discovery_swipe_pair",
        ),
    )
    op.create_index(
        "ix_discovery_swipes_from_athlete_id",
        "discovery_swipes",
        ["from_athlete_id"],
    )
    op.create_index(
        "ix_discovery_swipes_to_athlete_id",
        "discovery_swipes",
        ["to_athlete_id"],
    )
    op.create_index(
        "ix_discovery_swipes_created_at",
        "discovery_swipes",
        ["created_at"],
    )
    op.create_table(
        "discovery_matches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("athlete_a_id", sa.Integer(), nullable=False),
        sa.Column("athlete_b_id", sa.Integer(), nullable=False),
        sa.Column("pair_key", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["athlete_a_id"], ["athletes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["athlete_b_id"], ["athletes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pair_key", name="uq_discovery_match_pair"),
    )
    op.create_index(
        "ix_discovery_matches_athlete_a_id",
        "discovery_matches",
        ["athlete_a_id"],
    )
    op.create_index(
        "ix_discovery_matches_athlete_b_id",
        "discovery_matches",
        ["athlete_b_id"],
    )
    op.create_index(
        "ix_discovery_matches_created_at",
        "discovery_matches",
        ["created_at"],
    )
    op.add_column(
        "conversations",
        sa.Column(
            "conversation_type",
            sa.String(length=16),
            server_default="direct",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("conversations", "conversation_type")
    op.drop_index("ix_discovery_matches_created_at", table_name="discovery_matches")
    op.drop_index("ix_discovery_matches_athlete_b_id", table_name="discovery_matches")
    op.drop_index("ix_discovery_matches_athlete_a_id", table_name="discovery_matches")
    op.drop_table("discovery_matches")
    op.drop_index("ix_discovery_swipes_created_at", table_name="discovery_swipes")
    op.drop_index("ix_discovery_swipes_to_athlete_id", table_name="discovery_swipes")
    op.drop_index("ix_discovery_swipes_from_athlete_id", table_name="discovery_swipes")
    op.drop_table("discovery_swipes")
    op.drop_table("discovery_preferences")
