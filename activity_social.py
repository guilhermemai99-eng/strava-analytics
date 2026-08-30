"""Likes, comments, hidden posts, and activity reports."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)

from database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


ACTIVITY_VISIBILITIES = ("public", "followers", "private")


class ActivityLike(Base):
    __tablename__ = "activity_likes"
    __table_args__ = (
        UniqueConstraint(
            "activity_id",
            "athlete_id",
            name="uq_activity_likes_activity_athlete",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_id = Column(
        Integer,
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    athlete_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class ActivityComment(Base):
    __tablename__ = "activity_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_id = Column(
        Integer,
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    athlete_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class HiddenActivity(Base):
    __tablename__ = "hidden_activities"
    __table_args__ = (
        UniqueConstraint(
            "athlete_id",
            "activity_id",
            name="uq_hidden_activities_athlete_activity",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_id = Column(
        Integer,
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class ActivityReport(Base):
    __tablename__ = "activity_reports"
    __table_args__ = (
        UniqueConstraint(
            "activity_id",
            "reporter_id",
            name="uq_activity_reports_activity_reporter",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_id = Column(
        Integer,
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reporter_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
