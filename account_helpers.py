"""Hard-delete the authenticated athlete and dependent rows."""

from __future__ import annotations

from sqlalchemy.orm import Session

from athlete import Athlete
from coach_message import CoachMessage
from dm_helpers import delete_dms_for_athlete
from notification_helpers import delete_notifications_for_athlete
from follow import Follow
from models import Activity
from strava_auth import StravaAuth
from user_session import UserSession, utcnow


class AccountDeleteError(ValueError):
    pass


def revoke_all_sessions(db: Session, athlete_id: int) -> int:
    """Invalidate every session for this athlete (all devices)."""
    now = utcnow()
    rows = (
        db.query(UserSession)
        .filter(
            UserSession.athlete_id == athlete_id,
            UserSession.revoked_at.is_(None),
        )
        .all()
    )
    for row in rows:
        row.revoked_at = now
    return len(rows)


def delete_athlete_account(db: Session, athlete_id: int) -> dict:
    """
    Permanently remove an athlete and owned data.

    Order matters: children without ON DELETE CASCADE first, then athlete.
    Follows cascade via FK, but we delete explicitly for clarity and counts.
    """
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).one_or_none()
    if athlete is None:
        raise AccountDeleteError("Account not found.")

    # Count active sessions before hard-delete (invalidation = delete).
    sessions_revoked = (
        db.query(UserSession)
        .filter(
            UserSession.athlete_id == athlete_id,
            UserSession.revoked_at.is_(None),
        )
        .count()
    )
    sessions_deleted = (
        db.query(UserSession)
        .filter(UserSession.athlete_id == athlete_id)
        .delete(synchronize_session=False)
    )
    strava_deleted = (
        db.query(StravaAuth)
        .filter(StravaAuth.athlete_id == athlete_id)
        .delete(synchronize_session=False)
    )
    coach_deleted = (
        db.query(CoachMessage)
        .filter(CoachMessage.athlete_id == athlete_id)
        .delete(synchronize_session=False)
    )
    activities_deleted = (
        db.query(Activity)
        .filter(Activity.athlete_id == athlete_id)
        .delete(synchronize_session=False)
    )
    follows_deleted = (
        db.query(Follow)
        .filter(
            (Follow.follower_id == athlete_id) | (Follow.following_id == athlete_id)
        )
        .delete(synchronize_session=False)
    )
    dm_stats = delete_dms_for_athlete(db, athlete_id)
    notifications_deleted = delete_notifications_for_athlete(db, athlete_id)

    db.delete(athlete)
    db.commit()

    # Best-effort local file caches (not transactional).
    try:
        from ai_cache import clear_ai_cache

        clear_ai_cache(athlete_id)
    except Exception:
        pass
    try:
        from pr_cache import clear_cache

        clear_cache(athlete_id)
    except Exception:
        pass

    return {
        "athlete_id": athlete_id,
        "deleted": True,
        "sessions_revoked": int(sessions_revoked),
        "sessions_deleted": int(sessions_deleted),
        "strava_auth_deleted": int(strava_deleted),
        "coach_messages_deleted": int(coach_deleted),
        "activities_deleted": int(activities_deleted),
        "follows_deleted": int(follows_deleted),
        "dm_messages_deleted": int(dm_stats.get("messages_deleted") or 0),
        "dm_conversations_deleted": int(dm_stats.get("conversations_deleted") or 0),
    }
