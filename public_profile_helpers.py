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
from models import Activity
from profile_helpers import display_name_for, ensure_handle, initials_for, public_avatar_url_for
from media_helpers import proxied_media_url
from sqlalchemy import func
from sqlalchemy.orm import Session


def can_view_profile(viewer: Athlete, target: Athlete, db: Session | None = None) -> bool:
    if viewer.id == target.id:
        return True
    if bool(target.is_profile_public):
        return True
    if db is None:
        return False
    from follow_helpers import is_following

    return is_following(db, follower_id=viewer.id, following_id=target.id)


def resolve_profile_athlete(db: Session, handle: str) -> Athlete | None:
    athlete = get_athlete_by_handle(db, handle)
    return athlete


def activity_stats_for(
    db: Session,
    athlete_id: int,
    *,
    viewer_id: int | None = None,
) -> dict:
    """Aggregate runs the viewer is allowed to see (never deleted rows)."""
    from follow_helpers import is_following
    from sqlalchemy import or_

    filters = [
        Activity.athlete_id == athlete_id,
        Activity.deleted_at.is_(None),
    ]
    if viewer_id is None:
        # Public aggregates (Explore cards): public runs only.
        filters.append(
            or_(Activity.visibility == "public", Activity.visibility.is_(None))
        )
    elif viewer_id != athlete_id:
        if is_following(db, follower_id=viewer_id, following_id=athlete_id):
            filters.append(
                or_(
                    Activity.visibility.in_(("public", "followers")),
                    Activity.visibility.is_(None),
                )
            )
        else:
            filters.append(
                or_(Activity.visibility == "public", Activity.visibility.is_(None))
            )

    row = (
        db.query(
            func.count(Activity.id),
            func.coalesce(func.sum(Activity.distance_m), 0.0),
            func.coalesce(func.sum(Activity.moving_time_s), 0),
        )
        .filter(*filters)
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

    stats = activity_stats_for(db, target.id, viewer_id=viewer.id)
    from activity_social_helpers import list_visible_profile_activities

    activities = [
        serialize_profile_activity(a)
        for a in list_visible_profile_activities(
            db, target_id=target.id, viewer_id=viewer.id, limit=activity_limit
        )
    ]
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
        "is_private_locked": False,
        "is_self": rel["is_self"],
        "is_following": rel["is_following"],
        "is_followed_by": rel["is_followed_by"],
        "is_mutual": rel["is_mutual"],
        "is_follow_requested": rel["is_follow_requested"],
        "has_incoming_follow_request": rel["has_incoming_follow_request"],
        "follow_status": rel["follow_status"],
        "relationship": rel,
        "follower_count": followers,
        "following_count": following,
        "followers_count": followers,
        "stats": stats,
        "activities": activities,
        "activity_count": stats["activity_count"],
        "posts_count": stats["activity_count"],
    }


def serialize_locked_profile(
    db: Session, *, target: Athlete, viewer: Athlete
) -> dict:
    """Private account visible enough to send a follow request — no posts."""
    rel = relationship_payload(db, viewer_id=viewer.id, target_id=target.id)
    followers = follower_count(db, target.id)
    following = following_count(db, target.id)
    return {
        "athlete_id": target.id,
        "id": target.id,
        "display_name": display_name_for(target),
        "handle": target.handle,
        "username": target.handle or target.username,
        "bio": None,
        "initials": initials_for(target),
        "avatar_url": public_avatar_url_for(target),
        "location": {
            "display_name": None,
            "city": None,
            "country": None,
        },
        "is_profile_public": False,
        "is_private_locked": True,
        "is_self": False,
        "is_following": False,
        "is_followed_by": rel["is_followed_by"],
        "is_mutual": False,
        "is_follow_requested": rel["is_follow_requested"],
        "has_incoming_follow_request": rel["has_incoming_follow_request"],
        "follow_status": rel["follow_status"],
        "relationship": rel,
        "follower_count": followers,
        "following_count": following,
        "followers_count": followers,
        "stats": {
            "activity_count": None,
            "total_distance_km": None,
            "total_moving_time_s": None,
        },
        "activities": [],
        "activity_count": 0,
        "posts_count": 0,
    }


def serialize_profile_for_viewer(
    db: Session, *, target: Athlete, viewer: Athlete
) -> dict:
    if can_view_profile(viewer, target, db):
        return serialize_public_profile(db, target=target, viewer=viewer)
    return serialize_locked_profile(db, target=target, viewer=viewer)


def ensure_own_handle_on_me(db: Session, athlete: Athlete) -> Athlete:
    return ensure_handle(db, athlete) if not athlete.handle else athlete
