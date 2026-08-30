"""Run clubs: create, join/leave, listing, club runs."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from athlete import Athlete
from club import CLUB_ROLES, CLUB_VISIBILITIES, ClubMember, RunClub
from profile_helpers import display_name_for, initials_for, public_avatar_url_for
from run import Run


class ClubError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _member_count(db: Session, club_id: int) -> int:
    return (
        db.query(func.count(ClubMember.id))
        .filter(ClubMember.club_id == club_id)
        .scalar()
        or 0
    )


def get_membership(
    db: Session, *, club_id: int, athlete_id: int
) -> ClubMember | None:
    return (
        db.query(ClubMember)
        .filter(
            ClubMember.club_id == club_id,
            ClubMember.athlete_id == athlete_id,
        )
        .one_or_none()
    )


def membership_role(db: Session, *, club_id: int, athlete_id: int) -> str | None:
    row = get_membership(db, club_id=club_id, athlete_id=athlete_id)
    return row.role if row else None


def can_manage_club(db: Session, *, club_id: int, athlete_id: int) -> bool:
    role = membership_role(db, club_id=club_id, athlete_id=athlete_id)
    return role in ("owner", "admin")


def can_view_club(db: Session, club: RunClub, viewer_id: int) -> bool:
    if club.visibility == "public":
        return True
    return get_membership(db, club_id=club.id, athlete_id=viewer_id) is not None


def validate_visibility(raw: str) -> str:
    value = (raw or "public").strip().lower()
    if value not in CLUB_VISIBILITIES:
        raise ClubError("Visibility must be public or private.")
    return value


def get_club(db: Session, club_id: int) -> RunClub | None:
    return db.query(RunClub).filter(RunClub.id == club_id).one_or_none()


def serialize_club_ref(db: Session, club_id: int | None) -> dict | None:
    if not club_id:
        return None
    club = get_club(db, club_id)
    if not club:
        return None
    return {"id": club.id, "name": club.name}


def serialize_club(
    db: Session,
    club: RunClub,
    *,
    viewer_id: int,
    include_members: bool = False,
    member_limit: int = 40,
) -> dict:
    role = membership_role(db, club_id=club.id, athlete_id=viewer_id)
    payload = {
        "id": club.id,
        "name": club.name,
        "description": club.description,
        "location_name": club.location_name,
        "cover_url": club.cover_url,
        "visibility": club.visibility,
        "member_count": _member_count(db, club.id),
        "is_member": role is not None,
        "role": role,
        "can_manage": role in ("owner", "admin"),
        "is_owner": role == "owner",
        "created_at": club.created_at.isoformat() if club.created_at else None,
    }
    if include_members:
        payload["members"] = list_members(db, club_id=club.id, limit=member_limit)
    return payload


def create_club(
    db: Session,
    *,
    creator_id: int,
    name: str,
    description: str | None,
    location_name: str | None,
    visibility: str,
    cover_url: str | None = None,
) -> RunClub:
    clean = (name or "").strip()
    if len(clean) < 3:
        raise ClubError("Club name must be at least 3 characters.")
    if len(clean) > 120:
        raise ClubError("Club name is too long.")

    club = RunClub(
        creator_id=creator_id,
        name=clean,
        description=(description or "").strip() or None,
        location_name=(location_name or "").strip() or None,
        visibility=validate_visibility(visibility),
        cover_url=(cover_url or "").strip() or None,
    )
    db.add(club)
    db.flush()
    db.add(
        ClubMember(
            club_id=club.id,
            athlete_id=creator_id,
            role="owner",
        )
    )
    db.commit()
    db.refresh(club)
    return club


def join_club(db: Session, *, club: RunClub, athlete_id: int) -> ClubMember:
    if club.visibility == "private":
        raise ClubError("This club is private. Ask an admin to invite you.", status_code=403)
    existing = get_membership(db, club_id=club.id, athlete_id=athlete_id)
    if existing:
        return existing
    member = ClubMember(club_id=club.id, athlete_id=athlete_id, role="member")
    db.add(member)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ClubError("Already a member.") from exc
    db.refresh(member)
    return member


def leave_club(db: Session, *, club: RunClub, athlete_id: int) -> None:
    row = get_membership(db, club_id=club.id, athlete_id=athlete_id)
    if not row:
        raise ClubError("You are not a member of this club.", status_code=404)
    if row.role == "owner":
        raise ClubError("Owners cannot leave — transfer or delete the club.")
    db.delete(row)
    db.commit()


def list_discover_clubs(
    db: Session,
    *,
    viewer_id: int,
    limit: int = 30,
    location_q: str | None = None,
) -> list[RunClub]:
    q = db.query(RunClub).filter(RunClub.visibility == "public")
    if location_q:
        like = f"%{location_q.strip()}%"
        q = q.filter(RunClub.location_name.ilike(like))
    return q.order_by(RunClub.created_at.desc()).limit(min(limit, 50)).all()


def list_my_clubs(db: Session, *, viewer_id: int, limit: int = 40) -> list[RunClub]:
    return (
        db.query(RunClub)
        .join(ClubMember, ClubMember.club_id == RunClub.id)
        .filter(ClubMember.athlete_id == viewer_id)
        .order_by(RunClub.created_at.desc())
        .limit(min(limit, 50))
        .all()
    )


def list_admin_clubs(db: Session, *, viewer_id: int) -> list[RunClub]:
    return (
        db.query(RunClub)
        .join(ClubMember, ClubMember.club_id == RunClub.id)
        .filter(
            ClubMember.athlete_id == viewer_id,
            ClubMember.role.in_(("owner", "admin")),
        )
        .order_by(RunClub.name.asc())
        .all()
    )


def list_members(db: Session, *, club_id: int, limit: int = 50) -> list[dict]:
    rows = (
        db.query(ClubMember, Athlete)
        .join(Athlete, Athlete.id == ClubMember.athlete_id)
        .filter(ClubMember.club_id == club_id)
        .order_by(
            ClubMember.role.asc(),
            ClubMember.joined_at.asc(),
        )
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
            "role": member.role,
            "joined_at": member.joined_at.isoformat() if member.joined_at else None,
        }
        for member, athlete in rows
    ]


def list_club_runs(
    db: Session,
    *,
    club_id: int,
    tab: str = "upcoming",
    limit: int = 30,
) -> list[Run]:
    now = _utcnow()
    tab = (tab or "upcoming").lower()
    q = db.query(Run).filter(Run.club_id == club_id)
    if tab == "past":
        q = q.filter(
            (Run.meeting_time <= now) | (Run.status.in_(("completed", "cancelled")))
        ).order_by(Run.meeting_time.desc())
    else:
        q = q.filter(Run.status == "scheduled", Run.meeting_time > now).order_by(
            Run.meeting_time.asc()
        )
    return q.limit(min(limit, 50)).all()
