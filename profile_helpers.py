"""Profile helpers: display identity, handle validation, serialization."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from athlete import Athlete, utcnow
from sqlalchemy.orm import Session


HANDLE_RE = re.compile(r"^[a-z0-9_]{3,30}$")
RESERVED_HANDLES = frozenset(
    {
        "admin",
        "api",
        "auth",
        "coach",
        "dashboard",
        "explore",
        "feed",
        "lab",
        "login",
        "logout",
        "me",
        "pulse",
        "settings",
        "static",
        "strava",
        "support",
        "u",
        "user",
        "users",
    }
)


class ProfileValidationError(ValueError):
    pass


def display_name_for(athlete: Athlete) -> str:
    if athlete.display_name and athlete.display_name.strip():
        return athlete.display_name.strip()

    parts = [
        (athlete.firstname or "").strip(),
        (athlete.lastname or "").strip(),
    ]
    full = " ".join(p for p in parts if p)
    if full:
        return full

    if athlete.username:
        return athlete.username

    return f"Atleta {athlete.id}"


def initials_for(athlete: Athlete) -> str:
    name = display_name_for(athlete)
    tokens = [t for t in re.split(r"\s+", name) if t]
    if len(tokens) >= 2:
        return (tokens[0][0] + tokens[1][0]).upper()
    if tokens:
        return tokens[0][:2].upper()
    return "P"


def normalize_handle(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = raw.strip().lower()
    if value == "":
        return None
    return value


def validate_handle(handle: str | None) -> str | None:
    normalized = normalize_handle(handle)
    if normalized is None:
        return None

    if not HANDLE_RE.match(normalized):
        raise ProfileValidationError(
            "Handle inválido. Usa 3–30 caracteres: a-z, 0-9 e underscore."
        )

    if normalized in RESERVED_HANDLES:
        raise ProfileValidationError("Este handle está reservado.")

    return normalized


def assert_handle_available(db: Session, handle: str, athlete_id: int) -> None:
    existing = (
        db.query(Athlete)
        .filter(Athlete.handle == handle, Athlete.id != athlete_id)
        .one_or_none()
    )
    if existing is not None:
        raise ProfileValidationError("Este handle já está em uso.")


def avatar_url_for(athlete: Athlete) -> str | None:
    if athlete.avatar_data and athlete.avatar_content_type:
        # Cache-bust with updated_at so browsers refresh after upload.
        stamp = ""
        if athlete.updated_at is not None:
            ts = athlete.updated_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            stamp = f"?v={int(ts.timestamp())}"
        return f"/api/me/avatar{stamp}"

    if athlete.profile_medium:
        return athlete.profile_medium

    if athlete.profile:
        return athlete.profile

    return None


def serialize_profile(athlete: Athlete, *, include_stats: dict | None = None) -> dict:
    return {
        "athlete_id": athlete.id,
        "display_name": display_name_for(athlete),
        "display_name_custom": athlete.display_name,
        "handle": athlete.handle,
        "bio": athlete.bio,
        "initials": initials_for(athlete),
        "avatar_url": avatar_url_for(athlete),
        "has_custom_avatar": bool(athlete.avatar_data),
        "strava": {
            "username": athlete.username,
            "firstname": athlete.firstname,
            "lastname": athlete.lastname,
            "profile_url": athlete.profile,
            "profile_medium_url": athlete.profile_medium,
            "connected": True,
        },
        "location": {
            "city": athlete.city,
            "state": athlete.state,
            "country": athlete.country,
        },
        "is_profile_public": bool(athlete.is_profile_public),
        "member_since": (
            athlete.created_at.isoformat() if athlete.created_at else None
        ),
        "last_login_at": (
            athlete.last_login_at.isoformat() if athlete.last_login_at else None
        ),
        "stats": include_stats,
    }


def apply_profile_patch(db: Session, athlete: Athlete, payload: dict) -> Athlete:
    if "display_name" in payload:
        raw = payload.get("display_name")
        if raw is None or (isinstance(raw, str) and raw.strip() == ""):
            athlete.display_name = None
        elif not isinstance(raw, str):
            raise ProfileValidationError("display_name inválido.")
        else:
            name = raw.strip()
            if len(name) > 120:
                raise ProfileValidationError(
                    "display_name demasiado longo (máx. 120)."
                )
            athlete.display_name = name

    if "handle" in payload:
        handle = validate_handle(payload.get("handle"))
        if handle is not None:
            assert_handle_available(db, handle, athlete.id)
        athlete.handle = handle

    if "bio" in payload:
        raw = payload.get("bio")
        if raw is None or (isinstance(raw, str) and raw.strip() == ""):
            athlete.bio = None
        elif not isinstance(raw, str):
            raise ProfileValidationError("bio inválida.")
        else:
            bio = raw.strip()
            if len(bio) > 500:
                raise ProfileValidationError("bio demasiado longa (máx. 500).")
            athlete.bio = bio

    athlete.updated_at = utcnow()
    db.commit()
    db.refresh(athlete)
    return athlete
