"""Fernet helpers for Strava OAuth tokens at rest.

token_version semantics (see strava_auth / strava_tokens):
  1 = Fernet ciphertext (required)
  0 = legacy plaintext — no longer accepted after Foundation cutover

Key resolution:
  - Prefer TOKEN_ENCRYPTION_KEY when it is a valid Fernet key
  - Otherwise derive a stable key from STRAVA_CLIENT_SECRET
  - Decrypt tries every available key so a key rotation / mis-set
    env var does not permanently lock athletes out after re-login
"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from dotenv import load_dotenv


load_dotenv()


TOKEN_VERSION_PLAINTEXT = 0  # legacy; rejected by readers
TOKEN_VERSION_FERNET = 1

_warned_missing = False
_warned_invalid = False


class TokenEncryptionError(Exception):
    pass


def reset_fernet_cache() -> None:
    """Reset module warning flags (tests mutate env between cases)."""

    global _warned_missing, _warned_invalid
    _warned_missing = False
    _warned_invalid = False


def _derived_key_from_secret(secret: str) -> bytes:
    digest = hashlib.sha256(
        f"pulse-fernet-v1:{secret}".encode("utf-8")
    ).digest()
    return base64.urlsafe_b64encode(digest)


def _try_parse_fernet_key(raw_key: str) -> bytes | None:
    """Return key material if raw_key is a valid Fernet key, else None."""

    global _warned_invalid
    try:
        key_bytes = raw_key.encode("utf-8")
        Fernet(key_bytes)  # validate
        return key_bytes
    except Exception:
        if not _warned_invalid:
            print(
                "[security] TOKEN_ENCRYPTION_KEY is set but invalid; "
                "falling back to STRAVA_CLIENT_SECRET-derived key. "
                "Generate a real Fernet key and set TOKEN_ENCRYPTION_KEY."
            )
            _warned_invalid = True
        return None


def _fernet_key_material() -> list[bytes]:
    """Return Fernet key bytes in preference order (encrypt uses first)."""

    global _warned_missing

    keys: list[bytes] = []

    raw_key = (os.getenv("TOKEN_ENCRYPTION_KEY") or "").strip()
    if raw_key:
        parsed = _try_parse_fernet_key(raw_key)
        if parsed is not None:
            keys.append(parsed)

    client_secret = (os.getenv("STRAVA_CLIENT_SECRET") or "").strip()
    if client_secret:
        derived = _derived_key_from_secret(client_secret)
        if derived not in keys:
            if not keys and not _warned_missing:
                print(
                    "[security] TOKEN_ENCRYPTION_KEY missing or invalid; "
                    "using STRAVA_CLIENT_SECRET-derived Fernet key. "
                    "Set TOKEN_ENCRYPTION_KEY explicitly on Railway."
                )
                _warned_missing = True
            keys.append(derived)

    if not keys:
        raise TokenEncryptionError(
            "No usable token encryption key. Set TOKEN_ENCRYPTION_KEY "
            "(Fernet) or ensure STRAVA_CLIENT_SECRET is configured. "
            "Generate one with: python -c \"from cryptography.fernet "
            "import Fernet; print(Fernet.generate_key().decode())\""
        )

    return keys


def encryption_key_status() -> dict:
    """Non-secret diagnostics for startup / health checks."""

    raw_key = (os.getenv("TOKEN_ENCRYPTION_KEY") or "").strip()
    has_secret = bool((os.getenv("STRAVA_CLIENT_SECRET") or "").strip())
    env_key_valid = False
    if raw_key:
        try:
            Fernet(raw_key.encode("utf-8"))
            env_key_valid = True
        except Exception:
            env_key_valid = False
    return {
        "token_encryption_key_set": bool(raw_key),
        "token_encryption_key_valid": env_key_valid,
        "strava_client_secret_set": has_secret,
        "can_encrypt": env_key_valid or has_secret,
        "encrypt_source": (
            "TOKEN_ENCRYPTION_KEY"
            if env_key_valid
            else ("STRAVA_CLIENT_SECRET" if has_secret else None)
        ),
    }


def _load_fernet() -> Fernet:
    return Fernet(_fernet_key_material()[0])


def _load_multi_fernet() -> MultiFernet:
    return MultiFernet([Fernet(k) for k in _fernet_key_material()])


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

    multi = _load_multi_fernet()

    try:
        return multi.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise TokenEncryptionError(
            "Failed to decrypt Strava token. "
            "Check TOKEN_ENCRYPTION_KEY or re-authenticate."
        ) from exc
