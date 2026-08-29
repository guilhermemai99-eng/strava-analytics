"""Serialize Pulse feed items from activities + author profile."""

from __future__ import annotations

from athlete import Athlete
from feed_titles import pace_min_per_km, pulse_title_for_activity
from models import Activity
from media_helpers import proxied_media_url
from profile_helpers import display_name_for, initials_for, public_avatar_url_for


def format_duration(seconds: int | None) -> str | None:
    if seconds is None or seconds < 0:
        return None
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_pace(distance_m: float | None, moving_time_s: int | None) -> str | None:
    pace = pace_min_per_km(distance_m, moving_time_s)
    if pace is None or pace <= 0 or pace > 60:
        return None
    total_sec = int(round(pace * 60))
    return f"{total_sec // 60}:{total_sec % 60:02d}"


def activity_type_label(activity: Activity) -> str:
    name = (activity.name or "").lower()
    sport = (activity.sport_type or "Run").strip() or "Run"

    if "race" in name:
        return "Race"
    if "tempo" in name:
        return "Tempo"
    if "interval" in name or "workout" in name or "repeats" in name:
        return "Workout"
    if "long" in name:
        return "Long Run"
    if "easy" in name or "recovery" in name:
        return "Easy Run"
    if sport in {"TrailRun", "VirtualRun", "Run"}:
        return "Run"
    return sport


def location_display_for(athlete: Athlete) -> str | None:
    """Human location only — never GPS. Prefer profile city/country."""

    city = (athlete.city or "").strip()
    country = (athlete.country or "").strip()
    if city and country:
        return f"{city}, {country}"
    if city:
        return city
    if country:
        return country
    return None


def relative_time_label(iso_value: str | None) -> str | None:
    if not iso_value:
        return None
    # Keep ISO for client formatting; also provide a short server hint.
    return iso_value


def serialize_feed_author(athlete: Athlete) -> dict:
    handle = athlete.handle or athlete.username
    return {
        "athlete_id": athlete.id,
        "name": display_name_for(athlete),
        "username": handle,
        "handle": athlete.handle,
        "avatar_url": public_avatar_url_for(athlete),
        "initials": initials_for(athlete),
    }


def serialize_feed_item(activity: Activity, athlete: Athlete) -> dict:
    distance_m = activity.distance_m
    moving_time_s = activity.moving_time_s
    title = pulse_title_for_activity(
        activity.id,
        distance_m=distance_m,
        moving_time_s=moving_time_s,
        sport_type=activity.sport_type,
        name=activity.name,
    )
    location = location_display_for(athlete)
    photo = proxied_media_url((activity.photo_url or "").strip() or None)
    polyline = (activity.summary_polyline or "").strip() or None

    return {
        "id": f"activity:{activity.id}",
        "kind": "activity",
        "created_at": activity.start_date_local or activity.start_date,
        "author": serialize_feed_author(athlete),
        "activity": {
            "id": activity.id,
            "strava_id": activity.strava_id,
            "title": title,
            "original_name": activity.name,
            "type": activity_type_label(activity),
            "sport_type": activity.sport_type or "Run",
            "distance_m": distance_m,
            "distance_km": (
                round(float(distance_m) / 1000.0, 2) if distance_m is not None else None
            ),
            "moving_time_s": moving_time_s,
            "duration_label": format_duration(moving_time_s),
            "pace_label": format_pace(distance_m, moving_time_s),
            "elevation_gain_m": activity.elevation_gain_m,
            "start_date": activity.start_date,
            "start_date_local": activity.start_date_local,
        },
        "media": {
            "primary_image_url": photo,
            "summary_polyline": polyline,
            "has_photo": bool(photo),
            "has_map": bool(polyline),
            "photo_count": activity.photo_count or (1 if photo else 0),
        },
        "location": {
            "display_name": location,
        },
    }
