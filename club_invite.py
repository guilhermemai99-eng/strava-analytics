"""Pending club invites (direct + shareable link)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


INVITE_STATUSES = ("pending", "accepted", "declined", "cancelled", "revoked")


class ClubInvite(Base):
    __tablename__ = "club_invites"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'accepted', 'declined', 'cancelled', 'revoked')",
            name="ck_club_invites_status",
        ),
        UniqueConstraint("token_hash", name="uq_club_invites_token_hash"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    club_id = Column(
        Integer,
        ForeignKey("run_clubs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inviter_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Null for shareable invite links (token_hash set).
    invitee_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    token_hash = Column(String(64), nullable=True)
    status = Column(
        String(16),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
