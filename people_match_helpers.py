"""People matching for social discovery (pace, distance, location, frequency).

Privacy: never expose exact coordinates. Only city/country / coarse area labels.
"""

from __future__ import annotations

from athlete import Athlete
from follow_helpers import is_following, has_outgoing_request
from pace_compatibility import estimate_running_profile, format_pace_range
from profile_helpers import display_name_for, initials_for, public_avatar_url_for
from sqlalchemy import func
from sqlalchemy.orm import Session


def _approx_location_label(athlete: Athlete, *, viewer: Athlete | None = None) -> str | None:
    """Coarse location only — never precise coords."""
    city = (athlete.city or "").strip()
    country = (athlete.country or "").strip()

    if city and viewer and (viewer.city or "").strip().lower() == city.lower():
        return f"Near {city}"
    if city:
        return f"Near {city}"
    if country and viewer and (viewer.country or "").strip().lower() == country.lower():
        return f"Near {country}"
    if country:
        return country
    return None


def _location_score(viewer: Athlete, other: Athlete) -> tuple[float, str | None]:
    """0–40 points for shared city/country."""
    v_city = (viewer.city or "").strip().lower()
    o_city = (other.city or "").strip().lower()
    v_country = (viewer.country or "").strip().lower()
    o_country = (other.country or "").strip().lower()

    if v_city and o_city and v_city == o_city:
        return 40.0, _approx_location_label(other, viewer=viewer)
    if v_country and o_country and v_country == o_country:
        return 18.0, _approx_location_label(other, viewer=viewer)
    if o_city or o_country:
        return 5.0, _approx_location_label(other, viewer=viewer)
    return 0.0, None


def _pace_score(viewer_pace: float | None, other_pace: float | None) -> tuple[float, str]:
    """0–40 points for pace proximity."""
    if not viewer_pace or not other_pace:
        return 12.0, "Pace unknown"
    diff = abs(viewer_pace - other_pace) / viewer_pace
    if diff <= 0.05:
        return 40.0, "Similar pace"
    if diff <= 0.10:
        return 32.0, "Close pace"
    if diff <= 0.18:
        return 20.0, "Compatible pace"
    if diff <= 0.28:
        return 10.0, "Different pace"
    return 2.0, "Very different pace"


def _distance_score(
    viewer_min: float | None,
    viewer_max: float | None,
    other_min: float | None,
    other_max: float | None,
) -> float:
    """0–12 points for overlapping typical distance bands."""
    if not viewer_min or not viewer_max or not other_min or not other_max:
        return 4.0
    lo = max(viewer_min, other_min)
    hi = min(viewer_max, other_max)
    if hi >= lo:
        return 12.0
    gap = lo - hi
    if gap <= 3:
        return 8.0
    if gap <= 8:
        return 4.0
    return 1.0


def _frequency_score(viewer_weekly: float | None, other_weekly: float | None) -> float:
    """0–8 points for similar weekly volume."""
    if viewer_weekly is None or other_weekly is None:
        return 2.0
    if viewer_weekly <= 0 and other_weekly <= 0:
        return 2.0
    base = max(viewer_weekly, 1.0)
    diff = abs(viewer_weekly - other_weekly) / base
    if diff <= 0.25:
        return 8.0
    if diff <= 0.5:
        return 5.0
    if diff <= 1.0:
        return 3.0
    return 1.0


def _mid_band(a: float | None, b: float | None, factor: float) -> float | None:
    if a and b:
        return ((a + b) / 2.0) * factor
    if a:
        return a * factor
    if b:
        return b * factor
    return None


def compute_people_match(
    viewer_profile: dict,
    other_profile: dict,
    *,
    viewer: Athlete,
    other: Athlete,
) -> dict:
    """Return match score 0–100 and labels. Never blocks interaction."""
    pace_pts, pace_note = _pace_score(
        viewer_profile.get("easy_pace_sec_per_km"),
        other_profile.get("easy_pace_sec_per_km"),
    )
    loc_pts, loc_label = _location_score(viewer, other)
    dist_pts = _distance_score(
        viewer_profile.get("typical_distance_km_min"),
        viewer_profile.get("typical_distance_km_max"),
        other_profile.get("typical_distance_km_min"),
        other_profile.get("typical_distance_km_max"),
    )
    freq_pts = _frequency_score(
        viewer_profile.get("weekly_distance_km"),
        other_profile.get("weekly_distance_km"),
    )

    total = round(min(100.0, pace_pts + loc_pts + dist_pts + freq_pts))
    if total >= 75:
        level, emoji, label = "great_match", "🟢", "Great match"
    elif total >= 50:
        level, emoji, label = "good_match", "🟡", "Good match"
    elif total >= 30:
        level, emoji, label = "possible_match", "🟠", "Possible match"
    else:
        level, emoji, label = "low_match", "⚪", "Different style"

    suggested_pace = format_pace_range(
        _mid_band(
            viewer_profile.get("easy_pace_sec_per_km"),
            other_profile.get("easy_pace_sec_per_km"),
            0.97,
        ),
        _mid_band(
            viewer_profile.get("easy_pace_sec_per_km"),
            other_profile.get("easy_pace_sec_per_km"),
            1.05,
        ),
    )
    v_min = viewer_profile.get("typical_distance_km_min")
    o_min = other_profile.get("typical_distance_km_min")
    v_max = viewer_profile.get("typical_distance_km_max")
    o_max = other_profile.get("typical_distance_km_max")
    suggested_distance = None
    if v_min and o_min and v_max and o_max:
        lo = round(max(v_min, o_min), 1)
        hi = round(min(v_max, o_max), 1)
        if hi >= lo:
            suggested_distance = f"{lo:g}–{hi:g} km"
        else:
            mid = round((v_min + o_min) / 2, 1)
            suggested_distance = f"{mid:g}–{round(mid + 5, 1):g} km"

    return {
        "score": total,
        "level": level,
        "emoji": emoji,
        "label": label,
        "pace_note": pace_note,
        "location_label": loc_label,
        "suggested_pace": suggested_pace,
        "suggested_distance": suggested_distance,
    }


def serialize_match_card(
    db: Session,
    *,
    viewer: Athlete,
    other: Athlete,
    viewer_profile: dict,
    other_profile: dict | None = None,
) -> dict:
    other_prof = other_profile or estimate_running_profile(db, other.id)
    match = compute_people_match(
        viewer_profile, other_prof, viewer=viewer, other=other
    )
    following = is_following(
        db, follower_id=viewer.id, following_id=other.id
    )
    followed_by = is_following(
        db, follower_id=other.id, following_id=viewer.id
    )
    dist_label = None
    if other_prof.get("typical_distance_km_min") and other_prof.get(
        "typical_distance_km_max"
    ):
        dist_label = (
            f"{other_prof['typical_distance_km_min']:g}"
            f"–{other_prof['typical_distance_km_max']:g} km"
        )

    return {
        "athlete_id": other.id,
        "name": display_name_for(other),
        "handle": other.handle,
        "avatar_url": public_avatar_url_for(other),
        "initials": initials_for(other),
        "bio": (other.bio or "")[:160] or None,
        "easy_pace_range": other_prof.get("easy_pace_range")
        or other_prof.get("easy_pace_label"),
        "typical_distance": dist_label,
        "weekly_distance_km": other_prof.get("weekly_distance_km"),
        "location_label": match.get("location_label"),
        "match": match,
        "is_following": following,
        "is_follow_requested": has_outgoing_request(
            db, requester_id=viewer.id, target_id=other.id
        ),
        "is_mutual": bool(following and followed_by),
        "is_self": False,
    }


def list_people_matches(
    db: Session,
    *,
    viewer_id: int,
    limit: int = 24,
) -> list[dict]:
    """Rank public athletes by match score. Prefer same city, then country."""
    viewer = db.query(Athlete).filter(Athlete.id == viewer_id).one_or_none()
    if not viewer:
        return []

    safe_limit = max(1, min(int(limit), 40))
    viewer_profile = estimate_running_profile(db, viewer_id)

    filters = [
        Athlete.is_profile_public.is_(True),
        Athlete.id != viewer_id,
    ]
    city = (viewer.city or "").strip()
    country = (viewer.country or "").strip()

    candidates: list[Athlete] = []
    seen: set[int] = set()

    def _add(rows: list[Athlete]) -> None:
        for a in rows:
            if a.id not in seen:
                seen.add(a.id)
                candidates.append(a)

    if city:
        _add(
            db.query(Athlete)
            .filter(*filters, func.lower(Athlete.city) == city.lower())
            .order_by(Athlete.last_login_at.desc().nullslast())
            .limit(safe_limit * 2)
            .all()
        )
    if country and len(candidates) < safe_limit * 2:
        _add(
            db.query(Athlete)
            .filter(*filters, func.lower(Athlete.country) == country.lower())
            .order_by(Athlete.last_login_at.desc().nullslast())
            .limit(safe_limit * 2)
            .all()
        )
    if len(candidates) < safe_limit:
        _add(
            db.query(Athlete)
            .filter(*filters)
            .order_by(Athlete.last_login_at.desc().nullslast())
            .limit(safe_limit * 3)
            .all()
        )

    cards = [
        serialize_match_card(
            db,
            viewer=viewer,
            other=other,
            viewer_profile=viewer_profile,
        )
        for other in candidates
    ]
    cards.sort(key=lambda c: c["match"]["score"], reverse=True)
    return cards[:safe_limit]


def get_compatibility_with(
    db: Session,
    *,
    viewer_id: int,
    target_id: int,
) -> dict | None:
    if viewer_id == target_id:
        return None
    viewer = db.query(Athlete).filter(Athlete.id == viewer_id).one_or_none()
    other = db.query(Athlete).filter(Athlete.id == target_id).one_or_none()
    if not viewer or not other:
        return None
    if not other.is_profile_public:
        if not is_following(
            db, follower_id=viewer_id, following_id=target_id
        ) and not is_following(
            db, follower_id=target_id, following_id=viewer_id
        ):
            return None

    viewer_profile = estimate_running_profile(db, viewer_id)
    return serialize_match_card(
        db,
        viewer=viewer,
        other=other,
        viewer_profile=viewer_profile,
    )


def run_together_suggestion(
    db: Session,
    *,
    viewer_id: int,
    target_id: int,
) -> dict | None:
    """Prefill payload for Create Run with a matched athlete."""
    card = get_compatibility_with(db, viewer_id=viewer_id, target_id=target_id)
    if not card:
        return None
    match = card["match"]
    first = (card.get("name") or "a friend").split()[0]
    return {
        "peer": {
            "athlete_id": card["athlete_id"],
            "name": card["name"],
            "handle": card["handle"],
            "avatar_url": card["avatar_url"],
            "initials": card["initials"],
        },
        "match": match,
        "suggested_title": f"Run with {first}",
        "suggested_pace_min": _pace_from_range(match.get("suggested_pace"), 0),
        "suggested_pace_max": _pace_from_range(match.get("suggested_pace"), 1),
        "suggested_distance_km": _distance_mid(match.get("suggested_distance")),
        "suggested_location": card.get("location_label"),
    }


def _pace_from_range(label: str | None, index: int) -> str | None:
    if not label:
        return None
    cleaned = label.replace("/km", "").strip()
    parts = [p.strip() for p in cleaned.replace("–", "-").split("-") if p.strip()]
    if len(parts) == 1:
        return parts[0]
    if len(parts) >= 2:
        return parts[index]
    return None


def _distance_mid(label: str | None) -> float | None:
    if not label:
        return None
    cleaned = label.replace("km", "").strip()
    parts = [p.strip() for p in cleaned.replace("–", "-").split("-") if p.strip()]
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return None
    if not nums:
        return None
    if len(nums) == 1:
        return nums[0]
    return round((nums[0] + nums[1]) / 2, 1)
