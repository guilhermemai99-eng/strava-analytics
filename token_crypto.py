"""Fernet helpers for Strava OAuth tokens at rest.

token_version semantics (see strava_auth / strava_tokens):
  1 = Fernet ciphertext (required)
  0 = legacy plaintext — no longer accepted after Foundation cutover
"""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv


load_dotenv()


TOKEN_VERSION_PLAINTEXT = 0  # legacy; rejected by readers
TOKEN_VERSION_FERNET = 1


class TokenEncryptionError(Exception):
    pass


def _load_fernet() -> Fernet:
    raw_key = (os.getenv("TOKEN_ENCRYPTION_KEY") or "").strip()

    if not raw_key:
        raise TokenEncryptionError(
            "TOKEN_ENCRYPTION_KEY is missing. "
            "Generate one with: "
            "python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )

    try:
        return Fernet(raw_key.encode("utf-8"))
    except Exception as exc:
        raise TokenEncryptionError(
            "TOKEN_ENCRYPTION_KEY is invalid. "
            "It must be a url-safe base64-encoded 32-byte Fernet key."
        ) from exc


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
