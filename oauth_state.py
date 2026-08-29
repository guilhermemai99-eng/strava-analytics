from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String

from database import Base


def utcnow():
    return datetime.now(timezone.utc)


class OAuthState(Base):
    """One-time Strava OAuth CSRF state, persisted for multi-instance safety."""

    __tablename__ = "oauth_states"

    state = Column(
        String(128),
        primary_key=True,
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

    consumed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
