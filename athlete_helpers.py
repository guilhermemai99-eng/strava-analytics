from datetime import datetime, timezone

from athlete import Athlete, utcnow


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
    existing.profile = athlete_payload.get("profile")
    existing.profile_medium = athlete_payload.get("profile_medium")
    existing.updated_at = now
    existing.last_login_at = now

    db.flush()
    return existing
