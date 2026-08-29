"""Shared fixtures for Foundation V2 Phase H tests.

Sets DATABASE_URL / secrets before importing application modules, then
runs Alembic against a dedicated Postgres test database.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_DATABASE_URL = (
    "postgresql+psycopg://strava:strava@localhost:5432/strava_analytics_test"
)

# Must be set before importing database / main / token_crypto.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["OPENAI_API_KEY"] = "test-key-not-used"
os.environ["TOKEN_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["STRAVA_CLIENT_ID"] = "test-client-id"
os.environ["STRAVA_CLIENT_SECRET"] = "test-client-secret"
os.environ["STRAVA_REDIRECT_URI"] = "http://test.local/auth/strava/callback"
# Avoid loading a local .env that could override test DB.
os.environ.pop("RAILWAY_ENVIRONMENT", None)


def pytest_configure(config):
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def app():
    from main import app as fastapi_app

    return fastapi_app


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app, follow_redirects=False) as test_client:
        yield test_client


@pytest.fixture
def db_session():
    from database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def encryption_key():
    return os.environ["TOKEN_ENCRYPTION_KEY"]


def _utcnow():
    return datetime.now(timezone.utc)


@pytest.fixture
def make_athlete(db_session):
    from athlete import Athlete

    created = []

    def _make(athlete_id: int, **fields):
        row = db_session.query(Athlete).filter(Athlete.id == athlete_id).one_or_none()
        now = _utcnow()
        if row is None:
            row = Athlete(
                id=athlete_id,
                is_profile_public=False,
                created_at=now,
                updated_at=now,
                **fields,
            )
            db_session.add(row)
        else:
            for key, value in fields.items():
                setattr(row, key, value)
            row.updated_at = now
        db_session.commit()
        created.append(athlete_id)
        return row

    yield _make

    from models import Activity
    from strava_auth import StravaAuth
    from user_session import UserSession

    for athlete_id in created:
        db_session.query(Activity).filter(Activity.athlete_id == athlete_id).delete()
        db_session.query(UserSession).filter(UserSession.athlete_id == athlete_id).delete()
        db_session.query(StravaAuth).filter(StravaAuth.athlete_id == athlete_id).delete()
        from coach_message import CoachMessage

        db_session.query(CoachMessage).filter(CoachMessage.athlete_id == athlete_id).delete()
        db_session.query(Athlete).filter(Athlete.id == athlete_id).delete()
    db_session.commit()


@pytest.fixture
def make_session(db_session, make_athlete):
    from session_helpers import SESSION_COOKIE_NAME, create_session

    def _make(athlete_id: int):
        make_athlete(athlete_id)
        raw = create_session(db_session, athlete_id)
        return raw, SESSION_COOKIE_NAME

    return _make


@pytest.fixture
def make_activity(db_session, make_athlete):
    from models import Activity

    def _make(athlete_id: int, *, strava_id: int, name: str = "Run"):
        make_athlete(athlete_id)
        activity = Activity(
            athlete_id=athlete_id,
            strava_id=strava_id,
            name=name,
            sport_type="Run",
            distance_m=5000,
            moving_time_s=1500,
            start_date_local="2026-08-01T07:00:00Z",
        )
        db_session.add(activity)
        db_session.commit()
        db_session.refresh(activity)
        return activity

    return _make
