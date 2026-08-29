"""Fernet helpers for Strava OAuth tokens at rest.

token_version semantics (see strava_auth / strava_tokens):
  1 = Fernet ciphertext (required)
  0 = legacy plaintext — no longer accepted after Foundation cutover

Key resolution order:
  1) TOKEN_ENCRYPTION_KEY (preferred, dedicated Fernet key)
  2) Stable key derived from STRAVA_CLIENT_SECRET (Railway-safe fallback
     so login keeps working if the dedicated secret was not set yet)
"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv


load_dotenv()


TOKEN_VERSION_PLAINTEXT = 0  # legacy; rejected by readers
TOKEN_VERSION_FERNET = 1

_fernet_warned_fallback = False


class TokenEncryptionError(Exception):
    pass


def _derived_key_from_secret(secret: str) -> bytes:
    digest = hashlib.sha256(
        f"pulse-fernet-v1:{secret}".encode("utf-8")
    ).digest()
    return base64.urlsafe_b64encode(digest)


def _load_fernet() -> Fernet:
    global _fernet_warned_fallback

    raw_key = (os.getenv("TOKEN_ENCRYPTION_KEY") or "").strip()

    if raw_key:
        try:
            return Fernet(raw_key.encode("utf-8"))
        except Exception as exc:
            raise TokenEncryptionError(
                "TOKEN_ENCRYPTION_KEY is invalid. "
                "It must be a url-safe base64-encoded 32-byte Fernet key."
            ) from exc

    # Fallback: derive from Strava client secret so OAuth login does not
    # 500 when TOKEN_ENCRYPTION_KEY was not configured on the host.
    client_secret = (os.getenv("STRAVA_CLIENT_SECRET") or "").strip()
    if client_secret:
        if not _fernet_warned_fallback:
            print(
                "[security] TOKEN_ENCRYPTION_KEY missing; "
                "deriving Fernet key from STRAVA_CLIENT_SECRET. "
                "Set TOKEN_ENCRYPTION_KEY explicitly on Railway."
            )
            _fernet_warned_fallback = True
        return Fernet(_derived_key_from_secret(client_secret))

    raise TokenEncryptionError(
        "TOKEN_ENCRYPTION_KEY is missing (and STRAVA_CLIENT_SECRET "
        "fallback is unavailable). Generate one with: "
        "python -c \"from cryptography.fernet import Fernet; "
        "print(Fernet.generate_key().decode())\""
    )


def encrypt_token(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None

    if plaintext == "":
        return ""

    fernet = _load_fernet()
    return fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_token(ciphertext: str | None) -> str | None:
    if ciphertext is None:
        return None

    if ciphertext == "":
        return ""

    fernet = _load_fernet()

    try:
        return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise TokenEncryptionError(
            "Failed to decrypt Strava token. "
            "Check TOKEN_ENCRYPTION_KEY or re-authenticate."
        ) from exc
