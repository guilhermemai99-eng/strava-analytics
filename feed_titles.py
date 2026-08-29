"""Deterministic Pulse titles for activity feed posts."""

from __future__ import annotations

import hashlib


# Buckets of lines keyed by vibe. Same activity always picks the same line.
TITLE_BANK: dict[str, tuple[str, ...]] = {
    "ultra_long": (
        "Long enough to question your life choices.",
        "Still standing. Somehow.",
        "That one needed a soundtrack.",
    ),
    "long": (
        "Just enough suffering.",
        "Miles collected. Ego adjusted.",
        "Went out for a run. Came back different.",
    ),
    "medium": (
        "Put in the work. Kept the receipts.",
        "Solid. Unbothered. Slightly sweaty.",
        "Another day, another set of miles.",
    ),
    "short": (
        "Quick. Painful. Worth it.",
        "Short run. Long attitude.",
        "In and out before excuses woke up.",
    ),
    "fast": (
        "Someone woke up dangerous.",
        "Pace said what it said.",
        "Legs filed a complaint. Ignored it.",
    ),
    "easy": (
        "Easy means easy. Allegedly.",
        "Recovery energy. Mostly.",
        "Chill pace. Loud intentions.",
    ),
    "default": (
        "Survived another one.",
        "Out there. Moving. Count it.",
        "The couch lost today.",
    ),
}


def _stable_index(seed: str, size: int) -> int:
    if size <= 0:
        return 0
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % size


def _pick(bucket: str, activity_id: int | str) -> str:
    lines = TITLE_BANK.get(bucket) or TITLE_BANK["default"]
    return lines[_stable_index(f"pulse-title:{bucket}:{activity_id}", len(lines))]


def pace_min_per_km(distance_m: float | None, moving_time_s: int | None) -> float | None:
    if not distance_m or not moving_time_s or distance_m <= 0:
        return None
    km = float(distance_m) / 1000.0
    if km <= 0:
        return None
    return (float(moving_time_s) / 60.0) / km


def classify_title_bucket(
    *,
    distance_m: float | None,
    moving_time_s: int | None,
    sport_type: str | None = None,
    name: str | None = None,
) -> str:
    distance_km = (float(distance_m) / 1000.0) if distance_m else 0.0
    pace = pace_min_per_km(distance_m, moving_time_s)
    lowered = f"{name or ''} {sport_type or ''}".lower()

    if pace is not None and pace > 0 and pace < 4.35 and distance_km >= 3:
        return "fast"

    if "easy" in lowered or "recovery" in lowered:
        if pace is not None and pace >= 5.6:
            return "easy"

    if distance_km >= 20:
        return "ultra_long"
    if distance_km >= 10:
        return "long"
    if distance_km >= 5:
        return "medium"
    if distance_km > 0:
        if pace is not None and pace >= 6.0:
            return "easy"
        return "short"

    return "default"


def pulse_title_for_activity(
    activity_id: int | str,
    *,
    distance_m: float | None = None,
    moving_time_s: int | None = None,
    sport_type: str | None = None,
    name: str | None = None,
) -> str:
    bucket = classify_title_bucket(
        distance_m=distance_m,
        moving_time_s=moving_time_s,
        sport_type=sport_type,
        name=name,
    )
    return _pick(bucket, activity_id)
