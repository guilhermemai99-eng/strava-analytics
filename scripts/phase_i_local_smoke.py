#!/usr/bin/env python3
"""Foundation V2 Phase I — local smoke (TestClient, no live Strava).

Runs against the same Postgres test DB as pytest. Covers the automated
portion of the Phase I checklist: auth contract, 401s, session isolation,
legacy removal, and encrypted token store.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cryptography.fernet import Fernet

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://strava:strava@localhost:5432/strava_analytics_test",
)
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-used")
os.environ.setdefault(
    "TOKEN_ENCRYPTION_KEY",
    Fernet.generate_key().decode(),
)
os.environ.setdefault("STRAVA_CLIENT_ID", "test-client-id")
os.environ.setdefault("STRAVA_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault(
    "STRAVA_REDIRECT_URI",
    "http://test.local/auth/strava/callback",
)

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from athlete import Athlete, utcnow
from database import SessionLocal
from main import app
from models import Activity
from oauth_helpers import create_oauth_state
from session_helpers import SESSION_COOKIE_NAME, create_session
from strava_auth import StravaAuth
from strava_tokens import store_strava_tokens
from token_crypto import decrypt_token


def _ok(msg: str) -> None:
    print(f"PASS {msg}")


def main() -> int:
    cfg = Config(str(ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")

    client = TestClient(app, follow_redirects=False)
    db = SessionLocal()
    athlete_id = 760001

    try:
        assert client.get("/").status_code == 200
        _ok("GET / login page")

        assert client.get("/auth/me").json() == {"authenticated": False}
        _ok("/auth/me anonymous")

        assert client.get("/dashboard").status_code == 302
        _ok("/dashboard redirects when anonymous")

        for path in (
            "/activities",
            "/analytics/summary",
            "/strava/sync",
        ):
            method = client.post if path == "/strava/sync" else client.get
            resp = method(path)
            assert resp.status_code == 401, (path, resp.status_code)
        _ok("protected APIs return 401")

        post = client.post("/activities", json={"name": "x"})
        assert post.status_code in {404, 405}
        _ok("legacy POST /activities removed")

        # Seed athlete + encrypted tokens + activity + session
        now = utcnow()
        if not db.query(Athlete).filter(Athlete.id == athlete_id).one_or_none():
            db.add(
                Athlete(
                    id=athlete_id,
                    is_profile_public=False,
                    created_at=now,
                    updated_at=now,
                    firstname="Smoke",
                )
            )
            db.commit()

        auth = (
            db.query(StravaAuth)
            .filter(StravaAuth.athlete_id == athlete_id)
            .one_or_none()
        )
        if auth is None:
            auth = StravaAuth(athlete_id=athlete_id)
            db.add(auth)
        store_strava_tokens(
            auth,
            access_token="smoke-access",
            refresh_token="smoke-refresh",
            expires_at=1893456000,
        )
        db.commit()
        assert auth.token_version == 1
        assert decrypt_token(auth.access_token) == "smoke-access"
        _ok("tokens stored encrypted")

        if not db.query(Activity).filter(Activity.strava_id == 199760001).one_or_none():
            db.add(
                Activity(
                    athlete_id=athlete_id,
                    strava_id=199760001,
                    name="Smoke Run",
                    sport_type="Run",
                    distance_m=5000,
                    moving_time_s=1500,
                    start_date_local="2026-08-01T07:00:00Z",
                )
            )
            db.commit()

        raw = create_session(db, athlete_id)
        client.cookies.set(SESSION_COOKIE_NAME, raw)

        me = client.get("/auth/me")
        assert me.json() == {"authenticated": True, "athlete_id": athlete_id}
        _ok("/auth/me authenticated")

        acts = client.get("/activities")
        assert acts.status_code == 200
        assert any(a["name"] == "Smoke Run" for a in acts.json())
        _ok("GET /activities scoped to session")

        summary = client.get("/analytics/summary")
        assert summary.status_code == 200
        assert summary.json()["total_activities"] >= 1
        _ok("/analytics/summary")

        # Forged numeric cookie must not authenticate
        client.cookies.set(SESSION_COOKIE_NAME, str(athlete_id))
        assert client.get("/auth/me").json() == {"authenticated": False}
        _ok("forged athlete_id cookie rejected")

        # OAuth state reject path
        bad = client.get(
            "/auth/strava/callback",
            params={"code": "x", "state": "nope"},
        )
        assert bad.json()["error"] == "Estado OAuth inválido."
        _ok("invalid OAuth state rejected")

        # Mocked successful callback creates session cookie
        state = "phase-i-smoke-state"
        create_oauth_state(db, state)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "cb-access",
            "refresh_token": "cb-refresh",
            "expires_at": 1893456000,
            "athlete": {"id": 760002, "firstname": "CB", "username": "cb"},
        }
        with patch("main.requests.post", return_value=mock_resp):
            cb = client.get(
                "/auth/strava/callback",
                params={"code": "code", "state": state},
            )
        assert cb.status_code == 302
        assert cb.headers["location"] == "/dashboard?boot=1"
        assert SESSION_COOKIE_NAME in cb.cookies
        _ok("OAuth callback upsert + session cookie")

        print("ALL PHASE I LOCAL SMOKE CHECKS PASSED")
        return 0
    except Exception as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    finally:
        db.query(Activity).filter(Activity.athlete_id.in_([760001, 760002])).delete()
        from user_session import UserSession

        db.query(UserSession).filter(
            UserSession.athlete_id.in_([760001, 760002])
        ).delete()
        db.query(StravaAuth).filter(
            StravaAuth.athlete_id.in_([760001, 760002])
        ).delete()
        db.query(Athlete).filter(Athlete.id.in_([760001, 760002])).delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
