from datetime import datetime, timezone

from athlete import Athlete, utcnow
from profile_helpers import upgrade_strava_profile_url


def upsert_athlete_from_strava(db, athlete_payload: dict) -> Athlete:
    athlete_id = athlete_payload.get("id")

    if not athlete_id:
        raise ValueError("Strava athlete payload missing id")

    now = utcnow()

    existing = (
        db.query(Athlete)
        .filter(Athlete.id == athlete_id)
        .one_or_none()
    )

    if existing is None:
        existing = Athlete(
            id=athlete_id,
            created_at=now,
            updated_at=now,
        )
        db.add(existing)

    existing.username = athlete_payload.get("username")
    existing.firstname = athlete_payload.get("firstname")
    existing.lastname = athlete_payload.get("lastname")
    existing.sex = athlete_payload.get("sex")
    existing.city = athlete_payload.get("city")
    existing.state = athlete_payload.get("state")
    existing.country = athlete_payload.get("country")
    # Keep profile_medium as Strava sent it; promote profile to large.jpg when
    # possible so reads always have the sharper asset even if OAuth only
    # returned medium.
    raw_profile = athlete_payload.get("profile")
    raw_medium = athlete_payload.get("profile_medium")
    existing.profile = upgrade_strava_profile_url(raw_profile) or upgrade_strava_profile_url(
        raw_medium
    )
    existing.profile_medium = raw_medium
    existing.updated_at = now
    existing.last_login_at = now

    db.flush()
    return existing
