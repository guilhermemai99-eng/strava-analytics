from sqlalchemy import Column, ForeignKey, Integer, String

from database import Base


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

    access_token = Column(String)
    refresh_token = Column(String)
    expires_at = Column(Integer)
