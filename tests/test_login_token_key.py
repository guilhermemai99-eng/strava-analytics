"""Login must not 500 when TOKEN_ENCRYPTION_KEY is missing or invalid."""

from __future__ import annotations

import secrets
from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet


def test_encrypt_without_token_encryption_key(monkeypatch):
    monkeypatch.delenv("TOKEN_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "strava-secret-for-tests")

    import token_crypto

    token_crypto.reset_fernet_cache()
    ct = token_crypto.encrypt_token("access-token-abc")
    assert ct != "access-token-abc"
    assert ct.startswith("gAAAA")
    assert token_crypto.decrypt_token(ct) == "access-token-abc"
    token_crypto.reset_fernet_cache()


def test_encrypt_falls_back_when_token_key_invalid(monkeypatch):
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "not-a-valid-fernet-key")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "strava-secret-for-tests")

    import token_crypto

    token_crypto.reset_fernet_cache()
    ct = token_crypto.encrypt_token("access-token-xyz")
    assert ct.startswith("gAAAA")
    assert token_crypto.decrypt_token(ct) == "access-token-xyz"
    token_crypto.reset_fernet_cache()


def test_decrypt_reads_tokens_from_either_key(monkeypatch):
    """Tokens encrypted under secret-derived key remain readable after a real key is added."""
    monkeypatch.delenv("TOKEN_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "strava-secret-for-tests")

    import token_crypto

    token_crypto.reset_fernet_cache()
    legacy_ct = token_crypto.encrypt_token("legacy-token")

    real_key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", real_key)
    token_crypto.reset_fernet_cache()

    assert token_crypto.decrypt_token(legacy_ct) == "legacy-token"
    fresh = token_crypto.encrypt_token("fresh-token")
    assert token_crypto.decrypt_token(fresh) == "fresh-token"
    token_crypto.reset_fernet_cache()


def _cleanup_athlete(db_session, athlete_id: int) -> None:
    from athlete import Athlete
    from strava_auth import StravaAuth
    from user_session import UserSession

    db_session.query(UserSession).filter(UserSession.athlete_id == athlete_id).delete()
    db_session.query(StravaAuth).filter(StravaAuth.athlete_id == athlete_id).delete()
    db_session.query(Athlete).filter(Athlete.id == athlete_id).delete()
    db_session.commit()


def test_oauth_callback_succeeds_without_token_encryption_key(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.delenv("TOKEN_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "strava-secret-for-tests")
    monkeypatch.setenv("STRAVA_CLIENT_ID", "12345")

    import token_crypto
    from oauth_helpers import create_oauth_state
    from session_helpers import SESSION_COOKIE_NAME
    from strava_auth import StravaAuth

    token_crypto.reset_fernet_cache()

    athlete_id = 880101
    _cleanup_athlete(db_session, athlete_id)

    state = secrets.token_urlsafe(16)
    create_oauth_state(db_session, state)

    token_payload = {
        "access_token": "at-1",
        "refresh_token": "rt-1",
        "expires_at": 1893456000,
        "athlete": {
            "id": athlete_id,
            "firstname": "Gui",
            "lastname": "M",
        },
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = token_payload

    with patch("main.requests.post", return_value=mock_resp):
        response = client.get(
            "/auth/strava/callback",
            params={"code": "abc", "state": state},
        )

    assert response.status_code == 302, response.text
    assert response.headers.get("location") == "/dashboard?boot=1"
    assert SESSION_COOKIE_NAME in response.cookies

    auth = (
        db_session.query(StravaAuth)
        .filter(StravaAuth.athlete_id == athlete_id)
        .one()
    )
    assert auth.token_version == 1
    assert token_crypto.decrypt_token(auth.access_token) == "at-1"

    _cleanup_athlete(db_session, athlete_id)
    token_crypto.reset_fernet_cache()


def test_oauth_callback_succeeds_with_invalid_token_encryption_key(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "placeholder-wrong")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "strava-secret-for-tests")
    monkeypatch.setenv("STRAVA_CLIENT_ID", "12345")

    import token_crypto
    from oauth_helpers import create_oauth_state
    from session_helpers import SESSION_COOKIE_NAME

    token_crypto.reset_fernet_cache()

    athlete_id = 880102
    _cleanup_athlete(db_session, athlete_id)

    state = secrets.token_urlsafe(16)
    create_oauth_state(db_session, state)

    token_payload = {
        "access_token": "at-2",
        "refresh_token": "rt-2",
        "expires_at": 1893456000,
        "athlete": {
            "id": athlete_id,
            "firstname": "Gui",
            "lastname": "M",
        },
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = token_payload

    with patch("main.requests.post", return_value=mock_resp):
        response = client.get(
            "/auth/strava/callback",
            params={"code": "xyz", "state": state},
        )

    assert response.status_code == 302, response.text
    assert "/dashboard" in response.headers.get("location", "")
    assert SESSION_COOKIE_NAME in response.cookies

    _cleanup_athlete(db_session, athlete_id)
    token_crypto.reset_fernet_cache()
