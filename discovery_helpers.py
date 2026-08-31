"""Tinder-style people discovery: queue, swipes, matches, preferences."""

from __future__ import annotations

import math
from typing import Literal

from athlete import Athlete
from discovery import DiscoveryMatch, DiscoveryPreference, DiscoverySwipe, utcnow
from dm import Conversation
from dm_helpers import pair_key_for
from people_match_helpers import compute_people_match, serialize_match_card
from pace_compatibility import estimate_running_profile
from profile_helpers import display_name_for, initials_for, public_avatar_url_for
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

SwipeAction = Literal["like", "pass"]
VALID_RADIUS = {5, 10, 25, 50}
LOCATION_MODES = {"near_me", "city", "anywhere"}


class DiscoveryError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(d_lng / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def _approx_distance_label(km: float | None) -> str | None:
    if km is None:
        return None
    if km < 2:
        return "In your area"
    if km < 8:
        return "About 5 km away"
    if km < 15:
        return "About 10 km away"
    if km < 35:
        return "About 25 km away"
    return "Within 50 km"


def _compat_hint(match: dict) -> str:
    notes = []
    pace = match.get("pace_note")
    if pace and pace not in ("Pace unknown", "Very different pace"):
        notes.append(f"You have {pace.lower()}")
    loc = match.get("location_label")
    if loc:
        notes.append(f"You both run near {loc.replace('Near ', '')}")
    dist = match.get("suggested_distance")
    if dist:
        notes.append(f"Similar distances ({dist})")
    if match.get("score", 0) >= 75:
        return notes[0] if notes else "Great compatibility"
    if notes:
        return notes[0]
    return match.get("label") or "Worth a look"


def get_or_create_preferences(
    db: Session, athlete_id: int
) -> DiscoveryPreference:
    row = (
        db.query(DiscoveryPreference)
        .filter(DiscoveryPreference.athlete_id == athlete_id)
        .one_or_none()
    )
    if row:
        return row
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).one()
    row = DiscoveryPreference(
        athlete_id=athlete_id,
        manual_city=athlete.city,
        manual_country=athlete.country,
        updated_at=utcnow(),
    )
    db.add(row)
    db.flush()
    return row


def serialize_preferences(
    db: Session, prefs: DiscoveryPreference, viewer: Athlete
) -> dict:
    city = prefs.manual_city or viewer.city
    country = prefs.manual_country or viewer.country
    return {
        "radius_km": prefs.radius_km,
        "location_mode": prefs.location_mode,
        "manual_city": city,
        "manual_country": country,
        "has_private_location": bool(
            prefs.private_lat is not None and prefs.private_lng is not None
        ),
        "pace_min_sec": prefs.pace_min_sec,
        "pace_max_sec": prefs.pace_max_sec,
        "distance_min_km": prefs.distance_min_km,
        "distance_max_km": prefs.distance_max_km,
        "available_days": prefs.available_days,
        "goals": prefs.goals,
        "show_goals": bool(prefs.show_goals),
        "show_availability": bool(prefs.show_availability),
        "discovery_bio": prefs.discovery_bio,
    }


def update_preferences(
    db: Session,
    *,
    athlete_id: int,
    payload: dict,
) -> DiscoveryPreference:
    prefs = get_or_create_preferences(db, athlete_id)
    if "radius_km" in payload and payload["radius_km"] is not None:
        r = int(payload["radius_km"])
        if r not in VALID_RADIUS:
            raise DiscoveryError(
                f"Radius must be one of {sorted(VALID_RADIUS)}.",
                status_code=400,
            )
        prefs.radius_km = r
    if "location_mode" in payload and payload["location_mode"]:
        mode = str(payload["location_mode"]).strip().lower()
        if mode not in LOCATION_MODES:
            raise DiscoveryError("Invalid location mode.", status_code=400)
        prefs.location_mode = mode
    for field in ("manual_city", "manual_country", "available_days", "goals"):
        if field in payload:
            val = payload[field]
            setattr(prefs, field, (val or "").strip() or None if val is not None else None)
    if "discovery_bio" in payload:
        bio = (payload.get("discovery_bio") or "").strip()
        prefs.discovery_bio = bio[:280] if bio else None
    for field in ("pace_min_sec", "pace_max_sec", "distance_min_km", "distance_max_km"):
        if field in payload:
            val = payload[field]
            setattr(prefs, field, float(val) if val not in (None, "") else None)
    for field in ("show_goals", "show_availability"):
        if field in payload and payload[field] is not None:
            setattr(prefs, field, bool(payload[field]))
    if "private_lat" in payload and "private_lng" in payload:
        lat, lng = payload.get("private_lat"), payload.get("private_lng")
        if lat is not None and lng is not None:
            prefs.private_lat = float(lat)
            prefs.private_lng = float(lng)
    prefs.updated_at = utcnow()
    db.flush()
    return prefs


def _swiped_ids(db: Session, viewer_id: int) -> set[int]:
    rows = (
        db.query(DiscoverySwipe.to_athlete_id)
        .filter(DiscoverySwipe.from_athlete_id == viewer_id)
        .all()
    )
    return {int(r[0]) for r in rows}


def _matched_ids(db: Session, viewer_id: int) -> set[int]:
    rows = (
        db.query(DiscoveryMatch.athlete_a_id, DiscoveryMatch.athlete_b_id)
        .filter(
            (DiscoveryMatch.athlete_a_id == viewer_id)
            | (DiscoveryMatch.athlete_b_id == viewer_id)
        )
        .all()
    )
    out: set[int] = set()
    for a, b in rows:
        out.add(int(a) if int(a) != viewer_id else int(b))
    return out


def _within_radius(
    viewer: Athlete,
    prefs: DiscoveryPreference,
    other: Athlete,
    other_prefs: DiscoveryPreference | None,
) -> bool:
    mode = prefs.location_mode or "city"
    if mode == "anywhere":
        return True

    v_city = (prefs.manual_city or viewer.city or "").strip().lower()
    v_country = (prefs.manual_country or viewer.country or "").strip().lower()
    o_city = (other.city or "").strip().lower()
    o_country = (other.country or "").strip().lower()
    if other_prefs:
        o_city = (other_prefs.manual_city or other.city or "").strip().lower()
        o_country = (
            other_prefs.manual_country or other.country or ""
        ).strip().lower()

    radius = prefs.radius_km or 25
    if radius <= 10:
        if v_city and o_city:
            return v_city == o_city
        return v_country and o_country and v_country == o_country
    if radius <= 25:
        return bool(v_country and o_country and v_country == o_country)

    if (
        prefs.private_lat is not None
        and prefs.private_lng is not None
        and other_prefs
        and other_prefs.private_lat is not None
        and other_prefs.private_lng is not None
    ):
        km = _haversine_km(
            prefs.private_lat,
            prefs.private_lng,
            other_prefs.private_lat,
            other_prefs.private_lng,
        )
        return km <= float(radius)

    if v_country and o_country:
        return v_country == o_country
    return True


def _passes_filters(
    prefs: DiscoveryPreference,
    other_profile: dict,
) -> bool:
    pace = other_profile.get("easy_pace_sec_per_km")
    if prefs.pace_min_sec and pace and pace < prefs.pace_min_sec:
        return False
    if prefs.pace_max_sec and pace and pace > prefs.pace_max_sec:
        return False
    o_min = other_profile.get("typical_distance_km_min")
    o_max = other_profile.get("typical_distance_km_max")
    if prefs.distance_min_km and o_max and o_max < prefs.distance_min_km:
        return False
    if prefs.distance_max_km and o_min and o_min > prefs.distance_max_km:
        return False
    return True


def _serialize_discovery_card(
    db: Session,
    *,
    viewer: Athlete,
    other: Athlete,
    viewer_profile: dict,
    prefs: DiscoveryPreference,
    other_prefs: DiscoveryPreference | None,
) -> dict:
    card = serialize_match_card(
        db,
        viewer=viewer,
        other=other,
        viewer_profile=viewer_profile,
    )
    other_profile = estimate_running_profile(db, other.id)
    match = card["match"]
    card["compatibility_hint"] = _compat_hint(match)
    card["compatibility_level"] = (
        "high"
        if match.get("score", 0) >= 75
        else "good"
        if match.get("score", 0) >= 50
        else "ok"
    )

    dist_km = None
    if (
        prefs.private_lat is not None
        and prefs.private_lng is not None
        and other_prefs
        and other_prefs.private_lat is not None
        and other_prefs.private_lng is not None
    ):
        dist_km = _haversine_km(
            prefs.private_lat,
            prefs.private_lng,
            other_prefs.private_lat,
            other_prefs.private_lng,
        )
        card["distance_label"] = _approx_distance_label(dist_km)
    else:
        card["distance_label"] = card.get("location_label")

    city = other.city or (other_prefs.manual_city if other_prefs else None)
    card["location_public"] = city or other.country or "Nearby"

    op = other_prefs
    if op and op.show_goals and op.discovery_bio:
        card["discovery_bio"] = op.discovery_bio
    elif op and op.show_goals and op.goals:
        card["discovery_bio"] = op.goals
    elif other.bio:
        card["discovery_bio"] = (other.bio or "")[:160]
    else:
        card["discovery_bio"] = None

    if op and op.show_availability and op.available_days:
        card["availability"] = op.available_days

    return card


def _rank_candidates(
    db: Session,
    *,
    viewer: Athlete,
    prefs: DiscoveryPreference,
    limit: int = 40,
) -> list[tuple[Athlete, float]]:
    viewer_id = viewer.id
    excluded = _swiped_ids(db, viewer_id) | _matched_ids(db, viewer_id) | {viewer_id}
    viewer_profile = estimate_running_profile(db, viewer_id)

    filters = [Athlete.is_profile_public.is_(True)]
    if excluded:
        filters.append(~Athlete.id.in_(list(excluded)))

    candidates: list[Athlete] = []
    seen: set[int] = set()
    city = (prefs.manual_city or viewer.city or "").strip()
    country = (prefs.manual_country or viewer.country or "").strip()

    def _add(rows: list[Athlete]) -> None:
        for a in rows:
            if a.id not in seen and a.id not in excluded:
                seen.add(a.id)
                candidates.append(a)

    if city and prefs.location_mode != "anywhere":
        _add(
            db.query(Athlete)
            .filter(*filters, func.lower(Athlete.city) == city.lower())
            .order_by(Athlete.last_login_at.desc().nullslast())
            .limit(limit * 2)
            .all()
        )
    if country and len(candidates) < limit and prefs.radius_km >= 25:
        _add(
            db.query(Athlete)
            .filter(*filters, func.lower(Athlete.country) == country.lower())
            .order_by(Athlete.last_login_at.desc().nullslast())
            .limit(limit * 2)
            .all()
        )
    if len(candidates) < limit or prefs.location_mode == "anywhere":
        _add(
            db.query(Athlete)
            .filter(*filters)
            .order_by(Athlete.last_login_at.desc().nullslast())
            .limit(limit * 3)
            .all()
        )

    other_prefs_map = {
        p.athlete_id: p
        for p in db.query(DiscoveryPreference)
        .filter(DiscoveryPreference.athlete_id.in_([c.id for c in candidates]))
        .all()
    }

    scored: list[tuple[Athlete, float]] = []
    for other in candidates:
        op = other_prefs_map.get(other.id)
        if not _within_radius(viewer, prefs, other, op):
            continue
        other_profile = estimate_running_profile(db, other.id)
        if not _passes_filters(prefs, other_profile):
            continue
        match = compute_people_match(
            viewer_profile,
            other_profile,
            viewer=viewer,
            other=other,
        )
        score = float(match["score"])
        scored.append((other, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]


def get_next_person(db: Session, *, viewer_id: int) -> dict | None:
    viewer = db.query(Athlete).filter(Athlete.id == viewer_id).one_or_none()
    if not viewer:
        return None
    prefs = get_or_create_preferences(db, viewer_id)
    ranked = _rank_candidates(db, viewer=viewer, prefs=prefs, limit=40)
    if not ranked:
        return None
    viewer_profile = estimate_running_profile(db, viewer_id)
    other, _score = ranked[0]
    other_prefs = (
        db.query(DiscoveryPreference)
        .filter(DiscoveryPreference.athlete_id == other.id)
        .one_or_none()
    )
    card = _serialize_discovery_card(
        db,
        viewer=viewer,
        other=other,
        viewer_profile=viewer_profile,
        prefs=prefs,
        other_prefs=other_prefs,
    )
    remaining = max(0, len(ranked) - 1)
    return {"person": card, "remaining": remaining}


def record_swipe(
    db: Session,
    *,
    from_id: int,
    to_id: int,
    action: SwipeAction,
) -> dict:
    if from_id == to_id:
        raise DiscoveryError("Cannot swipe on yourself.", status_code=400)
    if action not in ("like", "pass"):
        raise DiscoveryError("Action must be like or pass.", status_code=400)

    target = (
        db.query(Athlete)
        .filter(Athlete.id == to_id, Athlete.is_profile_public.is_(True))
        .one_or_none()
    )
    if not target:
        raise DiscoveryError("Runner not found.", status_code=404)

    existing = (
        db.query(DiscoverySwipe)
        .filter(
            DiscoverySwipe.from_athlete_id == from_id,
            DiscoverySwipe.to_athlete_id == to_id,
        )
        .one_or_none()
    )
    if existing:
        return {"action": existing.action, "is_match": False, "match": None}

    swipe = DiscoverySwipe(
        from_athlete_id=from_id,
        to_athlete_id=to_id,
        action=action,
        created_at=utcnow(),
    )
    db.add(swipe)
    db.flush()

    is_match = False
    match_payload = None
    if action == "like":
        reciprocal = (
            db.query(DiscoverySwipe)
            .filter(
                DiscoverySwipe.from_athlete_id == to_id,
                DiscoverySwipe.to_athlete_id == from_id,
                DiscoverySwipe.action == "like",
            )
            .one_or_none()
        )
        if reciprocal:
            is_match = True
            key = pair_key_for(from_id, to_id)
            dm = (
                db.query(DiscoveryMatch)
                .filter(DiscoveryMatch.pair_key == key)
                .one_or_none()
            )
            if not dm:
                low, high = sorted((from_id, to_id))
                dm = DiscoveryMatch(
                    athlete_a_id=low,
                    athlete_b_id=high,
                    pair_key=key,
                    created_at=utcnow(),
                )
                db.add(dm)
                db.flush()
                conv = (
                    db.query(Conversation)
                    .filter(Conversation.pair_key == key)
                    .one_or_none()
                )
                if not conv:
                    conv = Conversation(
                        pair_key=key,
                        conversation_type="match",
                    )
                    db.add(conv)
                    db.flush()
                elif conv.conversation_type == "direct":
                    conv.conversation_type = "match"

            viewer = db.query(Athlete).filter(Athlete.id == from_id).one()
            viewer_profile = estimate_running_profile(db, from_id)
            card = serialize_match_card(
                db,
                viewer=viewer,
                other=target,
                viewer_profile=viewer_profile,
            )
            match_payload = {
                "match_id": dm.id,
                "person": card,
                "conversation_type": "match",
            }

    return {
        "action": action,
        "is_match": is_match,
        "match": match_payload,
    }


def list_matches(db: Session, *, viewer_id: int, limit: int = 30) -> list[dict]:
    safe = max(1, min(int(limit), 50))
    rows = (
        db.query(DiscoveryMatch)
        .filter(
            (DiscoveryMatch.athlete_a_id == viewer_id)
            | (DiscoveryMatch.athlete_b_id == viewer_id)
        )
        .order_by(DiscoveryMatch.created_at.desc())
        .limit(safe)
        .all()
    )
    viewer = db.query(Athlete).filter(Athlete.id == viewer_id).one()
    viewer_profile = estimate_running_profile(db, viewer_id)
    out = []
    for row in rows:
        other_id = (
            row.athlete_b_id
            if row.athlete_a_id == viewer_id
            else row.athlete_a_id
        )
        other = db.query(Athlete).filter(Athlete.id == other_id).one_or_none()
        if not other:
            continue
        card = serialize_match_card(
            db,
            viewer=viewer,
            other=other,
            viewer_profile=viewer_profile,
        )
        out.append(
            {
                "match_id": row.id,
                "matched_at": row.created_at.isoformat(),
                "person": card,
            }
        )
    return out


def has_discovery_match(db: Session, user_a: int, user_b: int) -> bool:
    key = pair_key_for(user_a, user_b)
    return (
        db.query(DiscoveryMatch)
        .filter(DiscoveryMatch.pair_key == key)
        .one_or_none()
        is not None
    )
