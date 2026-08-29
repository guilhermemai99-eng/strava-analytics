from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from database import Base


def utcnow():
    return datetime.now(timezone.utc)


class StravaAuth(Base):
    __tablename__ = "strava_auth"

    id = Column(Integer, primary_key=True)

    athlete_id = Column(
        Integer,
        ForeignKey("athletes.id"),
        unique=True,
        index=True,
        nullable=False,
    )

    # Stored as plaintext (token_version=0) or Fernet ciphertext (1).
    access_token = Column(String)
    refresh_token = Column(String)
    expires_at = Column(Integer)

    # 0 = plaintext legacy; 1 = Fernet at rest.
    token_version = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=utcnow,
        onupdate=utcnow,
    )
