from sqlalchemy import Column, Integer, String

from database import Base


class StravaAuth(Base):
    __tablename__ = "strava_auth"

    id = Column(Integer, primary_key=True)
    athlete_id = Column(Integer, unique=True, index=True)
    access_token = Column(String)
    refresh_token = Column(String)
    expires_at = Column(Integer)