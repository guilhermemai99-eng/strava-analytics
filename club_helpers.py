"""Run clubs: create, join/leave, listing, covers, invites, club runs."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from athlete import Athlete
from club import CLUB_VISIBILITIES, ClubMember, RunClub
from club_invite import ClubInvite
from follow_helpers import get_athlete_by_handle
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


def public_cover_url_for(club: RunClub) -> str | None:
    if not club.cover_data:
        return None
    version = 0
    if club.updated_at is not None:
        try:
            version = int(club.updated_at.timestamp())
        except (OSError, OverflowError, ValueError):
            version = 0
    return f"/api/clubs/{club.id}/cover?v={version}"


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
    pending_invite = (
        db.query(ClubInvite)
        .filter(
            ClubInvite.club_id == club.id,
            ClubInvite.invitee_id == viewer_id,
            ClubInvite.status == "pending",
        )
        .one_or_none()
    )
    payload = {
        "id": club.id,
        "name": club.name,
        "description": club.description,
        "location_name": club.location_name,
        "cover_url": public_cover_url_for(club),
        "visibility": club.visibility,
        "member_count": _member_count(db, club.id),
        "is_member": role is not None,
        "role": role,
        "can_manage": role in ("owner", "admin"),
        "is_owner": role == "owner",
        "pending_invite_id": pending_invite.id if pending_invite else None,
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
        cover_url=None,
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


def set_club_cover(
    db: Session,
    *,
    club: RunClub,
    actor_id: int,
    data: bytes,
    content_type: str,
) -> RunClub:
    if not can_manage_club(db, club_id=club.id, athlete_id=actor_id):
        raise ClubError("Only owners and admins can change the cover.", status_code=403)
    club.cover_data = data
    club.cover_content_type = content_type
    club.updated_at = _utcnow()
    db.commit()
    db.refresh(club)
    return club


def clear_club_cover(db: Session, *, club: RunClub, actor_id: int) -> RunClub:
    if not can_manage_club(db, club_id=club.id, athlete_id=actor_id):
        raise ClubError("Only owners and admins can change the cover.", status_code=403)
    club.cover_data = None
    club.cover_content_type = None
    club.updated_at = _utcnow()
    db.commit()
    db.refresh(club)
    return club


def join_club(db: Session, *, club: RunClub, athlete_id: int) -> ClubMember:
    if club.visibility == "private":
        raise ClubError(
            "This club is private. Ask an admin to invite you.", status_code=403
        )
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

    from notification_helpers import notify_club_join

    notify_club_join(
        db,
        club_id=club.id,
        joiner_id=athlete_id,
        club_name=club.name or "your club",
        admin_ids=list_admin_ids(db, club_id=club.id),
    )
    return member


def _add_member(db: Session, *, club: RunClub, athlete_id: int) -> ClubMember:
    existing = get_membership(db, club_id=club.id, athlete_id=athlete_id)
    if existing:
        return existing
    member = ClubMember(club_id=club.id, athlete_id=athlete_id, role="member")
    db.add(member)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ClubError("Already a member.") from exc
    return member


def list_admin_ids(db: Session, *, club_id: int) -> list[int]:
    rows = (
        db.query(ClubMember.athlete_id)
        .filter(
            ClubMember.club_id == club_id,
            ClubMember.role.in_(("owner", "admin")),
        )
        .all()
    )
    return [int(r[0]) for r in rows]


def list_member_ids(db: Session, *, club_id: int) -> list[int]:
    rows = (
        db.query(ClubMember.athlete_id)
        .filter(ClubMember.club_id == club_id)
        .all()
    )
    return [int(r[0]) for r in rows]


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


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _serialize_invite(
    db: Session, invite: ClubInvite, *, club: RunClub | None = None
) -> dict:
    club = club or get_club(db, invite.club_id)
    invitee = None
    if invite.invitee_id:
        invitee = db.query(Athlete).filter(Athlete.id == invite.invitee_id).one_or_none()
    inviter = db.query(Athlete).filter(Athlete.id == invite.inviter_id).one_or_none()
    return {
        "id": invite.id,
        "club_id": invite.club_id,
        "club_name": club.name if club else None,
        "status": invite.status,
        "is_link": invite.token_hash is not None and invite.invitee_id is None,
        "created_at": invite.created_at.isoformat() if invite.created_at else None,
        "invitee": (
            {
                "athlete_id": invitee.id,
                "name": display_name_for(invitee),
                "handle": invitee.handle,
                "avatar_url": public_avatar_url_for(invitee),
                "initials": initials_for(invitee),
            }
            if invitee
            else None
        ),
        "inviter": (
            {
                "athlete_id": inviter.id,
                "name": display_name_for(inviter),
                "handle": inviter.handle,
                "avatar_url": public_avatar_url_for(inviter),
                "initials": initials_for(inviter),
            }
            if inviter
            else None
        ),
    }


def resolve_invitee(
    db: Session, *, athlete_id: int | None, handle: str | None
) -> Athlete:
    if athlete_id:
        row = db.query(Athlete).filter(Athlete.id == int(athlete_id)).one_or_none()
        if row is None:
            raise ClubError("Runner not found.", status_code=404)
        return row
    clean = (handle or "").strip().lstrip("@")
    if not clean:
        raise ClubError("Provide a handle or athlete id.")
    row = get_athlete_by_handle(db, clean)
    if row is None:
        raise ClubError("Runner not found.", status_code=404)
    return row


def create_direct_invite(
    db: Session,
    *,
    club: RunClub,
    inviter_id: int,
    athlete_id: int | None = None,
    handle: str | None = None,
) -> ClubInvite:
    if not can_manage_club(db, club_id=club.id, athlete_id=inviter_id):
        raise ClubError("Only owners and admins can invite.", status_code=403)
    invitee = resolve_invitee(db, athlete_id=athlete_id, handle=handle)
    if invitee.id == inviter_id:
        raise ClubError("You are already in this club.")
    if get_membership(db, club_id=club.id, athlete_id=invitee.id):
        raise ClubError("They are already a member.")
    existing = (
        db.query(ClubInvite)
        .filter(
            ClubInvite.club_id == club.id,
            ClubInvite.invitee_id == invitee.id,
            ClubInvite.status == "pending",
        )
        .one_or_none()
    )
    if existing:
        return existing

    invite = ClubInvite(
        club_id=club.id,
        inviter_id=inviter_id,
        invitee_id=invitee.id,
        token_hash=None,
        status="pending",
        created_at=_utcnow(),
        expires_at=_utcnow() + timedelta(days=14),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    from notification_helpers import notify_club_invite

    notify_club_invite(
        db,
        club_id=club.id,
        inviter_id=inviter_id,
        invitee_id=invitee.id,
        club_name=club.name or "a club",
        invite_id=invite.id,
    )
    return invite


def list_pending_invites_for_club(
    db: Session, *, club_id: int, actor_id: int
) -> list[dict]:
    if not can_manage_club(db, club_id=club_id, athlete_id=actor_id):
        raise ClubError("Only owners and admins can view invites.", status_code=403)
    club = get_club(db, club_id)
    rows = (
        db.query(ClubInvite)
        .filter(
            ClubInvite.club_id == club_id,
            ClubInvite.status == "pending",
            ClubInvite.invitee_id.isnot(None),
        )
        .order_by(ClubInvite.created_at.desc())
        .limit(50)
        .all()
    )
    return [_serialize_invite(db, row, club=club) for row in rows]


def list_incoming_club_invites(db: Session, *, invitee_id: int) -> list[dict]:
    rows = (
        db.query(ClubInvite)
        .filter(
            ClubInvite.invitee_id == invitee_id,
            ClubInvite.status == "pending",
        )
        .order_by(ClubInvite.created_at.desc())
        .limit(40)
        .all()
    )
    return [_serialize_invite(db, row) for row in rows]


def cancel_invite(
    db: Session, *, club: RunClub, invite_id: int, actor_id: int
) -> None:
    if not can_manage_club(db, club_id=club.id, athlete_id=actor_id):
        raise ClubError("Only owners and admins can cancel invites.", status_code=403)
    invite = (
        db.query(ClubInvite)
        .filter(ClubInvite.id == invite_id, ClubInvite.club_id == club.id)
        .one_or_none()
    )
    if invite is None or invite.status != "pending":
        raise ClubError("Invite not found.", status_code=404)
    invite.status = "cancelled"
    invite.responded_at = _utcnow()
    db.commit()


def accept_invite(db: Session, *, invite_id: int, athlete_id: int) -> RunClub:
    invite = db.query(ClubInvite).filter(ClubInvite.id == invite_id).one_or_none()
    if (
        invite is None
        or invite.invitee_id != athlete_id
        or invite.status != "pending"
    ):
        raise ClubError("Invite not found.", status_code=404)
    if invite.expires_at and invite.expires_at < _utcnow():
        invite.status = "cancelled"
        invite.responded_at = _utcnow()
        db.commit()
        raise ClubError("This invite expired.", status_code=410)

    club = get_club(db, invite.club_id)
    if club is None:
        raise ClubError("Club not found.", status_code=404)

    _add_member(db, club=club, athlete_id=athlete_id)
    invite.status = "accepted"
    invite.responded_at = _utcnow()
    db.commit()
    db.refresh(club)

    from notification_helpers import notify_club_invite_accepted, notify_club_join

    notify_club_invite_accepted(
        db,
        club_id=club.id,
        inviter_id=invite.inviter_id,
        invitee_id=athlete_id,
        club_name=club.name or "your club",
    )
    notify_club_join(
        db,
        club_id=club.id,
        joiner_id=athlete_id,
        club_name=club.name or "your club",
        admin_ids=list_admin_ids(db, club_id=club.id),
    )
    return club


def decline_invite(db: Session, *, invite_id: int, athlete_id: int) -> None:
    invite = db.query(ClubInvite).filter(ClubInvite.id == invite_id).one_or_none()
    if (
        invite is None
        or invite.invitee_id != athlete_id
        or invite.status != "pending"
    ):
        raise ClubError("Invite not found.", status_code=404)
    invite.status = "declined"
    invite.responded_at = _utcnow()
    db.commit()


def create_or_rotate_invite_link(
    db: Session, *, club: RunClub, inviter_id: int
) -> dict:
    if not can_manage_club(db, club_id=club.id, athlete_id=inviter_id):
        raise ClubError(
            "Only owners and admins can create invite links.", status_code=403
        )

    (
        db.query(ClubInvite)
        .filter(
            ClubInvite.club_id == club.id,
            ClubInvite.invitee_id.is_(None),
            ClubInvite.status == "pending",
        )
        .update(
            {
                ClubInvite.status: "revoked",
                ClubInvite.responded_at: _utcnow(),
            },
            synchronize_session=False,
        )
    )

    raw = secrets.token_urlsafe(24)
    invite = ClubInvite(
        club_id=club.id,
        inviter_id=inviter_id,
        invitee_id=None,
        token_hash=_hash_token(raw),
        status="pending",
        created_at=_utcnow(),
        expires_at=None,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return {
        "invite_id": invite.id,
        "token": raw,
        "path": f"/dashboard?club_invite={raw}#club/{club.id}",
    }


def redeem_invite_token(db: Session, *, token: str, athlete_id: int) -> RunClub:
    clean = (token or "").strip()
    if not clean:
        raise ClubError("Invite token required.")
    invite = (
        db.query(ClubInvite)
        .filter(
            ClubInvite.token_hash == _hash_token(clean),
            ClubInvite.invitee_id.is_(None),
            ClubInvite.status == "pending",
        )
        .one_or_none()
    )
    if invite is None:
        raise ClubError("Invite link is invalid or expired.", status_code=404)
    club = get_club(db, invite.club_id)
    if club is None:
        raise ClubError("Club not found.", status_code=404)

    existing = get_membership(db, club_id=club.id, athlete_id=athlete_id)
    if existing:
        return club

    _add_member(db, club=club, athlete_id=athlete_id)
    db.commit()
    db.refresh(club)

    from notification_helpers import notify_club_join

    notify_club_join(
        db,
        club_id=club.id,
        joiner_id=athlete_id,
        club_name=club.name or "your club",
        admin_ids=list_admin_ids(db, club_id=club.id),
    )
    return club


def has_pending_club_invite(
    db: Session, *, invitee_id: int, club_id: int
) -> bool:
    return (
        db.query(ClubInvite.id)
        .filter(
            ClubInvite.invitee_id == invitee_id,
            ClubInvite.club_id == club_id,
            ClubInvite.status == "pending",
        )
        .first()
        is not None
    )
