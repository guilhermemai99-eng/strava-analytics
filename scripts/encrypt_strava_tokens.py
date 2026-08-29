#!/usr/bin/env python3
"""Encrypt plaintext Strava tokens (token_version=0 -> 1).

Also runs automatically on app startup when TOKEN_ENCRYPTION_KEY is set.
Keep this script for one-shot ops / dry-runs.

Usage:
  TOKEN_ENCRYPTION_KEY=... DATABASE_URL=... \\
    .venv/bin/python scripts/encrypt_strava_tokens.py

  .venv/bin/python scripts/encrypt_strava_tokens.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import SessionLocal
from strava_auth import StravaAuth
from strava_tokens import upgrade_plaintext_tokens
from token_crypto import (
    TOKEN_VERSION_FERNET,
    TOKEN_VERSION_PLAINTEXT,
    TokenEncryptionError,
    decrypt_token,
    encrypt_token,
)


def _count_by_version(db):
    rows = db.query(StravaAuth).all()
    plaintext = sum(
        1
        for r in rows
        if (r.token_version or 0) == TOKEN_VERSION_PLAINTEXT
    )
    encrypted = sum(
        1
        for r in rows
        if (r.token_version or 0) == TOKEN_VERSION_FERNET
    )
    other = len(rows) - plaintext - encrypted
    return len(rows), plaintext, encrypted, other


def _assert_key_works() -> None:
    probe = encrypt_token("probe")
    if decrypt_token(probe) != "probe":
        raise TokenEncryptionError("Fernet round-trip failed")


def encrypt_all(*, dry_run: bool) -> int:
    try:
        _assert_key_works()
    except TokenEncryptionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        total, plaintext, encrypted, other = _count_by_version(db)
        print(
            f"strava_auth rows={total} "
            f"plaintext_v0={plaintext} "
            f"encrypted_v1={encrypted} "
            f"other={other}"
        )

        if other:
            print(
                "ERROR: unsupported token_version present; aborting.",
                file=sys.stderr,
            )
            return 1

        if plaintext == 0:
            print("Nothing to encrypt. All rows already at token_version=1.")
            return 0

        if dry_run:
            pending = (
                db.query(StravaAuth)
                .filter(
                    (StravaAuth.token_version == TOKEN_VERSION_PLAINTEXT)
                    | (StravaAuth.token_version.is_(None))
                )
                .order_by(StravaAuth.id)
                .all()
            )
            for auth in pending:
                print(
                    f"dry-run would encrypt id={auth.id} "
                    f"athlete_id={auth.athlete_id}"
                )
            print(f"done upgraded={len(pending)} dry_run=True")
            return 0

        result = upgrade_plaintext_tokens(db)
        print(
            f"done upgraded={result['upgraded']} "
            f"skipped={result['skipped']} "
            f"plaintext_v0={result['remaining_plaintext']}"
        )

        if result["remaining_plaintext"] != 0:
            print(
                "WARNING: plaintext rows remain after job.",
                file=sys.stderr,
            )
            return 2

        return 0
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Encrypt plaintext Strava tokens in strava_auth."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List rows that would be encrypted without writing.",
    )
    args = parser.parse_args()
    raise SystemExit(encrypt_all(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
