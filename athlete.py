from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Athlete(Base):
    __tablename__ = "athletes"

    # Strava athlete id is the primary key to avoid rewriting analytics.
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=False,
        index=True,
    )

    username = Column(String, nullable=True)
    firstname = Column(String, nullable=True)
    lastname = Column(String, nullable=True)
    sex = Column(String, nullable=True)

    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True)

    profile = Column(String, nullable=True)
    profile_medium = Column(String, nullable=True)
    bio = Column(Text, nullable=True)

    is_profile_public = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    last_login_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
