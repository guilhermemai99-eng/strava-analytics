"""Running profile estimation and run pace compatibility (MVP, no ML)."""

from __future__ import annotations

from statistics import median

from sqlalchemy.orm import Session

from analytics import RUNNING_SPORT_TYPES
from feed_helpers import format_pace
from feed_titles import pace_min_per_km
from models import Activity


def parse_pace_to_seconds(value: str | float | int | None) -> float | None:
    """Parse pace to seconds per km. Accepts 'M:SS' string or numeric seconds."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        sec = float(value)
        return sec if sec > 0 else None
    raw = str(value).strip()
    if not raw:
        return None
    if ":" in raw:
        parts = raw.split(":")
        if len(parts) != 2:
            return None
        try:
            minutes = int(parts[0])
            seconds = int(parts[1])
        except ValueError:
            return None
        total = minutes * 60 + seconds
        return float(total) if total > 0 else None
    try:
        sec = float(raw)
        return sec if sec > 0 else None
    except ValueError:
        return None


def format_pace_seconds(sec: float | None) -> str | None:
    if sec is None or sec <= 0:
        return None
    minutes = int(sec // 60)
    seconds = int(round(sec % 60))
    if seconds >= 60:
        minutes += 1
        seconds = 0
    return f"{minutes}:{seconds:02d}"


def format_pace_range(pace_min_sec: float | None, pace_max_sec: float | None) -> str | None:
    lo = format_pace_seconds(pace_min_sec)
    hi = format_pace_seconds(pace_max_sec)
    if lo and hi:
        return f"{lo}–{hi}/km"
    if lo:
        return f"{lo}/km"
    if hi:
        return f"{hi}/km"
    return None


def _activity_pace_sec(activity: Activity) -> float | None:
    pace_min = pace_min_per_km(activity.distance_m, activity.moving_time_s)
    if pace_min is None or pace_min <= 0:
        return None
    return pace_min * 60.0


def estimate_running_profile(db: Session, athlete_id: int) -> dict:
    """Simple running profile from recent activities."""
    rows = (
        db.query(Activity)
        .filter(
            Activity.athlete_id == athlete_id,
            Activity.sport_type.in_(RUNNING_SPORT_TYPES),
            Activity.distance_m.isnot(None),
            Activity.moving_time_s.isnot(None),
        )
        .order_by(Activity.start_date.desc().nullslast())
        .limit(40)
        .all()
    )

    paces: list[float] = []
    distances_km: list[float] = []
    for act in rows:
        pace_sec = _activity_pace_sec(act)
        dist_km = (act.distance_m or 0) / 1000.0
        if pace_sec and 180 <= pace_sec <= 720 and dist_km >= 1:
            paces.append(pace_sec)
            distances_km.append(dist_km)

    easy_pace_sec = median(paces) if paces else None
    typical_km = median(distances_km) if distances_km else None

    easy_min = easy_pace_sec * 0.95 if easy_pace_sec else None
    easy_max = easy_pace_sec * 1.08 if easy_pace_sec else None
    dist_min = max(3.0, typical_km * 0.6) if typical_km else None
    dist_max = typical_km * 1.4 if typical_km else None

    weekly_km = round(sum(distances_km[:7]), 1) if distances_km else None

    return {
        "easy_pace_sec_per_km": round(easy_pace_sec, 1) if easy_pace_sec else None,
        "easy_pace_label": format_pace_seconds(easy_pace_sec),
        "easy_pace_range": format_pace_range(easy_min, easy_max),
        "typical_distance_km_min": round(dist_min, 1) if dist_min else None,
        "typical_distance_km_max": round(dist_max, 1) if dist_max else None,
        "weekly_distance_km": weekly_km,
        "sample_activities": len(paces),
    }


def run_pace_midpoint(pace_min_sec: float | None, pace_max_sec: float | None) -> float | None:
    if pace_min_sec and pace_max_sec:
        return (pace_min_sec + pace_max_sec) / 2.0
    return pace_min_sec or pace_max_sec


def compatibility_for_run(
    profile: dict,
    *,
    pace_min_sec: float | None,
    pace_max_sec: float | None,
) -> dict:
    """Compare athlete easy pace to run pace range. Never blocks joining."""
    user_pace = profile.get("easy_pace_sec_per_km")
    run_mid = run_pace_midpoint(pace_min_sec, pace_max_sec)

    if not user_pace or not run_mid:
        return {
            "level": "unknown",
            "label": "Pace unknown",
            "message": "Sync Strava to see how this run matches your usual pace.",
            "emoji": "⚪",
        }

    diff_ratio = abs(run_mid - user_pace) / user_pace

    if diff_ratio <= 0.06:
        return {
            "level": "great_match",
            "label": "Great match",
            "message": "This run matches your usual pace.",
            "emoji": "🟢",
        }
    if diff_ratio <= 0.14:
        return {
            "level": "possible_match",
            "label": "Possible match",
            "message": "Slightly different from your usual easy pace — still doable.",
            "emoji": "🟡",
        }
    if run_mid < user_pace:
        return {
            "level": "challenging",
            "label": "Challenging",
            "message": "This pace may be faster than your usual easy runs.",
            "emoji": "🔴",
        }
    return {
        "level": "challenging",
        "label": "Challenging",
        "message": "This pace may feel slower or longer than your typical runs.",
        "emoji": "🔴",
    }


def participant_pace_label(db: Session, athlete_id: int) -> str | None:
    profile = estimate_running_profile(db, athlete_id)
    return profile.get("easy_pace_range") or profile.get("easy_pace_label")
