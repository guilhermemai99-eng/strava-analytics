"""Organized social runs — creator, participants, pace, visibility."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


RUN_TYPES = (
    "easy",
    "long",
    "tempo",
    "intervals",
    "recovery",
    "trail",
    "social",
)

RUN_VISIBILITIES = ("everyone", "followers", "invite_only")
RUN_STATUSES = ("scheduled", "cancelled", "completed")
PARTICIPANT_STATUSES = ("going", "left")


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (
        CheckConstraint(
            "distance_km > 0",
            name="ck_runs_distance_positive",
        ),
        CheckConstraint(
            "status IN ('scheduled', 'cancelled', 'completed')",
            name="ck_runs_status",
        ),
        CheckConstraint(
            "visibility IN ('everyone', 'followers', 'invite_only')",
            name="ck_runs_visibility",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id = Column(
        Integer,
        ForeignKey("run_clubs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    location_name = Column(String(200), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    meeting_time = Column(DateTime(timezone=True), nullable=False, index=True)
    distance_km = Column(Float, nullable=False)
    pace_min_sec = Column(Float, nullable=True)
    pace_max_sec = Column(Float, nullable=True)
    run_type = Column(String(32), nullable=False, default="easy", server_default="easy")

    max_participants = Column(Integer, nullable=True)
    visibility = Column(
        String(32),
        nullable=False,
        default="everyone",
        server_default="everyone",
    )
    route_data = Column(Text, nullable=True)
    status = Column(
        String(32),
        nullable=False,
        default="scheduled",
        server_default="scheduled",
        index=True,
    )

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    participants = relationship(
        "RunParticipant",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class RunParticipant(Base):
    __tablename__ = "run_participants"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "athlete_id",
            name="uq_run_participants_run_athlete",
        ),
        CheckConstraint(
            "status IN ('going', 'left')",
            name="ck_run_participants_status",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(
        Integer,
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    athlete_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        String(16),
        nullable=False,
        default="going",
        server_default="going",
    )
    joined_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    run = relationship("Run", back_populates="participants")
