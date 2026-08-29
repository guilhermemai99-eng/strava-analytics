"""Public @handle profile payloads (identity + follows + activities)."""

from __future__ import annotations

from athlete import Athlete
from feed_helpers import format_duration, format_pace, location_display_for
from follow_helpers import (
    follower_count,
    following_count,
    get_athlete_by_handle,
    relationship_payload,
)
from media_helpers import proxied_media_url
from models import Activity
from profile_helpers import display_name_for, ensure_handle, initials_for, public_avatar_url_for
from sqlalchemy import func
from sqlalchemy.orm import Session


def can_view_profile(viewer: Athlete, target: Athlete) -> bool:
    if viewer.id == target.id:
        return True
    return bool(target.is_profile_public)


def resolve_profile_athlete(db: Session, handle: str) -> Athlete | None:
    athlete = get_athlete_by_handle(db, handle)
    return athlete


def activity_stats_for(db: Session, athlete_id: int) -> dict:
    row = (
        db.query(
            func.count(Activity.id),
            func.coalesce(func.sum(Activity.distance_m), 0.0),
            func.coalesce(func.sum(Activity.moving_time_s), 0),
        )
        .filter(Activity.athlete_id == athlete_id)
        .one()
    )
    count = int(row[0] or 0)
    distance_m = float(row[1] or 0)
    moving_s = int(row[2] or 0)
    return {
        "activity_count": count,
        "total_distance_km": round(distance_m / 1000.0, 1),
        "total_moving_time_s": moving_s,
    }


def serialize_profile_activity(activity: Activity) -> dict:
    distance_m = activity.distance_m
    moving_time_s = activity.moving_time_s
    return {
        "id": activity.id,
        "name": activity.name,
        "sport_type": activity.sport_type or "Run",
        "distance_m": distance_m,
        "distance_km": (
            round(float(distance_m) / 1000.0, 2) if distance_m is not None else None
        ),
        "moving_time_s": moving_time_s,
        "pace_label": format_pace(distance_m, moving_time_s),
        "duration_label": format_duration(moving_time_s),
        "elevation_gain_m": activity.elevation_gain_m,
        "start_date_local": activity.start_date_local,
        "start_date": activity.start_date,
        "photo_url": proxied_media_url((activity.photo_url or "").strip() or None),
        # Deliberately omit polyline / GPS.
    }


def list_profile_activities(
    db: Session,
    athlete_id: int,
    *,
    limit: int = 24,
) -> list[dict]:
    safe_limit = max(1, min(int(limit), 50))
    rows = (
        db.query(Activity)
        .filter(Activity.athlete_id == athlete_id)
        .order_by(Activity.start_date_local.desc())
        .limit(safe_limit)
        .all()
    )
    return [serialize_profile_activity(a) for a in rows]


def serialize_public_profile(
    db: Session,
    *,
    target: Athlete,
    viewer: Athlete,
    activity_limit: int = 24,
) -> dict:
    is_self = viewer.id == target.id
    # Own profile always gets a handle so /@ urls work.
    if is_self and not target.handle:
        target = ensure_handle(db, target)

    stats = activity_stats_for(db, target.id)
    activities = list_profile_activities(db, target.id, limit=activity_limit)
    rel = relationship_payload(db, viewer_id=viewer.id, target_id=target.id)
    followers = follower_count(db, target.id)
    following = following_count(db, target.id)

    return {
        "athlete_id": target.id,
        "id": target.id,
        "display_name": display_name_for(target),
        "handle": target.handle,
        "username": target.handle or target.username,
        "bio": target.bio,
        "initials": initials_for(target),
        "avatar_url": public_avatar_url_for(target),
        "location": {
            "display_name": location_display_for(target),
            "city": target.city,
            "country": target.country,
        },
        "is_profile_public": bool(target.is_profile_public),
        "is_self": rel["is_self"],
        "is_following": rel["is_following"],
        "is_followed_by": rel["is_followed_by"],
        "is_mutual": rel["is_mutual"],
        "relationship": rel,
        "follower_count": followers,
        "following_count": following,
        "followers_count": followers,
        "stats": stats,
        "activities": activities,
        "activity_count": stats["activity_count"],
        "posts_count": stats["activity_count"],
    }


def ensure_own_handle_on_me(db: Session, athlete: Athlete) -> Athlete:
    return ensure_handle(db, athlete) if not athlete.handle else athlete
