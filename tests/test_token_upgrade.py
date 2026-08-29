"""Startup encrypts leftover plaintext tokens before rejecting dual-read."""

from __future__ import annotations

from strava_auth import StravaAuth
from strava_tokens import upgrade_plaintext_tokens
from token_crypto import decrypt_token


def test_upgrade_plaintext_tokens(db_session, make_athlete):
    make_athlete(770001)
    auth = StravaAuth(
        athlete_id=770001,
        access_token="legacy-access",
        refresh_token="legacy-refresh",
        expires_at=1893456000,
        token_version=0,
    )
    db_session.add(auth)
    db_session.commit()

    result = upgrade_plaintext_tokens(db_session)
    assert result["upgraded"] >= 1
    assert result["remaining_plaintext"] == 0

    db_session.refresh(auth)
    assert auth.token_version == 1
    assert auth.access_token != "legacy-access"
    assert decrypt_token(auth.access_token) == "legacy-access"
