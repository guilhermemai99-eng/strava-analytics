"""Run clubs — membership and club-hosted runs."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
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


CLUB_VISIBILITIES = ("public", "private")
CLUB_ROLES = ("owner", "admin", "member")


class RunClub(Base):
    __tablename__ = "run_clubs"
    __table_args__ = (
        CheckConstraint(
            "visibility IN ('public', 'private')",
            name="ck_run_clubs_visibility",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    location_name = Column(String(200), nullable=True)
    cover_url = Column(String(500), nullable=True)
    visibility = Column(
        String(16),
        nullable=False,
        default="public",
        server_default="public",
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    members = relationship(
        "ClubMember",
        back_populates="club",
        cascade="all, delete-orphan",
    )


class ClubMember(Base):
    __tablename__ = "club_members"
    __table_args__ = (
        UniqueConstraint(
            "club_id",
            "athlete_id",
            name="uq_club_members_club_athlete",
        ),
        CheckConstraint(
            "role IN ('owner', 'admin', 'member')",
            name="ck_club_members_role",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    club_id = Column(
        Integer,
        ForeignKey("run_clubs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    athlete_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(
        String(16),
        nullable=False,
        default="member",
        server_default="member",
    )
    joined_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    club = relationship("RunClub", back_populates="members")
