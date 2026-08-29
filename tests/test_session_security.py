"""Session security: forged cookie rejected; valid/expired/revoked sessions."""

from __future__ import annotations

from datetime import timedelta

from session_helpers import SESSION_COOKIE_NAME, create_session, hash_session_token
from user_session import UserSession, utcnow


def test_forged_numeric_athlete_id_cookie_does_not_authenticate(client):
    client.cookies.set(SESSION_COOKIE_NAME, "87717162")
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json() == {"authenticated": False}

    summary = client.get("/analytics/summary")
    assert summary.status_code == 401


def test_valid_session_resolves_correct_athlete(client, make_session):
    raw, cookie_name = make_session(710001)
    client.cookies.set(cookie_name, raw)

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json() == {"authenticated": True, "athlete_id": 710001}


def test_expired_session_returns_401(client, db_session, make_athlete):
    make_athlete(710002)
    raw = create_session(db_session, 710002)
    row = (
        db_session.query(UserSession)
        .filter(UserSession.token_hash == hash_session_token(raw))
        .one()
    )
    row.expires_at = utcnow() - timedelta(hours=1)
    db_session.commit()

    client.cookies.set(SESSION_COOKIE_NAME, raw)
    assert client.get("/analytics/summary").status_code == 401
    assert client.get("/auth/me").json() == {"authenticated": False}


def test_revoked_session_returns_401(client, db_session, make_athlete):
    make_athlete(710003)
    raw = create_session(db_session, 710003)
    row = (
        db_session.query(UserSession)
        .filter(UserSession.token_hash == hash_session_token(raw))
        .one()
    )
    row.revoked_at = utcnow()
    db_session.commit()

    client.cookies.set(SESSION_COOKIE_NAME, raw)
    assert client.get("/activities").status_code == 401
