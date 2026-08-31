"""Discovery swipes, matches, and viewer preferences (Tinder-style people discovery)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from database import Base


def utcnow():
    return datetime.now(timezone.utc)


class DiscoveryPreference(Base):
    """Viewer discovery settings. Private coords never exposed via API."""

    __tablename__ = "discovery_preferences"

    athlete_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    radius_km = Column(Integer, nullable=False, default=25, server_default="25")
    location_mode = Column(
        String(16),
        nullable=False,
        default="city",
        server_default="city",
    )
    manual_city = Column(String(120), nullable=True)
    manual_country = Column(String(120), nullable=True)
    private_lat = Column(Float, nullable=True)
    private_lng = Column(Float, nullable=True)
    pace_min_sec = Column(Float, nullable=True)
    pace_max_sec = Column(Float, nullable=True)
    distance_min_km = Column(Float, nullable=True)
    distance_max_km = Column(Float, nullable=True)
    available_days = Column(String(64), nullable=True)
    goals = Column(String(256), nullable=True)
    show_goals = Column(Boolean, nullable=False, default=True, server_default="true")
    show_availability = Column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    discovery_bio = Column(String(280), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class DiscoverySwipe(Base):
    """Like or pass on another runner."""

    __tablename__ = "discovery_swipes"
    __table_args__ = (
        UniqueConstraint(
            "from_athlete_id",
            "to_athlete_id",
            name="uq_discovery_swipe_pair",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_athlete_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    to_athlete_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action = Column(String(8), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )


class DiscoveryMatch(Base):
    """Mutual like between two runners."""

    __tablename__ = "discovery_matches"
    __table_args__ = (
        UniqueConstraint("pair_key", name="uq_discovery_match_pair"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_a_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    athlete_b_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pair_key = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )
