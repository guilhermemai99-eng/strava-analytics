"""OAuth state one-shot validation."""

from __future__ import annotations

from datetime import timedelta

from oauth_helpers import consume_oauth_state, create_oauth_state
from oauth_state import OAuthState, utcnow


def test_missing_state_rejected(db_session):
    assert consume_oauth_state(db_session, None) is False
    assert consume_oauth_state(db_session, "") is False
    assert consume_oauth_state(db_session, "does-not-exist") is False


def test_valid_state_consumed_once(db_session):
    create_oauth_state(db_session, "state-once")
    assert consume_oauth_state(db_session, "state-once") is True
    assert consume_oauth_state(db_session, "state-once") is False


def test_expired_state_rejected(db_session):
    create_oauth_state(db_session, "state-expired")
    row = (
        db_session.query(OAuthState)
        .filter(OAuthState.state == "state-expired")
        .one()
    )
    row.expires_at = utcnow() - timedelta(minutes=1)
    db_session.commit()

    assert consume_oauth_state(db_session, "state-expired") is False


def test_callback_rejects_invalid_state(client):
    resp = client.get(
        "/auth/strava/callback",
        params={"code": "abc", "state": "bad-state"},
    )
    assert resp.status_code == 200
    assert resp.json()["error"] == "Estado OAuth inválido."
