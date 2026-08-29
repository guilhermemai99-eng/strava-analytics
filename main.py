from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse, FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import os
import secrets
import requests

from urllib.parse import urlencode

from dotenv import load_dotenv

from database import SessionLocal
from models import Activity
from strava_auth import StravaAuth
from athlete import Athlete
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
from profile_helpers import (
    ProfileValidationError,
    apply_profile_patch,
    ensure_handle,
    serialize_profile,
)
from avatar_helpers import AvatarValidationError, validate_avatar_upload
from feed_helpers import serialize_feed_item
from explore_helpers import (
    get_public_athlete,
    public_athlete_payload,
    search_public_athletes,
    suggest_nearby,
    suggest_new_faces,
    suggest_recently_active,
)
from follow_helpers import (
    FollowError,
    create_follow,
    delete_follow,
    followed_athlete_ids,
    follower_count,
    following_count,
    get_athlete_by_handle,
    get_athlete_by_id,
    list_followers,
    list_following,
    relationship_payload,
    suggest_people,
)
from account_helpers import AccountDeleteError, delete_athlete_account
from public_profile_helpers import can_view_profile, serialize_public_profile
from dm_helpers import (
    DmError,
    get_conversation_for_viewer,
    get_or_create_conversation,
    list_conversations,
    list_messages,
    mark_conversation_read,
    send_message,
    serialize_message,
    total_unread,
)
from ai_coach_chat import (
    CoachChatError,
    build_coach_context,
    generate_coach_reply,
    welcome_message,
)
from coach_chat_helpers import (
    add_coach_message,
    clear_coach_messages,
    history_for_model,
    list_coach_messages,
    serialize_coach_message,
    trim_coach_messages,
)

from import_strava import sync_strava_activities
from strava_tokens import StravaTokenError, store_strava_tokens

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


# pydantic models for request bodies live near their routes


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


def run_startup_token_encryption() -> None:
    """Encrypt any leftover plaintext tokens before serving traffic."""

    from token_crypto import TokenEncryptionError, encryption_key_status
    from strava_tokens import upgrade_plaintext_tokens

    status = encryption_key_status()
    print(
        "[start] Token encryption status: "
        f"key_set={status['token_encryption_key_set']} "
        f"key_valid={status['token_encryption_key_valid']} "
        f"source={status['encrypt_source']}"
    )

    if not status["can_encrypt"]:
        print(
            "[start] No usable encryption key; "
            "skipping plaintext token upgrade."
        )
        return

    db = SessionLocal()
    try:
        result = upgrade_plaintext_tokens(db)
        print(
            "[start] Token encryption upgrade: "
            f"upgraded={result['upgraded']} "
            f"skipped={result['skipped']} "
            f"remaining_plaintext={result['remaining_plaintext']}"
        )
        if result["remaining_plaintext"]:
            print(
                "[start] WARNING: plaintext Strava tokens remain; "
                "those athletes must re-OAuth or be fixed manually."
            )
    except (TokenEncryptionError, StravaTokenError) as exc:
        # Never block boot on upgrade — login fallback still works.
        print(f"[start] Token encryption upgrade failed: {exc}")
    finally:
        db.close()


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("SKIP_STARTUP_MIGRATIONS") != "1":
        run_startup_migrations()
    else:
        print("[start] Skipping startup migrations (SKIP_STARTUP_MIGRATIONS=1).")
    run_startup_token_encryption()
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

        raise HTTPException(
            status_code=401,
            detail="Utilizador não autenticado."
        )

    return athlete_id


# ============================================================
# HOME
# ============================================================

@app.get("/health")
def health():
    """Lightweight probe for Railway / load balancers (no auth, no DB)."""
    return {"status": "ok"}


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

    if not STRAVA_CLIENT_ID or not STRAVA_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail=(
                "Strava OAuth não está configurado. "
                "Define STRAVA_CLIENT_ID e STRAVA_CLIENT_SECRET."
            ),
        )

    # Gerar estado único
    state = secrets.token_urlsafe(
        32
    )

    db = SessionLocal()

    try:

        cleanup_expired_oauth_states(db)
        create_oauth_state(db, state)

    except Exception as error:
        db.rollback()
        print("strava_login db error:", repr(error))
        raise HTTPException(
            status_code=503,
            detail=(
                "Não foi possível iniciar o login Strava. "
                "Tenta novamente dentro de momentos."
            ),
        ) from error

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

    try:

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

    except requests.RequestException as error:

        print("strava_callback token exchange network error:", repr(error))
        raise HTTPException(
            status_code=502,
            detail=(
                "Não foi possível contactar o Strava. "
                "Tenta novamente dentro de momentos."
            ),
        ) from error


    if token_response.status_code != 200:

        print(
            "strava_callback token exchange failed:",
            token_response.status_code,
            token_response.text[:500],
        )
        raise HTTPException(
            status_code=502,
            detail="Erro ao obter tokens do Strava. Tenta fazer login outra vez.",
        )


    try:

        token_data = token_response.json()

    except ValueError as error:

        print("strava_callback invalid token JSON:", repr(error))
        raise HTTPException(
            status_code=502,
            detail="Resposta inválida do Strava ao trocar o código OAuth.",
        ) from error


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
    raw_session_token = None

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

            store_strava_tokens(
                existing_auth,
                access_token=token_data.get(
                    "access_token"
                ),
                refresh_token=token_data.get(
                    "refresh_token"
                ),
                expires_at=token_data.get(
                    "expires_at"
                ),
            )


        else:

            new_auth = StravaAuth(
                athlete_id=athlete_id,
            )

            store_strava_tokens(
                new_auth,
                access_token=token_data.get(
                    "access_token"
                ),
                refresh_token=token_data.get(
                    "refresh_token"
                ),
                expires_at=token_data.get(
                    "expires_at"
                ),
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

    except StravaTokenError as error:
        db.rollback()
        print("strava_callback token error:", repr(error))
        raise HTTPException(
            status_code=503,
            detail=(
                "Não foi possível guardar a autenticação Strava. "
                f"{error}"
            ),
        ) from error

    except Exception as error:
        db.rollback()
        print("strava_callback unexpected error:", repr(error))
        raise HTTPException(
            status_code=500,
            detail=(
                "Erro interno ao concluir o login. "
                "Tenta novamente dentro de momentos."
            ),
        ) from error

    finally:

        db.close()

    if not raw_session_token:
        raise HTTPException(
            status_code=500,
            detail="Sessão não foi criada após o login.",
        )


    # ========================================================
    # CRIAR SESSÃO (cookie opaco)
    # ========================================================

    response = RedirectResponse(

        url="/dashboard?boot=1",

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


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    handle: Optional[str] = None
    bio: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    is_profile_public: Optional[bool] = None


# ============================================================
# PROFILE — /api/me/*
# ============================================================

@app.get("/api/me/profile")
def get_my_profile(request: Request):
    athlete_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        athlete = (
            db.query(Athlete)
            .filter(Athlete.id == athlete_id)
            .one_or_none()
        )
        if athlete is None:
            raise HTTPException(
                status_code=404,
                detail="Perfil não encontrado.",
            )

        athlete = ensure_handle(db, athlete)
        stats = get_summary(athlete_id)
        payload = serialize_profile(athlete, include_stats=stats)
        payload["follower_count"] = follower_count(db, athlete_id)
        payload["following_count"] = following_count(db, athlete_id)
        payload["followers_count"] = payload["follower_count"]
        payload["is_self"] = True
        payload["is_following"] = False
        payload["is_followed_by"] = False
        payload["is_mutual"] = False
        payload["relationship"] = {
            "is_self": True,
            "is_following": False,
            "is_followed_by": False,
            "is_mutual": False,
        }
        return payload
    finally:
        db.close()


@app.patch("/api/me/profile")
def patch_my_profile(request: Request, body: ProfileUpdate):
    athlete_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        athlete = (
            db.query(Athlete)
            .filter(Athlete.id == athlete_id)
            .one_or_none()
        )
        if athlete is None:
            raise HTTPException(
                status_code=404,
                detail="Perfil não encontrado.",
            )

        # Only apply fields explicitly sent by the client.
        payload = body.model_dump(exclude_unset=True)
        try:
            athlete = apply_profile_patch(db, athlete, payload)
        except ProfileValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if not athlete.handle:
            athlete = ensure_handle(db, athlete)

        stats = get_summary(athlete_id)
        out = serialize_profile(athlete, include_stats=stats)
        out["follower_count"] = follower_count(db, athlete_id)
        out["following_count"] = following_count(db, athlete_id)
        out["followers_count"] = out["follower_count"]
        out["is_self"] = True
        out["is_following"] = False
        out["is_followed_by"] = False
        out["is_mutual"] = False
        out["relationship"] = {
            "is_self": True,
            "is_following": False,
            "is_followed_by": False,
            "is_mutual": False,
        }
        return out
    finally:
        db.close()


def _avatar_bytes_response(athlete: Athlete) -> Response:
    if not athlete.avatar_data or not athlete.avatar_content_type:
        raise HTTPException(
            status_code=404,
            detail="Sem foto de perfil personalizada.",
        )
    return Response(
        content=bytes(athlete.avatar_data),
        media_type=athlete.avatar_content_type,
        headers={
            "Cache-Control": "private, max-age=3600",
        },
    )


@app.get("/api/me/avatar")
def get_my_avatar(request: Request):
    athlete_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        athlete = (
            db.query(Athlete)
            .filter(Athlete.id == athlete_id)
            .one_or_none()
        )
        if athlete is None:
            raise HTTPException(
                status_code=404,
                detail="Sem foto de perfil personalizada.",
            )
        return _avatar_bytes_response(athlete)
    finally:
        db.close()


@app.get("/api/athletes/{athlete_id}/avatar")
def get_athlete_avatar(athlete_id: int, request: Request):
    """Custom avatar for Explore cards. Own always ok; others need public profile."""
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        target = (
            db.query(Athlete)
            .filter(Athlete.id == athlete_id)
            .one_or_none()
        )
        if target is None:
            raise HTTPException(status_code=404, detail="Athlete not found")
        if target.id != viewer_id and not bool(target.is_profile_public):
            raise HTTPException(status_code=404, detail="Athlete not found")
        return _avatar_bytes_response(target)
    finally:
        db.close()


@app.get("/api/athletes/{athlete_id}/profile")
def get_athlete_public_profile(athlete_id: int, request: Request):
    """Public profile peek. Private profiles return 404 (no enumeration leak)."""
    require_athlete_id(request)
    db = SessionLocal()
    try:
        target = get_public_athlete(db, athlete_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Athlete not found")
        return public_athlete_payload(db, target)
    finally:
        db.close()


@app.post("/api/me/avatar")
async def upload_my_avatar(
    request: Request,
    file: UploadFile = File(...),
):
    athlete_id = require_athlete_id(request)
    data = await file.read()

    try:
        content_type = validate_avatar_upload(
            data,
            declared_type=file.content_type,
        )
    except AvatarValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db = SessionLocal()
    try:
        athlete = (
            db.query(Athlete)
            .filter(Athlete.id == athlete_id)
            .one_or_none()
        )
        if athlete is None:
            raise HTTPException(
                status_code=404,
                detail="Perfil não encontrado.",
            )

        athlete.avatar_data = data
        athlete.avatar_content_type = content_type
        from athlete import utcnow as athlete_utcnow

        athlete.updated_at = athlete_utcnow()
        db.commit()
        db.refresh(athlete)

        stats = get_summary(athlete_id)
        return serialize_profile(athlete, include_stats=stats)
    finally:
        db.close()


@app.delete("/api/me/avatar")
def delete_my_avatar(request: Request):
    athlete_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        athlete = (
            db.query(Athlete)
            .filter(Athlete.id == athlete_id)
            .one_or_none()
        )
        if athlete is None:
            raise HTTPException(
                status_code=404,
                detail="Perfil não encontrado.",
            )

        athlete.avatar_data = None
        athlete.avatar_content_type = None
        from athlete import utcnow as athlete_utcnow

        athlete.updated_at = athlete_utcnow()
        db.commit()
        db.refresh(athlete)

        stats = get_summary(athlete_id)
        return serialize_profile(athlete, include_stats=stats)
    finally:
        db.close()


# ============================================================
# LOGOUT
# ============================================================

def _clear_session_cookie(response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=_cookie_secure(),
        httponly=True,
        samesite="lax",
    )


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

    _clear_session_cookie(response)

    return response


@app.delete("/api/me/account")
def delete_my_account(request: Request):
    """Permanently delete the authenticated athlete and dependent data."""
    athlete_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        try:
            result = delete_athlete_account(db, athlete_id)
        except AccountDeleteError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        db.close()

    response = JSONResponse(
        content={
            "ok": True,
            "message": "Your account has officially vanished into the void.",
            **result,
        }
    )
    _clear_session_cookie(response)
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

    try:

        return sync_strava_activities(
            athlete_id
        )

    except StravaTokenError as error:

        return {

            "error":
                str(error)

        }

    except Exception as error:

        print(
            "strava_sync unexpected error:",
            repr(error)
        )

        return {

            "error":
                "Falha ao sincronizar atividades. "
                "Tenta novamente dentro de momentos."

        }


# ============================================================
# PUBLIC PROFILES + FOLLOWS — /api/profiles/{handle}
# Also aliased under /api/users/{id} for Instagram-style clients.
# ============================================================

def _require_visible_profile(db, *, handle: str | None = None, athlete_id: int | None = None, viewer_id: int):
    if handle is not None:
        target = get_athlete_by_handle(db, handle)
    else:
        target = get_athlete_by_id(db, int(athlete_id))
    if target is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    viewer = db.query(Athlete).filter(Athlete.id == viewer_id).one_or_none()
    if viewer is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado.")
    if not can_view_profile(viewer, target):
        raise HTTPException(status_code=404, detail="Profile not found")
    return target, viewer


def _people_list_response(kind: str, target: Athlete, payload: dict) -> dict:
    return {
        "handle": target.handle,
        "athlete_id": target.id,
        "kind": kind,
        **payload,
    }


@app.get("/api/profiles/suggestions")
def get_follow_suggestions(request: Request, limit: int = 8):
    """Suggested runners to follow — simple public / nearby heuristic."""
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        viewer = get_athlete_by_id(db, viewer_id)
        if viewer is None:
            raise HTTPException(status_code=404, detail="Perfil não encontrado.")
        people = suggest_people(db, viewer=viewer, limit=limit)
        return {"people": people, "count": len(people)}
    finally:
        db.close()


@app.get("/api/profiles/{handle}")
def get_public_profile(handle: str, request: Request):
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        target, viewer = _require_visible_profile(
            db, handle=handle, viewer_id=viewer_id
        )
        return serialize_public_profile(db, target=target, viewer=viewer)
    finally:
        db.close()


@app.get("/api/profiles/{handle}/relationship")
def get_profile_relationship(handle: str, request: Request):
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        target, _viewer = _require_visible_profile(
            db, handle=handle, viewer_id=viewer_id
        )
        return relationship_payload(
            db, viewer_id=viewer_id, target_id=target.id
        )
    finally:
        db.close()


@app.get("/api/profiles/{handle}/followers")
def get_profile_followers(
    handle: str,
    request: Request,
    limit: int = 30,
    offset: int = 0,
    q: str = "",
):
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        target, _viewer = _require_visible_profile(
            db, handle=handle, viewer_id=viewer_id
        )
        payload = list_followers(
            db,
            athlete_id=target.id,
            viewer_id=viewer_id,
            limit=limit,
            offset=offset,
            q=q,
        )
        return _people_list_response("followers", target, payload)
    finally:
        db.close()


@app.get("/api/profiles/{handle}/following")
def get_profile_following(
    handle: str,
    request: Request,
    limit: int = 30,
    offset: int = 0,
    q: str = "",
):
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        target, _viewer = _require_visible_profile(
            db, handle=handle, viewer_id=viewer_id
        )
        payload = list_following(
            db,
            athlete_id=target.id,
            viewer_id=viewer_id,
            limit=limit,
            offset=offset,
            q=q,
        )
        return _people_list_response("following", target, payload)
    finally:
        db.close()


@app.post("/api/profiles/{handle}/follow")
def follow_profile(handle: str, request: Request):
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        target = get_athlete_by_handle(db, handle)
        if target is None or (
            target.id != viewer_id and not bool(target.is_profile_public)
        ):
            raise HTTPException(status_code=404, detail="Profile not found")
        try:
            create_follow(db, follower_id=viewer_id, following_id=target.id)
        except FollowError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        viewer = db.query(Athlete).filter(Athlete.id == viewer_id).one()
        return serialize_public_profile(db, target=target, viewer=viewer)
    finally:
        db.close()


@app.delete("/api/profiles/{handle}/follow")
def unfollow_profile(handle: str, request: Request):
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        target = get_athlete_by_handle(db, handle)
        if target is None:
            raise HTTPException(status_code=404, detail="Profile not found")
        delete_follow(db, follower_id=viewer_id, following_id=target.id)
        viewer = db.query(Athlete).filter(Athlete.id == viewer_id).one()
        if not can_view_profile(viewer, target):
            return {
                "handle": target.handle,
                "is_following": False,
                "is_followed_by": False,
                "is_mutual": False,
                "follower_count": follower_count(db, target.id),
                "following_count": following_count(db, target.id),
                "followers_count": follower_count(db, target.id),
                "is_self": False,
            }
        return serialize_public_profile(db, target=target, viewer=viewer)
    finally:
        db.close()


# --- /api/users/{athlete_id} aliases (session auth; never trust client ids for actor) ---

@app.get("/api/users/{athlete_id}")
def get_user_profile(athlete_id: int, request: Request):
    """Full public profile by internal athlete id (Follow/graph never requires a handle)."""
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        target, viewer = _require_visible_profile(
            db, athlete_id=athlete_id, viewer_id=viewer_id
        )
        return serialize_public_profile(db, target=target, viewer=viewer)
    finally:
        db.close()


@app.get("/api/users/{athlete_id}/relationship")
def get_user_relationship(athlete_id: int, request: Request):
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        target, _viewer = _require_visible_profile(
            db, athlete_id=athlete_id, viewer_id=viewer_id
        )
        return relationship_payload(
            db, viewer_id=viewer_id, target_id=target.id
        )
    finally:
        db.close()


@app.get("/api/users/{athlete_id}/followers")
def get_user_followers(
    athlete_id: int,
    request: Request,
    limit: int = 30,
    offset: int = 0,
    q: str = "",
):
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        target, _viewer = _require_visible_profile(
            db, athlete_id=athlete_id, viewer_id=viewer_id
        )
        payload = list_followers(
            db,
            athlete_id=target.id,
            viewer_id=viewer_id,
            limit=limit,
            offset=offset,
            q=q,
        )
        return _people_list_response("followers", target, payload)
    finally:
        db.close()


@app.get("/api/users/{athlete_id}/following")
def get_user_following(
    athlete_id: int,
    request: Request,
    limit: int = 30,
    offset: int = 0,
    q: str = "",
):
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        target, _viewer = _require_visible_profile(
            db, athlete_id=athlete_id, viewer_id=viewer_id
        )
        payload = list_following(
            db,
            athlete_id=target.id,
            viewer_id=viewer_id,
            limit=limit,
            offset=offset,
            q=q,
        )
        return _people_list_response("following", target, payload)
    finally:
        db.close()


@app.post("/api/users/{athlete_id}/follow")
def follow_user(athlete_id: int, request: Request):
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        target = get_athlete_by_id(db, athlete_id)
        if target is None or (
            target.id != viewer_id and not bool(target.is_profile_public)
        ):
            raise HTTPException(status_code=404, detail="Profile not found")
        try:
            create_follow(db, follower_id=viewer_id, following_id=target.id)
        except FollowError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        viewer = db.query(Athlete).filter(Athlete.id == viewer_id).one()
        return serialize_public_profile(db, target=target, viewer=viewer)
    finally:
        db.close()


@app.delete("/api/users/{athlete_id}/follow")
def unfollow_user(athlete_id: int, request: Request):
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        target = get_athlete_by_id(db, athlete_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Profile not found")
        delete_follow(db, follower_id=viewer_id, following_id=target.id)
        viewer = db.query(Athlete).filter(Athlete.id == viewer_id).one()
        if not can_view_profile(viewer, target):
            return {
                "athlete_id": target.id,
                "is_following": False,
                "is_followed_by": False,
                "is_mutual": False,
                "follower_count": follower_count(db, target.id),
                "followers_count": follower_count(db, target.id),
                "following_count": following_count(db, target.id),
                "is_self": False,
            }
        return serialize_public_profile(db, target=target, viewer=viewer)
    finally:
        db.close()


@app.get("/api/feed/following-ids")
def get_following_ids_for_feed(request: Request):
    """Prep for Following Feed: list of athlete IDs the viewer follows."""
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        ids = followed_athlete_ids(db, viewer_id)
        return {"athlete_ids": ids, "count": len(ids)}
    finally:
        db.close()


# ============================================================
# EXPLORE — discovery of public runners
# ============================================================

@app.get("/api/explore")
def get_explore(request: Request):
    """Discovery feed: nearby, recently active, and new faces. Public only."""
    athlete_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        athlete = (
            db.query(Athlete)
            .filter(Athlete.id == athlete_id)
            .one_or_none()
        )
        if athlete is None:
            raise HTTPException(
                status_code=404,
                detail="Perfil não encontrado.",
            )

        nearby = suggest_nearby(db, viewer=athlete, limit=8)
        recent = suggest_recently_active(db, viewer_id=athlete_id, limit=8)
        new_faces = suggest_new_faces(db, viewer_id=athlete_id, limit=6)

        return {
            "me": {
                "athlete_id": athlete.id,
                "handle": athlete.handle,
                "is_profile_public": bool(athlete.is_profile_public),
                "city": athlete.city,
                "country": athlete.country,
            },
            "sections": [
                {
                    "id": "nearby",
                    "title": "Near you",
                    "empty_hint": (
                        "Add your city in Settings, or nobody nearby is public yet."
                    ),
                    "athletes": nearby,
                },
                {
                    "id": "recent",
                    "title": "Recently active",
                    "empty_hint": (
                        "Quiet out there. Public runners who synced lately show up here."
                    ),
                    "athletes": recent,
                },
                {
                    "id": "new",
                    "title": "New faces",
                    "empty_hint": (
                        "No fresh public profiles yet. Be the first — "
                        "flip the toggle in Settings."
                    ),
                    "athletes": new_faces,
                },
            ],
        }
    finally:
        db.close()


@app.get("/api/explore/search")
def get_explore_search(request: Request, q: str = ""):
    """Search public athletes by name, handle, or city."""
    athlete_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        results = search_public_athletes(
            db,
            query=q,
            viewer_id=athlete_id,
            limit=20,
        )
        return {
            "q": (q or "").strip(),
            "results": results,
            "count": len(results),
        }
    finally:
        db.close()


# ============================================================
# FEED — atividades como posts
# ============================================================

@app.get("/api/feed")
def get_feed(
    request: Request,
    limit: int = 30,
):
    """Own-athlete activity feed (follow graph lands later)."""

    athlete_id = require_athlete_id(request)
    safe_limit = max(1, min(int(limit), 50))

    db = SessionLocal()
    try:
        athlete = (
            db.query(Athlete)
            .filter(Athlete.id == athlete_id)
            .one_or_none()
        )
        if athlete is None:
            raise HTTPException(
                status_code=404,
                detail="Perfil não encontrado.",
            )

        activities = (
            db.query(Activity)
            .filter(Activity.athlete_id == athlete_id)
            .order_by(Activity.start_date_local.desc())
            .limit(safe_limit)
            .all()
        )

        items = [
            serialize_feed_item(activity, athlete)
            for activity in activities
        ]

        return {
            "scope": "self",
            "message": {
                "eyebrow": "Your runs. Front row.",
                "body": (
                    "The rest of the world is still lacing up. "
                    "Follows land later — for now, it’s all you."
                ),
            },
            "items": items,
            "count": len(items),
        }
    finally:
        db.close()


# ============================================================
# ACTIVITIES
# ============================================================

@app.get("/activities")
def get_activities(
    request: Request,
    limit: int | None = None,
):

    athlete_id = require_athlete_id(
        request
    )

    db = SessionLocal()

    try:

        query = (

            db.query(
                Activity
            )

            .filter(
                Activity.athlete_id
                ==
                athlete_id
            )

            .order_by(
                Activity.start_date_local.desc()
            )

        )

        if limit is not None:
            safe_limit = max(1, min(int(limit), 50))
            query = query.limit(safe_limit)

        activities = query.all()

        return activities


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
        "static/pulse.html"
    )


@app.get("/lab")
def analytics_lab(
    request: Request
):

    """Legacy analytics dashboard — kept reachable from Settings."""

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


class CoachChatRequest(BaseModel):
    message: str


# ============================================================
# DIRECT MESSAGES — mutual follow only
# ============================================================


class DmSendRequest(BaseModel):
    content: str


def _dm_http(exc: DmError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


@app.get("/api/dms")
def api_list_dms(request: Request, limit: int = 40):
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        items = list_conversations(db, viewer_id=viewer_id, limit=limit)
        return {
            "items": items,
            "unread_total": total_unread(db, viewer_id=viewer_id),
        }
    finally:
        db.close()


@app.get("/api/dms/unread-count")
def api_dms_unread_count(request: Request):
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        return {"unread_total": total_unread(db, viewer_id=viewer_id)}
    finally:
        db.close()


@app.post("/api/dms/with/{peer_id}")
def api_open_dm_with(peer_id: int, request: Request):
    """Get-or-create a 1:1 conversation. Requires mutual follow."""
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        conv = get_or_create_conversation(
            db, viewer_id=viewer_id, peer_id=peer_id
        )
        return get_conversation_for_viewer(
            db, conversation_id=conv.id, viewer_id=viewer_id
        )
    except DmError as exc:
        raise _dm_http(exc) from exc
    finally:
        db.close()


@app.get("/api/dms/{conversation_id}")
def api_get_dm(conversation_id: int, request: Request):
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        return get_conversation_for_viewer(
            db, conversation_id=conversation_id, viewer_id=viewer_id
        )
    except DmError as exc:
        raise _dm_http(exc) from exc
    finally:
        db.close()


@app.get("/api/dms/{conversation_id}/messages")
def api_list_dm_messages(
    conversation_id: int,
    request: Request,
    limit: int = 50,
    before_id: int | None = None,
):
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        messages = list_messages(
            db,
            conversation_id=conversation_id,
            viewer_id=viewer_id,
            limit=limit,
            before_id=before_id,
        )
        summary = get_conversation_for_viewer(
            db, conversation_id=conversation_id, viewer_id=viewer_id
        )
        return {
            "conversation": summary,
            "messages": messages,
        }
    except DmError as exc:
        raise _dm_http(exc) from exc
    finally:
        db.close()


@app.post("/api/dms/{conversation_id}/messages")
def api_send_dm(conversation_id: int, request: Request, body: DmSendRequest):
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        msg = send_message(
            db,
            conversation_id=conversation_id,
            sender_id=viewer_id,
            content=body.content,
        )
        return serialize_message(msg, viewer_id)
    except DmError as exc:
        raise _dm_http(exc) from exc
    finally:
        db.close()


@app.post("/api/dms/{conversation_id}/read")
def api_mark_dm_read(conversation_id: int, request: Request):
    viewer_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        return mark_conversation_read(
            db, conversation_id=conversation_id, viewer_id=viewer_id
        )
    except DmError as exc:
        raise _dm_http(exc) from exc
    finally:
        db.close()


# ============================================================
# AI COACH CHAT
# ============================================================

@app.get("/api/coach/messages")
def get_coach_messages(request: Request, limit: int = 40):
    athlete_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        rows = list_coach_messages(db, athlete_id, limit=limit)
        return {
            "welcome": welcome_message(),
            "messages": [serialize_coach_message(row) for row in rows],
            "count": len(rows),
        }
    finally:
        db.close()


@app.delete("/api/coach/messages")
def delete_coach_messages(request: Request):
    athlete_id = require_athlete_id(request)
    db = SessionLocal()
    try:
        deleted = clear_coach_messages(db, athlete_id)
        db.commit()
        return {"deleted": deleted, "welcome": welcome_message()}
    finally:
        db.close()


@app.post("/api/coach/chat")
def post_coach_chat(request: Request, body: CoachChatRequest):
    athlete_id = require_athlete_id(request)
    message = (body.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message required.")
    if len(message) > 1200:
        raise HTTPException(status_code=400, detail="Message too long.")

    weekly_data = get_weekly(athlete_id)
    performance_data = get_running_performance(athlete_id)
    summary_data = get_summary(athlete_id)
    evolution_data = calculate_evolution(weekly_data)
    performance_comparison = calculate_performance_comparison(athlete_id)
    athlete_score = calculate_athlete_score(
        evolution_data,
        performance_comparison,
        performance_data,
        athlete_id,
    )
    recommendation = get_recommendation(
        athlete_score,
        evolution_data,
        performance_comparison,
    )
    context = build_coach_context(
        weekly_data=weekly_data,
        performance_data=performance_data,
        summary_data=summary_data,
        evolution_data=evolution_data,
        performance_comparison=performance_comparison,
        recommendation=recommendation,
        athlete_score=athlete_score,
    )

    db = SessionLocal()
    try:
        prior = list_coach_messages(db, athlete_id, limit=24)
        history = history_for_model(prior)

        try:
            reply = generate_coach_reply(
                user_message=message,
                history=history,
                context=context,
            )
        except CoachChatError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        user_row = add_coach_message(db, athlete_id, "user", message)
        assistant_row = add_coach_message(db, athlete_id, "assistant", reply)
        trim_coach_messages(db, athlete_id)
        db.commit()
        db.refresh(user_row)
        db.refresh(assistant_row)

        return {
            "reply": reply,
            "user_message": serialize_coach_message(user_row),
            "assistant_message": serialize_coach_message(assistant_row),
        }
    finally:
        db.close()


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