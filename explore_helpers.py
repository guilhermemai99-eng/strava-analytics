"""Explore discovery: search and suggest public runners."""

from __future__ import annotations

from datetime import datetime, timezone

from athlete import Athlete
from feed_helpers import location_display_for
from models import Activity
from profile_helpers import display_name_for, initials_for, public_avatar_url_for
from sqlalchemy import func, or_
from sqlalchemy.orm import Session


def _iso_or_none(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def serialize_explore_athlete(
    athlete: Athlete,
    *,
    last_activity_at: str | None = None,
    activity_count: int | None = None,
    total_distance_km: float | None = None,
) -> dict:
    handle = athlete.handle or athlete.username
    return {
        "athlete_id": athlete.id,
        "name": display_name_for(athlete),
        "username": handle,
        "handle": athlete.handle,
        "initials": initials_for(athlete),
        "avatar_url": public_avatar_url_for(athlete),
        "bio": athlete.bio,
        "location": {
            "display_name": location_display_for(athlete),
            "city": athlete.city,
            "country": athlete.country,
        },
        "last_activity_at": _iso_or_none(last_activity_at),
        "stats": {
            "activity_count": activity_count,
            "total_distance_km": total_distance_km,
        },
        "is_profile_public": bool(athlete.is_profile_public),
    }


def _activity_aggregates(db: Session, athlete_ids: list[int]) -> dict[int, dict]:
    if not athlete_ids:
        return {}
    rows = (
        db.query(
            Activity.athlete_id,
            func.count(Activity.id),
            func.coalesce(func.sum(Activity.distance_m), 0.0),
            func.max(Activity.start_date_local),
        )
        .filter(Activity.athlete_id.in_(athlete_ids))
        .group_by(Activity.athlete_id)
        .all()
    )
    out: dict[int, dict] = {}
    for athlete_id, count, distance_m, last_local in rows:
        out[int(athlete_id)] = {
            "activity_count": int(count or 0),
            "total_distance_km": round(float(distance_m or 0) / 1000.0, 1),
            "last_activity_at": last_local,
        }
    return out


def _with_stats(db: Session, athletes: list[Athlete]) -> list[dict]:
    aggregates = _activity_aggregates(db, [a.id for a in athletes])
    items = []
    for athlete in athletes:
        stats = aggregates.get(athlete.id, {})
        items.append(
            serialize_explore_athlete(
                athlete,
                last_activity_at=stats.get("last_activity_at"),
                activity_count=stats.get("activity_count"),
                total_distance_km=stats.get("total_distance_km"),
            )
        )
    return items


def search_public_athletes(
    db: Session,
    *,
    query: str,
    viewer_id: int,
    limit: int = 20,
) -> list[dict]:
    q = (query or "").strip().lstrip("@").lower()
    safe_limit = max(1, min(int(limit), 40))
    if len(q) < 2:
        return []

    pattern = f"%{q}%"
    athletes = (
        db.query(Athlete)
        .filter(
            Athlete.is_profile_public.is_(True),
            Athlete.id != viewer_id,
            or_(
                func.lower(func.coalesce(Athlete.handle, "")).like(pattern),
                func.lower(func.coalesce(Athlete.display_name, "")).like(pattern),
                func.lower(func.coalesce(Athlete.username, "")).like(pattern),
                func.lower(func.coalesce(Athlete.firstname, "")).like(pattern),
                func.lower(func.coalesce(Athlete.lastname, "")).like(pattern),
                func.lower(func.coalesce(Athlete.city, "")).like(pattern),
            ),
        )
        .order_by(Athlete.last_login_at.desc().nullslast(), Athlete.id.desc())
        .limit(safe_limit)
        .all()
    )
    return _with_stats(db, athletes)


def suggest_nearby(
    db: Session,
    *,
    viewer: Athlete,
    limit: int = 12,
) -> list[dict]:
    safe_limit = max(1, min(int(limit), 30))
    filters = [
        Athlete.is_profile_public.is_(True),
        Athlete.id != viewer.id,
    ]
    city = (viewer.city or "").strip()
    country = (viewer.country or "").strip()
    if city:
        athletes = (
            db.query(Athlete)
            .filter(*filters, func.lower(Athlete.city) == city.lower())
            .order_by(Athlete.last_login_at.desc().nullslast(), Athlete.id.desc())
            .limit(safe_limit)
            .all()
        )
        if athletes:
            return _with_stats(db, athletes)
    if country:
        athletes = (
            db.query(Athlete)
            .filter(*filters, func.lower(Athlete.country) == country.lower())
            .order_by(Athlete.last_login_at.desc().nullslast(), Athlete.id.desc())
            .limit(safe_limit)
            .all()
        )
        return _with_stats(db, athletes)
    return []


def suggest_recently_active(
    db: Session,
    *,
    viewer_id: int,
    limit: int = 12,
) -> list[dict]:
    safe_limit = max(1, min(int(limit), 30))
    latest = (
        db.query(
            Activity.athlete_id.label("athlete_id"),
            func.max(Activity.start_date_local).label("last_at"),
        )
        .group_by(Activity.athlete_id)
        .subquery()
    )
    rows = (
        db.query(Athlete, latest.c.last_at)
        .join(latest, latest.c.athlete_id == Athlete.id)
        .filter(
            Athlete.is_profile_public.is_(True),
            Athlete.id != viewer_id,
        )
        .order_by(latest.c.last_at.desc().nullslast(), Athlete.id.desc())
        .limit(safe_limit)
        .all()
    )
    athletes = [row[0] for row in rows]
    return _with_stats(db, athletes)


def suggest_new_faces(
    db: Session,
    *,
    viewer_id: int,
    limit: int = 12,
) -> list[dict]:
    safe_limit = max(1, min(int(limit), 30))
    athletes = (
        db.query(Athlete)
        .filter(
            Athlete.is_profile_public.is_(True),
            Athlete.id != viewer_id,
        )
        .order_by(Athlete.created_at.desc().nullslast(), Athlete.id.desc())
        .limit(safe_limit)
        .all()
    )
    return _with_stats(db, athletes)


def get_public_athlete(db: Session, athlete_id: int) -> Athlete | None:
    return (
        db.query(Athlete)
        .filter(
            Athlete.id == athlete_id,
            Athlete.is_profile_public.is_(True),
        )
        .one_or_none()
    )


def public_athlete_payload(db: Session, athlete: Athlete) -> dict:
    return _with_stats(db, [athlete])[0]
