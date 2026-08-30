"""Pending follow requests for private profiles."""

from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
)

from database import Base


def utcnow():
    return datetime.now(timezone.utc)


class FollowRequest(Base):
    __tablename__ = "follow_requests"
    __table_args__ = (
        UniqueConstraint(
            "requester_id",
            "target_id",
            name="uq_follow_requests_requester_target",
        ),
        CheckConstraint(
            "requester_id <> target_id",
            name="ck_follow_requests_no_self",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    requester_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
