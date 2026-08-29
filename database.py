import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://strava:strava@localhost:5432/strava_analytics"
)


def normalize_database_url(url: str) -> str:
    """
    Railway and many hosts provide postgres:// URLs.
    SQLAlchemy 2 + psycopg3 expect postgresql+psycopg://.
    """

    url = (url or "").strip().strip('"').strip("'")

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


def _safe_db_host(url: str) -> str:
    return urlparse(url).hostname or "(none)"


# On Railway, trust only process env vars from the platform.
# Locally, allow .env for convenience.
if not _running_on_railway():
    load_dotenv()

raw_database_url = os.getenv("DATABASE_URL", "").strip().strip('"').strip("'")

if _running_on_railway():
    if not raw_database_url:
        raise RuntimeError(
            "DATABASE_URL is missing on Railway. "
            "Set it on the WEB app Variables, then redeploy."
        )

    DATABASE_URL = normalize_database_url(raw_database_url)
    db_host = _safe_db_host(DATABASE_URL)
    print(f"[database] Railway DATABASE_URL host={db_host}")

    if _is_localhost_url(DATABASE_URL):
        raise RuntimeError(
            "DATABASE_URL points to localhost on Railway "
            f"(host={db_host}). "
            "Open the WEB app Variables and set DATABASE_URL to the "
            "Postgres DATABASE_PRIVATE_URL "
            "(must contain postgres.railway.internal), then redeploy."
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
