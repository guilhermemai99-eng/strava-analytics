import os
import time

import requests
from dotenv import load_dotenv

from strava_auth import StravaAuth, utcnow
from token_crypto import (
    TOKEN_VERSION_FERNET,
    TOKEN_VERSION_PLAINTEXT,
    TokenEncryptionError,
    decrypt_token,
    encrypt_token,
)


load_dotenv()


STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"

REFRESH_MARGIN_SECONDS = 60


class StravaTokenError(Exception):
    pass


def _read_stored_token(raw_value, token_version):
    """Return plaintext from a Fernet-encrypted DB column."""

    if raw_value is None:
        return None

    version = (
        TOKEN_VERSION_PLAINTEXT
        if token_version is None
        else int(token_version)
    )

    if version == TOKEN_VERSION_PLAINTEXT:
        raise StravaTokenError(
            "Strava token is still plaintext (token_version=0). "
            "Run scripts/encrypt_strava_tokens.py, then re-login if needed."
        )

    if version == TOKEN_VERSION_FERNET:
        try:
            return decrypt_token(raw_value)
        except TokenEncryptionError as exc:
            raise StravaTokenError(str(exc)) from exc

    raise StravaTokenError(
        f"Unsupported token_version={version}."
    )


def store_strava_tokens(
    auth,
    access_token,
    refresh_token=None,
    expires_at=None,
):
    """Encrypt tokens in-place and mark token_version=1."""

    if not access_token:
        raise StravaTokenError(
            "access_token é obrigatório ao guardar tokens."
        )

    try:
        auth.access_token = encrypt_token(access_token)

        if refresh_token is not None:
            auth.refresh_token = encrypt_token(refresh_token)

        auth.token_version = TOKEN_VERSION_FERNET
        auth.updated_at = utcnow()

        if expires_at is not None:
            auth.expires_at = expires_at

    except TokenEncryptionError as exc:
        raise StravaTokenError(str(exc)) from exc

    return auth


def upgrade_plaintext_tokens(db) -> dict:
    """Encrypt all token_version=0 rows in-place. Safe to run on every boot."""

    pending = (
        db.query(StravaAuth)
        .filter(
            (StravaAuth.token_version == TOKEN_VERSION_PLAINTEXT)
            | (StravaAuth.token_version.is_(None))
        )
        .order_by(StravaAuth.id)
        .all()
    )

    upgraded = 0
    skipped = 0

    for auth in pending:
        access = auth.access_token
        refresh = auth.refresh_token

        if not access:
            skipped += 1
            continue

        store_strava_tokens(
            auth,
            access_token=access,
            refresh_token=refresh,
            expires_at=auth.expires_at,
        )

        if auth.access_token == access:
            raise StravaTokenError(
                f"id={auth.id}: access_token still equals plaintext after encrypt"
            )

        upgraded += 1

    if upgraded:
        db.commit()

    remaining = (
        db.query(StravaAuth)
        .filter(
            (StravaAuth.token_version == TOKEN_VERSION_PLAINTEXT)
            | (StravaAuth.token_version.is_(None))
        )
        .count()
    )

    return {
        "upgraded": upgraded,
        "skipped": skipped,
        "remaining_plaintext": remaining,
    }


def get_valid_access_token(
    db,
    athlete_id,
    force_refresh=False
):

    if athlete_id is None:

        raise StravaTokenError(
            "athlete_id é obrigatório."
        )


    auth = (

        db.query(
            StravaAuth
        )

        .filter(
            StravaAuth.athlete_id
            ==
            athlete_id
        )

        .one_or_none()

    )


    if not auth:

        raise StravaTokenError(
            "Não existe autenticação Strava "
            "para este atleta."
        )


    now = int(
        time.time()
    )


    expires_at = auth.expires_at or 0

    plaintext_access = _read_stored_token(
        auth.access_token,
        auth.token_version,
    )


    if (
        not force_refresh
        and
        plaintext_access
        and
        expires_at
        >
        now + REFRESH_MARGIN_SECONDS
    ):

        return plaintext_access


    return _refresh_access_token(
        db,
        auth
    )


def _refresh_access_token(db, auth):

    client_id = os.getenv(
        "STRAVA_CLIENT_ID"
    )

    client_secret = os.getenv(
        "STRAVA_CLIENT_SECRET"
    )


    if (
        not client_id
        or
        not client_secret
    ):

        raise StravaTokenError(
            "Credenciais Strava em falta "
            "no servidor."
        )


    plaintext_refresh = _read_stored_token(
        auth.refresh_token,
        auth.token_version,
    )


    if not plaintext_refresh:

        raise StravaTokenError(
            "Não existe refresh_token "
            "para este atleta."
        )


    response = requests.post(

        STRAVA_TOKEN_URL,

        data={

            "client_id":
                client_id,

            "client_secret":
                client_secret,

            "grant_type":
                "refresh_token",

            "refresh_token":
                plaintext_refresh

        },

        timeout=15

    )


    if response.status_code != 200:

        raise StravaTokenError(
            "Não foi possível renovar "
            "o token Strava."
        )


    token_data = response.json()


    access_token = token_data.get(
        "access_token"
    )

    refresh_token = token_data.get(
        "refresh_token"
    )

    expires_at = token_data.get(
        "expires_at"
    )


    if not access_token:

        raise StravaTokenError(
            "O Strava não devolveu "
            "um access_token."
        )


    # Keep previous refresh if Strava omits a new one.
    store_strava_tokens(
        auth,
        access_token=access_token,
        refresh_token=(
            refresh_token
            if refresh_token
            else plaintext_refresh
        ),
        expires_at=expires_at,
    )


    db.commit()


    return _read_stored_token(
        auth.access_token,
        auth.token_version,
    )
