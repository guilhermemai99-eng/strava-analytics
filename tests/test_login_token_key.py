"""TOKEN_ENCRYPTION_KEY fallback keeps OAuth token writes working."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet


def test_fernet_fallback_from_strava_client_secret(monkeypatch):
    monkeypatch.delenv("TOKEN_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test-strava-secret")

    from token_crypto import decrypt_token, encrypt_token

    plain = "access-token-value"
    cipher = encrypt_token(plain)
    assert cipher != plain
    assert decrypt_token(cipher) == plain


def test_oauth_callback_stores_tokens_without_explicit_key(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.delenv("TOKEN_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test-strava-secret")
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test-client-id")

    from oauth_helpers import create_oauth_state
    from session_helpers import SESSION_COOKIE_NAME
    from strava_auth import StravaAuth
    from token_crypto import decrypt_token
    from athlete import Athlete
    from user_session import UserSession

    state = "login-fix-state"
    create_oauth_state(db_session, state)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "login-access",
        "refresh_token": "login-refresh",
        "expires_at": 1893456000,
        "athlete": {
            "id": 880001,
            "username": "runner",
            "firstname": "Run",
            "lastname": "Ner",
        },
    }

    with patch("main.requests.post", return_value=mock_resp):
        resp = client.get(
            "/auth/strava/callback",
            params={"code": "abc", "state": state},
        )

    assert resp.status_code == 302, resp.text
    assert resp.headers.get("location") == "/dashboard?boot=1"
    assert SESSION_COOKIE_NAME in resp.cookies

    auth = (
        db_session.query(StravaAuth)
        .filter(StravaAuth.athlete_id == 880001)
        .one()
    )
    assert auth.token_version == 1
    assert decrypt_token(auth.access_token) == "login-access"

    db_session.query(UserSession).filter(UserSession.athlete_id == 880001).delete()
    db_session.query(StravaAuth).filter(StravaAuth.athlete_id == 880001).delete()
    db_session.query(Athlete).filter(Athlete.id == 880001).delete()
    db_session.commit()
