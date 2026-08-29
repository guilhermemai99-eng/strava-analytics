import os
from urllib.parse import urlparse

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

    url = (url or "").strip()

    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]

    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]

    return url


def _running_on_railway() -> bool:
    return bool(
        os.getenv("RAILWAY_ENVIRONMENT")
        or os.getenv("RAILWAY_PROJECT_ID")
        or os.getenv("RAILWAY_SERVICE_ID")
    )


def _is_localhost_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1"}


raw_database_url = os.getenv("DATABASE_URL", "").strip()

if _running_on_railway():
    if not raw_database_url:
        raise RuntimeError(
            "DATABASE_URL is missing on Railway. "
            "On the WEB app service Variables, set DATABASE_URL to a "
            "reference like ${{Postgres.DATABASE_PRIVATE_URL}} "
            "(use your exact Postgres service name), then redeploy."
        )

    DATABASE_URL = normalize_database_url(raw_database_url)

    if _is_localhost_url(DATABASE_URL):
        raise RuntimeError(
            "DATABASE_URL points to localhost on Railway. "
            "Set DATABASE_URL on the WEB app (not the Postgres service) "
            "to ${{YourPostgresService.DATABASE_PRIVATE_URL}} and redeploy."
        )
else:
    DATABASE_URL = normalize_database_url(
        raw_database_url or DEFAULT_DATABASE_URL
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
