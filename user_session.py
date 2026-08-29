from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from database import Base


def utcnow():
    return datetime.now(timezone.utc)


class UserSession(Base):
    """Server-side session. Cookie stores the raw token; DB stores the hash."""

    __tablename__ = "sessions"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    token_hash = Column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )

    athlete_id = Column(
        Integer,
        ForeignKey("athletes.id"),
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    last_seen_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    revoked_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
