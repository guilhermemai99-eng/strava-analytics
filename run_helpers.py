"""Run CRUD, join/leave, listing, serialization."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from athlete import Athlete
from follow_helpers import is_following
from pace_compatibility import (
    compatibility_for_run,
    estimate_running_profile,
    format_pace_range,
    format_pace_seconds,
    parse_pace_to_seconds,
    participant_pace_label,
)
from profile_helpers import display_name_for, initials_for, public_avatar_url_for
from run import RUN_STATUSES, RUN_TYPES, RUN_VISIBILITIES, Run, RunParticipant


class RunError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_host(athlete: Athlete) -> dict:
    return {
        "athlete_id": athlete.id,
        "name": display_name_for(athlete),
        "handle": athlete.handle,
        "avatar_url": public_avatar_url_for(athlete),
        "initials": initials_for(athlete),
    }


def _participant_count(db: Session, run_id: int) -> int:
    return (
        db.query(func.count(RunParticipant.id))
        .filter(
            RunParticipant.run_id == run_id,
            RunParticipant.status == "going",
        )
        .scalar()
        or 0
    )


def _viewer_is_going(db: Session, run_id: int, viewer_id: int) -> bool:
    row = (
        db.query(RunParticipant.id)
        .filter(
            RunParticipant.run_id == run_id,
            RunParticipant.athlete_id == viewer_id,
            RunParticipant.status == "going",
        )
        .first()
    )
    return row is not None


def can_view_run(db: Session, run: Run, viewer_id: int) -> bool:
    if run.creator_id == viewer_id:
        return True
    if run.visibility == "everyone":
        return True
    if run.visibility == "followers":
        return is_following(
            db,
            follower_id=viewer_id,
            following_id=run.creator_id,
        ) or is_following(
            db,
            follower_id=run.creator_id,
            following_id=viewer_id,
        )
    # invite_only: visible if already going or creator
    return _viewer_is_going(db, run.id, viewer_id)


def can_join_run(db: Session, run: Run, viewer_id: int) -> bool:
    if run.status != "scheduled":
        return False
    if run.meeting_time <= _utcnow():
        return False
    if not can_view_run(db, run, viewer_id):
        return False
    if run.visibility == "invite_only" and run.creator_id != viewer_id:
        if not _viewer_is_going(db, run.id, viewer_id):
            return False
    if run.max_participants:
        count = _participant_count(db, run.id)
        if count >= run.max_participants and not _viewer_is_going(db, run.id, viewer_id):
            return False
    return True


def serialize_run(
    db: Session,
    run: Run,
    *,
    viewer_id: int,
    include_participants: bool = False,
    participant_limit: int = 8,
) -> dict:
    creator = db.query(Athlete).filter(Athlete.id == run.creator_id).one_or_none()
    going_count = _participant_count(db, run.id)
    profile = estimate_running_profile(db, viewer_id)
    compatibility = compatibility_for_run(
        profile,
        pace_min_sec=run.pace_min_sec,
        pace_max_sec=run.pace_max_sec,
    )

    payload = {
        "id": run.id,
        "title": run.title,
        "description": run.description,
        "location_name": run.location_name,
        "latitude": run.latitude,
        "longitude": run.longitude,
        "meeting_time": run.meeting_time.isoformat() if run.meeting_time else None,
        "distance_km": run.distance_km,
        "pace_min": format_pace_seconds(run.pace_min_sec),
        "pace_max": format_pace_seconds(run.pace_max_sec),
        "pace_range": format_pace_range(run.pace_min_sec, run.pace_max_sec),
        "run_type": run.run_type,
        "max_participants": run.max_participants,
        "visibility": run.visibility,
        "status": run.status,
        "club_id": run.club_id,
        "club": _serialize_club_ref(db, run.club_id),
        "participant_count": going_count,
        "is_host": run.creator_id == viewer_id,
        "is_going": _viewer_is_going(db, run.id, viewer_id),
        "can_join": can_join_run(db, run, viewer_id),
        "host": _serialize_host(creator) if creator else None,
        "compatibility": compatibility,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }

    if include_participants:
        rows = (
            db.query(RunParticipant, Athlete)
            .join(Athlete, Athlete.id == RunParticipant.athlete_id)
            .filter(
                RunParticipant.run_id == run.id,
                RunParticipant.status == "going",
            )
            .order_by(RunParticipant.joined_at.asc())
            .limit(participant_limit)
            .all()
        )
        payload["participants"] = [
            {
                "athlete_id": athlete.id,
                "name": display_name_for(athlete),
                "handle": athlete.handle,
                "avatar_url": public_avatar_url_for(athlete),
                "initials": initials_for(athlete),
                "pace_label": participant_pace_label(db, athlete.id),
                "joined_at": part.joined_at.isoformat() if part.joined_at else None,
            }
            for part, athlete in rows
        ]
    return payload


def serialize_run_card(db: Session, run: Run, *, viewer_id: int) -> dict:
    return serialize_run(db, run, viewer_id=viewer_id, include_participants=False)


def validate_run_type(run_type: str) -> str:
    normalized = (run_type or "easy").strip().lower()
    if normalized not in RUN_TYPES:
        raise RunError(f"Invalid run type. Use one of: {', '.join(RUN_TYPES)}")
    return normalized


def validate_visibility(visibility: str) -> str:
    normalized = (visibility or "everyone").strip().lower()
    if normalized not in RUN_VISIBILITIES:
        raise RunError(
            f"Invalid visibility. Use one of: {', '.join(RUN_VISIBILITIES)}"
        )
    return normalized


def parse_meeting_time(value: str) -> datetime:
    raw = (value or "").strip()
    if not raw:
        raise RunError("Meeting time is required.")
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise RunError("Invalid meeting time format.") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _serialize_club_ref(db: Session, club_id: int | None) -> dict | None:
    if not club_id:
        return None
    from club_helpers import serialize_club_ref

    return serialize_club_ref(db, club_id)


def create_run(
    db: Session,
    *,
    creator_id: int,
    title: str,
    description: str | None,
    location_name: str,
    latitude: float | None,
    longitude: float | None,
    meeting_time: datetime,
    distance_km: float,
    pace_min: str | float | None,
    pace_max: str | float | None,
    run_type: str,
    max_participants: int | None,
    visibility: str,
    route_data: dict | str | None,
    club_id: int | None = None,
) -> Run:
    title_clean = (title or "").strip()
    location_clean = (location_name or "").strip()
    if not title_clean:
        raise RunError("Title is required.")
    if not location_clean:
        raise RunError("Location is required.")
    if distance_km <= 0:
        raise RunError("Distance must be greater than zero.")
    if meeting_time <= _utcnow():
        raise RunError("Meeting time must be in the future.")

    pace_min_sec = parse_pace_to_seconds(pace_min)
    pace_max_sec = parse_pace_to_seconds(pace_max)
    if pace_min_sec and pace_max_sec and pace_min_sec > pace_max_sec:
        pace_min_sec, pace_max_sec = pace_max_sec, pace_min_sec

    route_text = None
    if route_data is not None:
        route_text = (
            route_data
            if isinstance(route_data, str)
            else json.dumps(route_data)
        )

    resolved_club_id = None
    if club_id:
        from club_helpers import can_manage_club, get_club

        club = get_club(db, int(club_id))
        if not club:
            raise RunError("Club not found.", status_code=404)
        if not can_manage_club(db, club_id=club.id, athlete_id=creator_id):
            raise RunError("Only club admins can host a club run.", status_code=403)
        resolved_club_id = club.id

    run = Run(
        creator_id=creator_id,
        club_id=resolved_club_id,
        title=title_clean,
        description=(description or "").strip() or None,
        location_name=location_clean,
        latitude=latitude,
        longitude=longitude,
        meeting_time=meeting_time,
        distance_km=float(distance_km),
        pace_min_sec=pace_min_sec,
        pace_max_sec=pace_max_sec,
        run_type=validate_run_type(run_type),
        max_participants=max_participants,
        visibility=validate_visibility(visibility),
        route_data=route_text,
        status="scheduled",
    )
    db.add(run)
    db.flush()

    host_part = RunParticipant(
        run_id=run.id,
        athlete_id=creator_id,
        status="going",
    )
    db.add(host_part)
    db.commit()
    db.refresh(run)
    return run


def update_run(
    db: Session,
    *,
    run: Run,
    editor_id: int,
    fields: dict,
) -> Run:
    if run.creator_id != editor_id:
        raise RunError("Only the host can edit this run.", status_code=403)
    if run.status == "cancelled":
        raise RunError("This run was cancelled.")

    if "title" in fields and fields["title"] is not None:
        title = str(fields["title"]).strip()
        if not title:
            raise RunError("Title cannot be empty.")
        run.title = title
    if "description" in fields:
        run.description = (fields.get("description") or "").strip() or None
    if "location_name" in fields and fields["location_name"] is not None:
        loc = str(fields["location_name"]).strip()
        if not loc:
            raise RunError("Location cannot be empty.")
        run.location_name = loc
    if "latitude" in fields:
        run.latitude = fields["latitude"]
    if "longitude" in fields:
        run.longitude = fields["longitude"]
    if "meeting_time" in fields and fields["meeting_time"] is not None:
        run.meeting_time = parse_meeting_time(str(fields["meeting_time"]))
    if "distance_km" in fields and fields["distance_km"] is not None:
        dist = float(fields["distance_km"])
        if dist <= 0:
            raise RunError("Distance must be greater than zero.")
        run.distance_km = dist
    if "pace_min" in fields:
        run.pace_min_sec = parse_pace_to_seconds(fields.get("pace_min"))
    if "pace_max" in fields:
        run.pace_max_sec = parse_pace_to_seconds(fields.get("pace_max"))
    if run.pace_min_sec and run.pace_max_sec and run.pace_min_sec > run.pace_max_sec:
        run.pace_min_sec, run.pace_max_sec = run.pace_max_sec, run.pace_min_sec
    if "run_type" in fields and fields["run_type"] is not None:
        run.run_type = validate_run_type(str(fields["run_type"]))
    if "max_participants" in fields:
        run.max_participants = fields.get("max_participants")
    if "visibility" in fields and fields["visibility"] is not None:
        run.visibility = validate_visibility(str(fields["visibility"]))

    run.updated_at = _utcnow()
    db.commit()
    db.refresh(run)
    return run


def cancel_run(db: Session, *, run: Run, editor_id: int) -> Run:
    if run.creator_id != editor_id:
        raise RunError("Only the host can cancel this run.", status_code=403)
    run.status = "cancelled"
    run.updated_at = _utcnow()
    db.commit()
    db.refresh(run)
    return run


def get_run(db: Session, run_id: int) -> Run | None:
    return (
        db.query(Run)
        .options(joinedload(Run.participants))
        .filter(Run.id == run_id)
        .one_or_none()
    )


def join_run(db: Session, *, run: Run, athlete_id: int) -> RunParticipant:
    if not can_join_run(db, run, athlete_id):
        raise RunError("You cannot join this run.", status_code=403)

    existing = (
        db.query(RunParticipant)
        .filter(
            RunParticipant.run_id == run.id,
            RunParticipant.athlete_id == athlete_id,
        )
        .one_or_none()
    )
    if existing:
        if existing.status == "going":
            return existing
        existing.status = "going"
        existing.joined_at = _utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    part = RunParticipant(run_id=run.id, athlete_id=athlete_id, status="going")
    db.add(part)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise RunError("Already joined this run.") from exc
    db.refresh(part)
    return part


def leave_run(db: Session, *, run: Run, athlete_id: int) -> None:
    if run.creator_id == athlete_id:
        raise RunError("Hosts cannot leave — cancel the run instead.")
    row = (
        db.query(RunParticipant)
        .filter(
            RunParticipant.run_id == run.id,
            RunParticipant.athlete_id == athlete_id,
            RunParticipant.status == "going",
        )
        .one_or_none()
    )
    if not row:
        raise RunError("You are not on this run.", status_code=404)
    row.status = "left"
    db.commit()


def list_discover_runs(
    db: Session,
    *,
    viewer_id: int,
    limit: int = 30,
    run_type: str | None = None,
    location_q: str | None = None,
) -> list[Run]:
    now = _utcnow()
    q = (
        db.query(Run)
        .filter(
            Run.status == "scheduled",
            Run.meeting_time > now,
        )
        .order_by(Run.meeting_time.asc())
        .limit(min(limit, 50))
    )
    if run_type:
        q = q.filter(Run.run_type == validate_run_type(run_type))
    if location_q:
        like = f"%{location_q.strip()}%"
        q = q.filter(Run.location_name.ilike(like))

    runs = q.all()
    visible = [r for r in runs if can_view_run(db, r, viewer_id)]
    return visible


def list_my_runs(
    db: Session,
    *,
    viewer_id: int,
    tab: str,
    limit: int = 40,
) -> list[Run]:
    now = _utcnow()
    tab = (tab or "upcoming").lower()

    if tab == "hosting":
        q = (
            db.query(Run)
            .filter(Run.creator_id == viewer_id)
            .order_by(Run.meeting_time.desc())
        )
        if limit:
            q = q.limit(min(limit, 50))
        return q.all()

    if tab == "past":
        q = (
            db.query(Run)
            .join(RunParticipant, RunParticipant.run_id == Run.id)
            .filter(
                RunParticipant.athlete_id == viewer_id,
                RunParticipant.status == "going",
                or_(Run.meeting_time <= now, Run.status.in_(("completed", "cancelled"))),
            )
            .order_by(Run.meeting_time.desc())
        )
        if limit:
            q = q.limit(min(limit, 50))
        return q.all()

    # upcoming — joined, future
    q = (
        db.query(Run)
        .join(RunParticipant, RunParticipant.run_id == Run.id)
        .filter(
            RunParticipant.athlete_id == viewer_id,
            RunParticipant.status == "going",
            Run.status == "scheduled",
            Run.meeting_time > now,
        )
        .order_by(Run.meeting_time.asc())
    )
    if limit:
        q = q.limit(min(limit, 50))
    return q.all()


def list_participants(
    db: Session,
    *,
    run_id: int,
    limit: int = 50,
) -> list[dict]:
    rows = (
        db.query(RunParticipant, Athlete)
        .join(Athlete, Athlete.id == RunParticipant.athlete_id)
        .filter(
            RunParticipant.run_id == run_id,
            RunParticipant.status == "going",
        )
        .order_by(RunParticipant.joined_at.asc())
        .limit(min(limit, 100))
        .all()
    )
    return [
        {
            "athlete_id": athlete.id,
            "name": display_name_for(athlete),
            "handle": athlete.handle,
            "avatar_url": public_avatar_url_for(athlete),
            "initials": initials_for(athlete),
            "pace_label": participant_pace_label(db, athlete.id),
            "joined_at": part.joined_at.isoformat() if part.joined_at else None,
        }
        for part, athlete in rows
    ]
