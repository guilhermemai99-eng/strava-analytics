"""Athlete upsert on OAuth callback (mocked Strava token exchange)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from athlete import Athlete
from oauth_helpers import create_oauth_state
from session_helpers import SESSION_COOKIE_NAME, hash_session_token
from strava_auth import StravaAuth
from token_crypto import decrypt_token
from user_session import UserSession


def _state(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _token_payload(athlete_id: int, *, firstname: str, access: str, refresh: str):
    return {
        "access_token": access,
        "refresh_token": refresh,
        "expires_at": 1893456000,
        "athlete": {
            "id": athlete_id,
            "username": f"user{athlete_id}",
            "firstname": firstname,
            "lastname": "Tester",
            "sex": "M",
            "city": "Lisboa",
            "state": None,
            "country": "Portugal",
            "profile": "http://example/profile.jpg",
            "profile_medium": "http://example/profile-med.jpg",
        },
    }


def test_callback_creates_athlete_auth_and_session(client, db_session):
    state = _state("oauth-create")
    create_oauth_state(db_session, state)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = _token_payload(
        720001,
        firstname="Ana",
        access="access-1",
        refresh="refresh-1",
    )

    with patch("main.requests.post", return_value=mock_resp):
        resp = client.get(
            "/auth/strava/callback",
            params={"code": "code-1", "state": state},
        )

    assert resp.status_code == 302
    assert resp.headers.get("location") == "/dashboard?boot=1"
    assert SESSION_COOKIE_NAME in resp.cookies

    athlete = db_session.query(Athlete).filter(Athlete.id == 720001).one()
    assert athlete.firstname == "Ana"
    assert athlete.username == "user720001"

    auth = db_session.query(StravaAuth).filter(StravaAuth.athlete_id == 720001).one()
    assert auth.token_version == 1
    assert auth.access_token != "access-1"
    assert decrypt_token(auth.access_token) == "access-1"
    assert decrypt_token(auth.refresh_token) == "refresh-1"

    raw = resp.cookies.get(SESSION_COOKIE_NAME)
    session = (
        db_session.query(UserSession)
        .filter(UserSession.token_hash == hash_session_token(raw))
        .one()
    )
    assert session.athlete_id == 720001

    db_session.query(UserSession).filter(UserSession.athlete_id == 720001).delete()
    db_session.query(StravaAuth).filter(StravaAuth.athlete_id == 720001).delete()
    db_session.query(Athlete).filter(Athlete.id == 720001).delete()
    db_session.commit()


def test_second_login_updates_profile_and_creates_new_session(client, db_session):
    state1 = _state("oauth-first")
    state2 = _state("oauth-second")
    create_oauth_state(db_session, state1)
    create_oauth_state(db_session, state2)

    first = MagicMock()
    first.status_code = 200
    first.json.return_value = _token_payload(
        720002,
        firstname="Old",
        access="access-old",
        refresh="refresh-old",
    )
    second = MagicMock()
    second.status_code = 200
    second.json.return_value = _token_payload(
        720002,
        firstname="New",
        access="access-new",
        refresh="refresh-new",
    )

    with patch("main.requests.post", return_value=first):
        r1 = client.get(
            "/auth/strava/callback",
            params={"code": "c1", "state": state1},
        )
    cookie1 = r1.cookies.get(SESSION_COOKIE_NAME)

    with patch("main.requests.post", return_value=second):
        r2 = client.get(
            "/auth/strava/callback",
            params={"code": "c2", "state": state2},
        )
    cookie2 = r2.cookies.get(SESSION_COOKIE_NAME)

    assert cookie1 != cookie2

    athlete = db_session.query(Athlete).filter(Athlete.id == 720002).one()
    assert athlete.firstname == "New"

    auth = db_session.query(StravaAuth).filter(StravaAuth.athlete_id == 720002).one()
    assert decrypt_token(auth.access_token) == "access-new"
    assert decrypt_token(auth.refresh_token) == "refresh-new"

    sessions = (
        db_session.query(UserSession)
        .filter(UserSession.athlete_id == 720002)
        .all()
    )
    assert len(sessions) == 2

    db_session.query(UserSession).filter(UserSession.athlete_id == 720002).delete()
    db_session.query(StravaAuth).filter(StravaAuth.athlete_id == 720002).delete()
    db_session.query(Athlete).filter(Athlete.id == 720002).delete()
    db_session.commit()
