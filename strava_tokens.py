import os
import time

import requests
from dotenv import load_dotenv

from strava_auth import StravaAuth


load_dotenv()


STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"

REFRESH_MARGIN_SECONDS = 60


class StravaTokenError(Exception):
    pass


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


    if (
        not force_refresh
        and
        auth.access_token
        and
        expires_at
        >
        now + REFRESH_MARGIN_SECONDS
    ):

        return auth.access_token


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


    if not auth.refresh_token:

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
                auth.refresh_token

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


    auth.access_token = access_token

    if refresh_token:

        auth.refresh_token = refresh_token

    if expires_at:

        auth.expires_at = expires_at


    db.commit()


    return auth.access_token
