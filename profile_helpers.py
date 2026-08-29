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

    if athlete.handle:
        return athlete.handle

    return "New athlete"


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


def _slug_candidate(raw: str) -> str:
    cleaned = re.sub(r"[^a-z0-9_]+", "_", raw.lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:30]


def suggest_handle_for(athlete: Athlete) -> str:
    """Stable candidate from name/username — no random suffixes yet."""
    sources = [
        athlete.handle,
        athlete.username,
        athlete.display_name,
        " ".join(
            p
            for p in [
                (athlete.firstname or "").strip(),
                (athlete.lastname or "").strip(),
            ]
            if p
        ),
        f"runner_{athlete.id}",
    ]
    for source in sources:
        if not source:
            continue
        slug = _slug_candidate(str(source))
        if len(slug) >= 3 and HANDLE_RE.match(slug) and slug not in RESERVED_HANDLES:
            return slug
    return f"runner_{athlete.id}"[:30]


def ensure_handle(db: Session, athlete: Athlete) -> Athlete:
    """Assign a stable unique handle once; never rotate an existing one."""
    if athlete.handle:
        return athlete

    base = suggest_handle_for(athlete)
    candidate = base
    suffix = 0
    while True:
        taken = (
            db.query(Athlete.id)
            .filter(Athlete.handle == candidate, Athlete.id != athlete.id)
            .first()
        )
        if taken is None and candidate not in RESERVED_HANDLES and HANDLE_RE.match(candidate):
            athlete.handle = candidate
            athlete.updated_at = utcnow()
            db.commit()
            db.refresh(athlete)
            return athlete
        suffix += 1
        # Keep base short enough for _NN suffix within 30 chars.
        stem = base[: max(3, 30 - len(str(suffix)) - 1)]
        candidate = f"{stem}_{suffix}"
        if suffix > 9999:
            candidate = f"u{athlete.id}"[:30]
            athlete.handle = candidate
            athlete.updated_at = utcnow()
            db.commit()
            db.refresh(athlete)
            return athlete


def upgrade_strava_profile_url(url: str | None) -> str | None:
    """Prefer the sharpest known Strava-hosted profile asset.

    Official Athlete fields:
      profile_medium → …/medium.jpg  (62×62)
      profile        → …/large.jpg   (124×124)

    There is no documented size above large.jpg; rewriting medium→large is
    the only safe CDN upgrade. Query strings are preserved.
    """
    if not url or not isinstance(url, str):
        return None
    raw = url.strip()
    if not raw:
        return None

    lower = raw.lower()
    # Strava CloudFront / legacy pics host: …/medium.jpg → …/large.jpg
    for needle in ("/medium.jpg", "/medium.jpeg", "/medium.png"):
        idx = lower.rfind(needle)
        if idx != -1:
            return raw[:idx] + "/large.jpg" + raw[idx + len(needle) :]

    return raw


def best_strava_profile_url(
    profile: str | None,
    profile_medium: str | None,
) -> str | None:
    """Pick profile over profile_medium, then upgrade medium→large when needed."""
    for candidate in (profile, profile_medium):
        upgraded = upgrade_strava_profile_url(candidate)
        if upgraded:
            return upgraded
    return None


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

    # Strava: profile (~124px / large.jpg) is sharper than profile_medium (~62px).
    return best_strava_profile_url(athlete.profile, athlete.profile_medium)


def public_avatar_url_for(athlete: Athlete) -> str | None:
    """Avatar URL safe for other runners to load (not /api/me/avatar)."""
    if athlete.avatar_data and athlete.avatar_content_type:
        stamp = ""
        if athlete.updated_at is not None:
            ts = athlete.updated_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            stamp = f"?v={int(ts.timestamp())}"
        return f"/api/athletes/{athlete.id}/avatar{stamp}"
    return best_strava_profile_url(athlete.profile, athlete.profile_medium)


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

    if "city" in payload:
        raw = payload.get("city")
        if raw is None or (isinstance(raw, str) and raw.strip() == ""):
            athlete.city = None
        elif not isinstance(raw, str):
            raise ProfileValidationError("city inválida.")
        else:
            city = raw.strip()
            if len(city) > 80:
                raise ProfileValidationError("city demasiado longa (máx. 80).")
            athlete.city = city

    if "country" in payload:
        raw = payload.get("country")
        if raw is None or (isinstance(raw, str) and raw.strip() == ""):
            athlete.country = None
        elif not isinstance(raw, str):
            raise ProfileValidationError("country inválido.")
        else:
            country = raw.strip()
            if len(country) > 80:
                raise ProfileValidationError("country demasiado longo (máx. 80).")
            athlete.country = country

    if "is_profile_public" in payload:
        value = payload.get("is_profile_public")
        if not isinstance(value, bool):
            raise ProfileValidationError("is_profile_public inválido.")
        athlete.is_profile_public = value

    athlete.updated_at = utcnow()
    db.commit()
    db.refresh(athlete)
    return athlete
