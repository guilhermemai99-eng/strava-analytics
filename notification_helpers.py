"""In-app notifications (Instagram-style activity feed)."""

from __future__ import annotations

from athlete import Athlete
from follow_helpers import is_following, relationship_payload
from notification import Notification, utcnow
from profile_helpers import display_name_for, public_avatar_url_for
from sqlalchemy.orm import Session


KIND_FOLLOW = "follow"
KIND_MUTUAL = "mutual"
KIND_MESSAGE = "message"
KIND_LIKE = "like"
KIND_COMMENT = "comment"
KIND_FOLLOW_REQUEST = "follow_request"
KIND_FOLLOW_ACCEPTED = "follow_accepted"


def _serialize_actor(athlete: Athlete | None) -> dict | None:
    if athlete is None:
        return None
    return {
        "athlete_id": athlete.id,
        "name": display_name_for(athlete),
        "handle": athlete.handle,
        "avatar_url": public_avatar_url_for(athlete),
    }


def create_notification(
    db: Session,
    *,
    recipient_id: int,
    actor_id: int | None,
    kind: str,
    body: str,
    target_type: str | None = None,
    target_id: int | None = None,
) -> Notification:
    if recipient_id == actor_id:
        raise ValueError("Cannot notify yourself.")
    row = Notification(
        recipient_id=recipient_id,
        actor_id=actor_id,
        kind=kind,
        body=body.strip(),
        target_type=target_type,
        target_id=target_id,
        read_at=None,
        created_at=utcnow(),
    )
    db.add(row)
    db.flush()
    db.refresh(row)
    return row


def notify_follow(db: Session, *, follower_id: int, following_id: int) -> None:
    """Notify the followed user; add mutual notice when both follow."""
    follower = db.query(Athlete).filter(Athlete.id == follower_id).one_or_none()
    if follower is None:
        return
    name = display_name_for(follower)
    create_notification(
        db,
        recipient_id=following_id,
        actor_id=follower_id,
        kind=KIND_FOLLOW,
        body=f"{name} started following you.",
        target_type="athlete",
        target_id=follower_id,
    )
    if is_following(db, follower_id=following_id, following_id=follower_id):
        following = db.query(Athlete).filter(Athlete.id == following_id).one_or_none()
        if following is not None:
            create_notification(
                db,
                recipient_id=follower_id,
                actor_id=following_id,
                kind=KIND_MUTUAL,
                body="You follow each other now. Say hi in Messages.",
                target_type="athlete",
                target_id=following_id,
            )
            create_notification(
                db,
                recipient_id=following_id,
                actor_id=follower_id,
                kind=KIND_MUTUAL,
                body="You follow each other now. Say hi in Messages.",
                target_type="athlete",
                target_id=follower_id,
            )
    db.commit()


def notify_follow_request(db: Session, *, requester_id: int, target_id: int) -> None:
    requester = db.query(Athlete).filter(Athlete.id == requester_id).one_or_none()
    if requester is None:
        return
    name = display_name_for(requester)
    create_notification(
        db,
        recipient_id=target_id,
        actor_id=requester_id,
        kind=KIND_FOLLOW_REQUEST,
        body=f"{name} requested to follow you.",
        target_type="athlete",
        target_id=requester_id,
    )
    db.commit()


def notify_follow_accepted(db: Session, *, target_id: int, requester_id: int) -> None:
    target = db.query(Athlete).filter(Athlete.id == target_id).one_or_none()
    if target is None:
        return
    name = display_name_for(target)
    create_notification(
        db,
        recipient_id=requester_id,
        actor_id=target_id,
        kind=KIND_FOLLOW_ACCEPTED,
        body=f"{name} accepted your follow request.",
        target_type="athlete",
        target_id=target_id,
    )
    if is_following(db, follower_id=target_id, following_id=requester_id):
        create_notification(
            db,
            recipient_id=requester_id,
            actor_id=target_id,
            kind=KIND_MUTUAL,
            body="You follow each other now. Say hi in Messages.",
            target_type="athlete",
            target_id=target_id,
        )
        create_notification(
            db,
            recipient_id=target_id,
            actor_id=requester_id,
            kind=KIND_MUTUAL,
            body="You follow each other now. Say hi in Messages.",
            target_type="athlete",
            target_id=requester_id,
        )
    db.commit()


def notify_message(
    db: Session,
    *,
    recipient_id: int,
    sender_id: int,
    conversation_id: int,
    preview: str,
) -> None:
    sender = db.query(Athlete).filter(Athlete.id == sender_id).one_or_none()
    if sender is None:
        return
    name = display_name_for(sender)
    text = (preview or "").strip()
    if len(text) > 80:
        text = text[:77] + "…"
    create_notification(
        db,
        recipient_id=recipient_id,
        actor_id=sender_id,
        kind=KIND_MESSAGE,
        body=f"{name} sent you a message: {text}",
        target_type="conversation",
        target_id=conversation_id,
    )
    db.commit()


def unread_count(db: Session, recipient_id: int) -> int:
    return (
        db.query(Notification.id)
        .filter(
            Notification.recipient_id == recipient_id,
            Notification.read_at.is_(None),
        )
        .count()
    )


def list_notifications(
    db: Session,
    *,
    recipient_id: int,
    limit: int = 40,
) -> list[dict]:
    safe_limit = max(1, min(int(limit), 80))
    rows = (
        db.query(Notification)
        .filter(Notification.recipient_id == recipient_id)
        .order_by(Notification.created_at.desc())
        .limit(safe_limit)
        .all()
    )
    actor_ids = {r.actor_id for r in rows if r.actor_id}
    actors: dict[int, Athlete] = {}
    if actor_ids:
        for a in db.query(Athlete).filter(Athlete.id.in_(actor_ids)).all():
            actors[a.id] = a

    out = []
    for row in rows:
        actor = actors.get(row.actor_id) if row.actor_id else None
        rel = None
        if actor is not None and row.kind in (KIND_FOLLOW, KIND_FOLLOW_REQUEST):
            rel = relationship_payload(
                db, viewer_id=recipient_id, target_id=actor.id
            )
        out.append(
            {
                "id": row.id,
                "kind": row.kind,
                "body": row.body,
                "read": row.read_at is not None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "actor": _serialize_actor(actor),
                "target_type": row.target_type,
                "target_id": row.target_id,
                "can_follow_back": bool(
                    rel
                    and row.kind == KIND_FOLLOW
                    and not rel.get("is_following")
                    and not rel.get("is_self")
                ),
                "can_accept_follow_request": bool(
                    rel
                    and row.kind == KIND_FOLLOW_REQUEST
                    and rel.get("has_incoming_follow_request")
                ),
            }
        )
    return out


def mark_all_read(db: Session, *, recipient_id: int) -> dict:
    now = utcnow()
    updated = (
        db.query(Notification)
        .filter(
            Notification.recipient_id == recipient_id,
            Notification.read_at.is_(None),
        )
        .update({Notification.read_at: now}, synchronize_session=False)
    )
    db.commit()
    return {"marked": int(updated or 0)}


def delete_notifications_for_athlete(db: Session, athlete_id: int) -> int:
    n = (
        db.query(Notification)
        .filter(
            (Notification.recipient_id == athlete_id)
            | (Notification.actor_id == athlete_id)
        )
        .delete(synchronize_session=False)
    )
    return int(n or 0)
