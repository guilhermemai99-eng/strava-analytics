#!/usr/bin/env python3
"""Phase E acceptance checks for token encryption (no network)."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryptography.fernet import Fernet


def _ok(name: str) -> None:
    print(f"PASS {name}")


def test_crypto_roundtrip():
    key = Fernet.generate_key().decode()
    with mock.patch.dict(os.environ, {"TOKEN_ENCRYPTION_KEY": key}):
        # Reload module with fresh env
        import importlib
        import token_crypto

        importlib.reload(token_crypto)

        plain = "strava-access-token-example"
        cipher = token_crypto.encrypt_token(plain)
        assert cipher != plain
        assert token_crypto.decrypt_token(cipher) == plain
        assert cipher.startswith("gAAAA")  # Fernet prefix
    _ok("crypto_roundtrip")


def test_dual_read_and_store():
    key = Fernet.generate_key().decode()
    with mock.patch.dict(os.environ, {"TOKEN_ENCRYPTION_KEY": key}):
        import importlib
        import token_crypto
        import strava_tokens
        from strava_auth import StravaAuth

        importlib.reload(token_crypto)
        importlib.reload(strava_tokens)

        # v0 plaintext still readable
        auth0 = StravaAuth(
            athlete_id=1,
            access_token="plain-access",
            refresh_token="plain-refresh",
            expires_at=1893456000,
            token_version=0,
        )
        assert (
            strava_tokens._read_stored_token(
                auth0.access_token, auth0.token_version
            )
            == "plain-access"
        )

        # store encrypts and bumps version
        strava_tokens.store_strava_tokens(
            auth0,
            access_token="plain-access",
            refresh_token="plain-refresh",
            expires_at=1893456000,
        )
        assert auth0.token_version == 1
        assert auth0.access_token != "plain-access"
        assert auth0.refresh_token != "plain-refresh"
        assert (
            strava_tokens._read_stored_token(
                auth0.access_token, auth0.token_version
            )
            == "plain-access"
        )
        assert (
            strava_tokens._read_stored_token(
                auth0.refresh_token, auth0.token_version
            )
            == "plain-refresh"
        )
    _ok("dual_read_and_store")


def test_db_migration_and_script(tmp_path_unused=None):
    """Apply 0004 against local Postgres and encrypt a seed row."""
    key = Fernet.generate_key().decode()
    os.environ["TOKEN_ENCRYPTION_KEY"] = key

    from alembic import command
    from alembic.config import Config
    from database import SessionLocal, engine
    from sqlalchemy import text

    cfg = Config(str(ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")

    # Confirm columns exist
    with engine.connect() as conn:
        cols = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'strava_auth'"
                )
            )
        }
    assert "token_version" in cols
    assert "updated_at" in cols
    _ok("migration_0004_columns")

    # Seed athlete + plaintext auth if needed
    from athlete import Athlete
    from strava_auth import StravaAuth
    from datetime import datetime, timezone

    db = SessionLocal()
    try:
        athlete_id = 900001
        existing = db.query(Athlete).filter(Athlete.id == athlete_id).one_or_none()
        if not existing:
            now = datetime.now(timezone.utc)
            db.add(
                Athlete(
                    id=athlete_id,
                    is_profile_public=False,
                    created_at=now,
                    updated_at=now,
                )
            )
            db.commit()

        auth = (
            db.query(StravaAuth)
            .filter(StravaAuth.athlete_id == athlete_id)
            .one_or_none()
        )
        if auth:
            auth.access_token = "seed-access-plain"
            auth.refresh_token = "seed-refresh-plain"
            auth.token_version = 0
            auth.expires_at = 1893456000
        else:
            auth = StravaAuth(
                athlete_id=athlete_id,
                access_token="seed-access-plain",
                refresh_token="seed-refresh-plain",
                expires_at=1893456000,
                token_version=0,
            )
            db.add(auth)
        db.commit()
        auth_id = auth.id
    finally:
        db.close()

    # Run encrypt job
    import scripts.encrypt_strava_tokens as encrypt_mod

    # Ensure modules see the key
    import importlib
    import token_crypto
    import strava_tokens

    importlib.reload(token_crypto)
    importlib.reload(strava_tokens)
    importlib.reload(encrypt_mod)

    rc = encrypt_mod.encrypt_all(dry_run=False)
    assert rc == 0

    db = SessionLocal()
    try:
        auth = db.query(StravaAuth).filter(StravaAuth.id == auth_id).one()
        assert auth.token_version == 1
        assert auth.access_token != "seed-access-plain"
        assert auth.refresh_token != "seed-refresh-plain"
        assert token_crypto.decrypt_token(auth.access_token) == "seed-access-plain"

        # get_valid_access_token returns plaintext
        plain = strava_tokens.get_valid_access_token(db, athlete_id)
        assert plain == "seed-access-plain"
    finally:
        db.close()

    _ok("db_encrypt_job_and_get_valid_access_token")


def main():
    test_crypto_roundtrip()
    test_dual_read_and_store()
    test_db_migration_and_script()
    print("ALL PHASE E CHECKS PASSED")


if __name__ == "__main__":
    main()
