from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import os
import secrets
import requests

from urllib.parse import urlencode

from dotenv import load_dotenv

from database import SessionLocal
from models import Activity
from strava_auth import StravaAuth
from oauth_helpers import (
    cleanup_expired_oauth_states,
    consume_oauth_state,
    create_oauth_state,
)
from athlete_helpers import upsert_athlete_from_strava
from session_helpers import (
    SESSION_COOKIE_NAME,
    SESSION_TTL_DAYS,
    create_session,
    resolve_athlete_id,
    revoke_session,
)

from import_strava import sync_strava_activities
from strava_tokens import StravaTokenError

from analytics import get_summary, get_weekly
from running_performance import get_running_performance
from insights import get_insights
from training_load import get_training_load

from ai_insights import generate_insights

from ai_cache import (
    load_ai_cache,
    save_ai_cache
)

from ai_context import build_ai_context

from performance_evolution import calculate_evolution
from performance_comparison import calculate_performance_comparison

from athlete_score import calculate_athlete_score

from ai_coach import get_recommendation

from weekly_training_plan import calculate_weekly_plan


# ============================================================
# CONFIGURAÇÃO
# ============================================================

load_dotenv()


# Schema is managed by Alembic (alembic upgrade head).
# Also run migrations on app startup so Railway still migrates
# even if the platform start command is overridden in the UI.


def run_startup_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    print("[start] Running database migrations from app startup...")
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    print("[start] Migrations complete.")


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_startup_migrations()
    yield


# ============================================================
# APLICAÇÃO
# ============================================================

app = FastAPI(
    title="Strava Analytics",
    lifespan=lifespan,
)


app.mount(
    "/static",
    StaticFiles(
        directory="static"
    ),
    name="static"
)


# ============================================================
# CREDENCIAIS STRAVA
# ============================================================

STRAVA_CLIENT_ID = os.getenv(
    "STRAVA_CLIENT_ID"
)

STRAVA_CLIENT_SECRET = os.getenv(
    "STRAVA_CLIENT_SECRET"
)

STRAVA_REDIRECT_URI = os.getenv(
    "STRAVA_REDIRECT_URI"
)


# ============================================================
# MODELO DE ATIVIDADE
# ============================================================

class ActivityCreate(BaseModel):

    name: str

    distance_km: float

    time_minutes: float

    average_heart_rate: int


# ============================================================
# HELPERS — AUTENTICAÇÃO
# ============================================================

def _cookie_secure() -> bool:
    return bool(
        os.getenv("RAILWAY_ENVIRONMENT")
        or os.getenv("SESSION_COOKIE_SECURE") == "1"
    )


def get_current_athlete_id(
    request: Request
):

    raw_token = request.cookies.get(
        SESSION_COOKIE_NAME
    )

    db = SessionLocal()

    try:

        return resolve_athlete_id(
            db,
            raw_token
        )

    finally:

        db.close()


def require_athlete_id(
    request: Request
):

    athlete_id = get_current_athlete_id(
        request
    )

    if not athlete_id:

        return None

    return athlete_id


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home(
    request: Request
):

    if get_current_athlete_id(
        request
    ):

        return RedirectResponse(
            url="/dashboard",
            status_code=302
        )

    return FileResponse(
        "static/login.html"
    )


# ============================================================
# STRAVA OAUTH — LOGIN
# ============================================================

@app.get("/auth/strava")
def strava_login():

    # Gerar estado único
    state = secrets.token_urlsafe(
        32
    )

    db = SessionLocal()

    try:

        cleanup_expired_oauth_states(db)
        create_oauth_state(db, state)

    finally:

        db.close()

    params = {

        "client_id":
            STRAVA_CLIENT_ID,

        "redirect_uri":
            STRAVA_REDIRECT_URI,

        "response_type":
            "code",

        "approval_prompt":
            "auto",

        "scope":
            "activity:read_all",

        "state":
            state
    }

    authorization_url = (

        "https://www.strava.com/oauth/authorize?"

        +
        urlencode(
            params
        )

    )

    return RedirectResponse(
        url=authorization_url,
        status_code=307
    )


# ============================================================
# STRAVA OAUTH — CALLBACK
# ============================================================

@app.get("/auth/strava/callback")
def strava_callback(
    request: Request,
    code: str = None,
    state: str = None
):

    # ========================================================
    # VALIDAR CODE
    # ========================================================

    if not code:

        return {

            "error":
                "Autorização cancelada ou sem código."

        }


    # ========================================================
    # VALIDAR STATE
    # ========================================================

    db = SessionLocal()

    try:

        state_ok = consume_oauth_state(db, state)

    finally:

        db.close()

    if not state_ok:

        return {

            "error":
                "Estado OAuth inválido."

        }


    # ========================================================
    # TROCAR CODE POR TOKENS
    # ========================================================

    token_response = requests.post(

        "https://www.strava.com/oauth/token",

        params={

            "client_id":
                STRAVA_CLIENT_ID,

            "client_secret":
                STRAVA_CLIENT_SECRET,

            "code":
                code,

            "grant_type":
                "authorization_code"

        },

        timeout=15
    )


    if token_response.status_code != 200:

        return {

            "error":
                "Erro ao obter tokens do Strava.",

            "details":
                token_response.text

        }


    token_data = (
        token_response.json()
    )


    athlete = token_data.get(
        "athlete",
        {}
    )


    athlete_id = athlete.get(
        "id"
    )


    # ========================================================
    # VALIDAR ATLETA
    # ========================================================

    if not athlete_id:

        return {

            "error":
                "O Strava não devolveu os dados do atleta."

        }


    # ========================================================
    # GUARDAR / ATUALIZAR ATLETA + STRAVA AUTH
    # ========================================================

    db = SessionLocal()

    try:

        upsert_athlete_from_strava(db, athlete)

        existing_auth = (

            db.query(
                StravaAuth
            )

            .filter(
                StravaAuth.athlete_id
                ==
                athlete_id
            )

            .first()

        )


        if existing_auth:

            existing_auth.access_token = (

                token_data.get(
                    "access_token"
                )

            )

            existing_auth.refresh_token = (

                token_data.get(
                    "refresh_token"
                )

            )

            existing_auth.expires_at = (

                token_data.get(
                    "expires_at"
                )

            )


        else:

            new_auth = StravaAuth(

                athlete_id=
                    athlete_id,

                access_token=
                    token_data.get(
                        "access_token"
                    ),

                refresh_token=
                    token_data.get(
                        "refresh_token"
                    ),

                expires_at=
                    token_data.get(
                        "expires_at"
                    )

            )

            db.add(
                new_auth
            )


        db.commit()

        raw_session_token = create_session(
            db,
            athlete_id,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )


    finally:

        db.close()


    # ========================================================
    # CRIAR SESSÃO (cookie opaco)
    # ========================================================

    response = RedirectResponse(

        url="/dashboard",

        status_code=302

    )


    response.set_cookie(

        key=SESSION_COOKIE_NAME,

        value=raw_session_token,

        httponly=True,

        secure=_cookie_secure(),

        max_age=60 * 60 * 24 * SESSION_TTL_DAYS,

        samesite="lax"

    )


    return response


# ============================================================
# AUTENTICAÇÃO — UTILIZADOR ATUAL
# ============================================================

@app.get("/auth/me")
def get_current_athlete(
    request: Request
):

    athlete_id = get_current_athlete_id(
        request
    )


    if not athlete_id:

        return {

            "authenticated":
                False

        }


    return {

        "authenticated":
            True,

        "athlete_id":
            athlete_id

    }


# ============================================================
# LOGOUT
# ============================================================

@app.get("/auth/logout")
def logout(request: Request):

    raw_token = request.cookies.get(
        SESSION_COOKIE_NAME
    )

    db = SessionLocal()

    try:

        revoke_session(db, raw_token)

    finally:

        db.close()

    response = RedirectResponse(
        url="/"
    )

    response.delete_cookie(
        SESSION_COOKIE_NAME
    )

    return response


# ============================================================
# STRAVA — SINCRONIZAÇÃO
# ============================================================

@app.post("/strava/sync")
def strava_sync(
    request: Request
):

    athlete_id = require_athlete_id(
        request
    )


    if not athlete_id:

        return {

            "error":
                "Utilizador não autenticado."

        }


    try:

        return sync_strava_activities(
            athlete_id
        )

    except StravaTokenError as error:

        return {

            "error":
                str(error)

        }


# ============================================================
# ACTIVITIES
# ============================================================

@app.get("/activities")
def get_activities(
    request: Request
):

    athlete_id = require_athlete_id(
        request
    )


    if not athlete_id:

        return {

            "error":
                "Utilizador não autenticado."

        }


    db = SessionLocal()

    try:

        activities = (

            db.query(
                Activity
            )

            .filter(
                Activity.athlete_id
                ==
                athlete_id
            )

            .all()

        )

        return activities


    finally:

        db.close()


# ============================================================
# CRIAR ATIVIDADE
# ============================================================

@app.post("/activities")
def create_activity(
    request: Request,
    activity: ActivityCreate
):

    athlete_id = require_athlete_id(
        request
    )


    if not athlete_id:

        return {

            "error":
                "Utilizador não autenticado."

        }


    db = SessionLocal()

    try:

        new_activity = Activity(

            athlete_id=
                athlete_id,

            name=
                activity.name,

            distance_km=
                activity.distance_km,

            time_minutes=
                activity.time_minutes,

            average_heart_rate=
                activity.average_heart_rate

        )


        db.add(
            new_activity
        )

        db.commit()

        db.refresh(
            new_activity
        )


        return new_activity


    finally:

        db.close()


# ============================================================
# ANALYTICS — SUMMARY
# ============================================================

@app.get("/analytics/summary")
def analytics_summary(
    request: Request
):

    athlete_id = require_athlete_id(
        request
    )


    if not athlete_id:

        return {

            "error":
                "Utilizador não autenticado."

        }


    return get_summary(
        athlete_id
    )


# ============================================================
# ANALYTICS — WEEKLY
# ============================================================

@app.get("/analytics/weekly")
def analytics_weekly(
    request: Request
):

    athlete_id = require_athlete_id(
        request
    )


    if not athlete_id:

        return {

            "error":
                "Utilizador não autenticado."

        }


    return get_weekly(
        athlete_id
    )


# ============================================================
# ANALYTICS — PERFORMANCE
# ============================================================

@app.get("/analytics/performance")
def analytics_performance(
    request: Request
):

    athlete_id = require_athlete_id(
        request
    )


    if not athlete_id:

        return {

            "error":
                "Utilizador não autenticado."

        }


    return get_running_performance(
        athlete_id
    )


# ============================================================
# ANALYTICS — RUNNING PERFORMANCE
# ============================================================

@app.get(
    "/analytics/running-performance"
)
def running_performance(
    request: Request
):

    athlete_id = require_athlete_id(
        request
    )


    if not athlete_id:

        return {

            "error":
                "Utilizador não autenticado."

        }


    return get_running_performance(
        athlete_id
    )


# ============================================================
# ANALYTICS — INSIGHTS
# ============================================================

@app.get("/analytics/insights")
def analytics_insights(
    request: Request
):

    athlete_id = require_athlete_id(
        request
    )


    if not athlete_id:

        return {

            "error":
                "Utilizador não autenticado."

        }


    return get_insights(
        athlete_id
    )


# ============================================================
# ANALYTICS — TRAINING LOAD
# ============================================================

@app.get(
    "/analytics/training-load"
)
def analytics_training_load(
    request: Request
):

    athlete_id = require_athlete_id(
        request
    )


    if not athlete_id:

        return {

            "error":
                "Utilizador não autenticado."

        }


    return get_training_load(
        athlete_id
    )


# ============================================================
# ANALYTICS — EVOLUTION
# ============================================================

@app.get(
    "/analytics/evolution"
)
def analytics_evolution(
    request: Request
):

    athlete_id = require_athlete_id(
        request
    )


    if not athlete_id:

        return {

            "error":
                "Utilizador não autenticado."

        }


    weekly_data = get_weekly(
        athlete_id
    )


    return calculate_evolution(
        weekly_data
    )


# ============================================================
# ANALYTICS — PERFORMANCE COMPARISON
# ============================================================

@app.get(
    "/analytics/performance-comparison"
)
def analytics_performance_comparison(
    request: Request
):

    athlete_id = require_athlete_id(
        request
    )


    if not athlete_id:

        return {

            "error":
                "Utilizador não autenticado."

        }


    return calculate_performance_comparison(
        athlete_id
    )


# ============================================================
# ANALYTICS — AI CONTEXT
# ============================================================

@app.get(
    "/analytics/ai-context"
)
def analytics_ai_context(
    request: Request
):

    athlete_id = require_athlete_id(
        request
    )


    if not athlete_id:

        return {

            "error":
                "Utilizador não autenticado."

        }


    weekly_data = get_weekly(
        athlete_id
    )


    performance_data = (
        get_running_performance(
            athlete_id
        )
    )


    summary_data = get_summary(
        athlete_id
    )


    evolution_data = (
        calculate_evolution(
            weekly_data
        )
    )


    performance_comparison = (

        calculate_performance_comparison(
            athlete_id
        )

    )


    context = build_ai_context(

        weekly_data,

        performance_data,

        summary_data

    )


    context["evolution"] = (
        evolution_data
    )


    context["performance_comparison"] = (
        performance_comparison
    )


    return context


# ============================================================
# ANALYTICS — AI INSIGHTS
# ============================================================

@app.get(
    "/analytics/ai-insights"
)
def analytics_ai_insights(
    request: Request
):

    athlete_id = require_athlete_id(
        request
    )


    if not athlete_id:

        return {

            "error":
                "Utilizador não autenticado."

        }


    # --------------------------------------------------------
    # CACHE
    # --------------------------------------------------------

    cached = load_ai_cache(athlete_id)

    if cached:

        return cached


    # --------------------------------------------------------
    # DADOS
    # --------------------------------------------------------

    weekly_data = get_weekly(
        athlete_id
    )


    performance_data = (
        get_running_performance(
            athlete_id
        )
    )


    summary_data = get_summary(
        athlete_id
    )


    evolution_data = (
        calculate_evolution(
            weekly_data
        )
    )


    performance_comparison = (

        calculate_performance_comparison(
            athlete_id
        )

    )


    # --------------------------------------------------------
    # AI
    # --------------------------------------------------------

    insights = generate_insights(

        weekly_data,

        performance_data,

        summary_data,

        evolution_data,

        performance_comparison

    )


    # --------------------------------------------------------
    # CACHE
    # --------------------------------------------------------

    save_ai_cache(
    insights,
    athlete_id
    )


    # --------------------------------------------------------
    # RESPOSTA
    # --------------------------------------------------------

    return {

        "insights":
            insights

    }


# ============================================================
# DASHBOARD
# ============================================================

@app.get("/dashboard")
def dashboard(
    request: Request
):

    if not get_current_athlete_id(
        request
    ):

        return RedirectResponse(
            url="/",
            status_code=302
        )

    return FileResponse(
        "static/dashboard.html"
    )


# ============================================================
# ANALYTICS — ATHLETE SCORE
# ============================================================

@app.get(
    "/analytics/athlete-score"
)
def analytics_athlete_score(
    request: Request
):

    athlete_id = require_athlete_id(
        request
    )


    if not athlete_id:

        return {

            "error":
                "Utilizador não autenticado."

        }


    weekly_data = get_weekly(
        athlete_id
    )


    performance_data = (
        get_running_performance(
            athlete_id
        )
    )


    evolution_data = calculate_evolution(
        weekly_data
    )


    performance_comparison = (

        calculate_performance_comparison(
            athlete_id
        )

    )


    return calculate_athlete_score(

        evolution_data,

        performance_comparison,

        performance_data,

        athlete_id

    )


# ============================================================
# ANALYTICS — AI COACH
# ============================================================

@app.get(
    "/analytics/ai-coach"
)
def analytics_ai_coach(
    request: Request
):

    athlete_id = require_athlete_id(
        request
    )


    if not athlete_id:

        return {

            "error":
                "Utilizador não autenticado."

        }


    weekly_data = get_weekly(
        athlete_id
    )


    performance_data = (
        get_running_performance(
            athlete_id
        )
    )


    evolution_data = calculate_evolution(
        weekly_data
    )


    performance_comparison = (

        calculate_performance_comparison(
            athlete_id
        )

    )


    athlete_score = calculate_athlete_score(

        evolution_data,

        performance_comparison,

        performance_data,

        athlete_id

    )


    recommendation = get_recommendation(

        athlete_score,

        evolution_data,

        performance_comparison

    )


    return {

        "athlete_score":
            athlete_score,

        "recommendation":
            recommendation

    }


# ============================================================
# ANALYTICS — WEEKLY TRAINING PLAN
# ============================================================

@app.get(
    "/analytics/weekly-training-plan"
)
def analytics_weekly_training_plan(
    request: Request
):

    athlete_id = require_athlete_id(
        request
    )


    if not athlete_id:

        return {

            "error":
                "Utilizador não autenticado."

        }


    weekly_data = get_weekly(
        athlete_id
    )


    performance_data = (
        get_running_performance(
            athlete_id
        )
    )


    evolution_data = calculate_evolution(
        weekly_data
    )


    performance_comparison = (

        calculate_performance_comparison(
            athlete_id
        )

    )


    athlete_score = calculate_athlete_score(

        evolution_data,

        performance_comparison,

        performance_data,

        athlete_id

    )


    return calculate_weekly_plan(

        athlete_score,

        evolution_data,

        performance_comparison

    )