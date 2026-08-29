"""Token encryption: dual-read, encrypt-on-store, plaintext to callers."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

from strava_auth import StravaAuth
from strava_tokens import (
    _read_stored_token,
    get_valid_access_token,
    store_strava_tokens,
)
from token_crypto import decrypt_token, encrypt_token


def test_fernet_roundtrip():
    plain = "strava-access-token-example"
    cipher = encrypt_token(plain)
    assert cipher != plain
    assert cipher.startswith("gAAAA")
    assert decrypt_token(cipher) == plain


def test_dual_read_plaintext_version_zero():
    auth = StravaAuth(
        athlete_id=1,
        access_token="plain-access",
        refresh_token="plain-refresh",
        expires_at=1893456000,
        token_version=0,
    )
    assert _read_stored_token(auth.access_token, auth.token_version) == "plain-access"


def test_store_encrypts_and_bumps_version():
    auth = StravaAuth(athlete_id=1)
    store_strava_tokens(
        auth,
        access_token="plain-access",
        refresh_token="plain-refresh",
        expires_at=1893456000,
    )
    assert auth.token_version == 1
    assert auth.access_token != "plain-access"
    assert auth.refresh_token != "plain-refresh"
    assert _read_stored_token(auth.access_token, auth.token_version) == "plain-access"
    assert _read_stored_token(auth.refresh_token, auth.token_version) == "plain-refresh"


def test_get_valid_access_token_returns_plaintext(db_session, make_athlete):
    make_athlete(730001)
    auth = StravaAuth(
        athlete_id=730001,
        expires_at=int(time.time()) + 3600,
        token_version=0,
    )
    store_strava_tokens(
        auth,
        access_token="live-access",
        refresh_token="live-refresh",
        expires_at=int(time.time()) + 3600,
    )
    db_session.add(auth)
    db_session.commit()

    plain = get_valid_access_token(db_session, 730001)
    assert plain == "live-access"

    stored = (
        db_session.query(StravaAuth)
        .filter(StravaAuth.athlete_id == 730001)
        .one()
    )
    assert stored.access_token != "live-access"
    assert stored.token_version == 1


def test_refresh_persists_newly_encrypted_tokens(db_session, make_athlete):
    make_athlete(730002)
    auth = StravaAuth(
        athlete_id=730002,
        expires_at=int(time.time()) - 10,
        token_version=0,
        access_token="old-access",
        refresh_token="old-refresh",
    )
    db_session.add(auth)
    db_session.commit()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "new-access",
        "refresh_token": "new-refresh",
        "expires_at": int(time.time()) + 3600,
    }

    with patch("strava_tokens.requests.post", return_value=mock_resp):
        plain = get_valid_access_token(db_session, 730002, force_refresh=True)

    assert plain == "new-access"
    db_session.refresh(auth)
    assert auth.token_version == 1
    assert auth.access_token != "new-access"
    assert decrypt_token(auth.access_token) == "new-access"
    assert decrypt_token(auth.refresh_token) == "new-refresh"
