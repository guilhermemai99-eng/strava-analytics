import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


load_dotenv()


DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://strava:strava@localhost:5432/strava_analytics"
)


def normalize_database_url(url: str) -> str:
    """
    Railway and many hosts provide postgres:// URLs.
    SQLAlchemy 2 + psycopg3 expect postgresql+psycopg://.
    """

    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]

    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]

    return url


DATABASE_URL = normalize_database_url(
    os.getenv(
        "DATABASE_URL",
        DEFAULT_DATABASE_URL
    )
)


engine_kwargs = {
    "pool_pre_ping": True,
}

# Optional SQLite support for ad-hoc local use only.
# Prefer PostgreSQL for development and production.
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {
        "check_same_thread": False
    }


engine = create_engine(
    DATABASE_URL,
    **engine_kwargs
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()
