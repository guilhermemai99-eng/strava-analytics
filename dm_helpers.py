"""Direct messages: mutual-follow gate, inbox, threads, send/read."""

from __future__ import annotations

from datetime import datetime, timezone

from athlete import Athlete
from dm import Conversation, ConversationParticipant, DirectMessage, utcnow
from follow_helpers import is_following
from profile_helpers import display_name_for, initials_for, public_avatar_url_for
from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


MAX_MESSAGE_LEN = 2000
DEFAULT_MESSAGE_LIMIT = 50
MAX_MESSAGE_LIMIT = 100


class DmError(ValueError):
    """Domain error for DMs (mapped to HTTP by routes)."""

    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def pair_key_for(user_a: int, user_b: int) -> str:
    low, high = sorted((int(user_a), int(user_b)))
    return f"{low}:{high}"


def are_mutual_followers(db: Session, user_a: int, user_b: int) -> bool:
    if int(user_a) == int(user_b):
        return False
    return is_following(
        db, follower_id=user_a, following_id=user_b
    ) and is_following(db, follower_id=user_b, following_id=user_a)


def can_message(db: Session, user_a: int, user_b: int) -> bool:
    """Mutual follow or discovery match unlocks DMs."""
    if are_mutual_followers(db, user_a, user_b):
        return True
    from discovery_helpers import has_discovery_match

    return has_discovery_match(db, user_a, user_b)


def require_mutual(db: Session, user_a: int, user_b: int) -> None:
    if not can_message(db, user_a, user_b):
        raise DmError(
            "Messages are available when you follow each other or match.",
            status_code=403,
        )


def _serialize_person(athlete: Athlete) -> dict:
    return {
        "athlete_id": athlete.id,
        "display_name": display_name_for(athlete),
        "handle": athlete.handle,
        "avatar_url": public_avatar_url_for(athlete),
        "initials": initials_for(athlete),
    }


def get_participant(
    db: Session, *, conversation_id: int, user_id: int
) -> ConversationParticipant | None:
    return (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == user_id,
        )
        .one_or_none()
    )


def require_participant(
    db: Session, *, conversation_id: int, user_id: int
) -> ConversationParticipant:
    row = get_participant(
        db, conversation_id=conversation_id, user_id=user_id
    )
    if row is None:
        raise DmError("Conversation not found.", status_code=404)
    return row


def other_participant_id(
    db: Session, *, conversation_id: int, viewer_id: int
) -> int | None:
    row = (
        db.query(ConversationParticipant.user_id)
        .filter(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id != viewer_id,
        )
        .first()
    )
    return int(row[0]) if row else None


def get_conversation(db: Session, conversation_id: int) -> Conversation | None:
    return (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id)
        .one_or_none()
    )


def find_conversation_between(
    db: Session, user_a: int, user_b: int
) -> Conversation | None:
    key = pair_key_for(user_a, user_b)
    return (
        db.query(Conversation)
        .filter(Conversation.pair_key == key)
        .one_or_none()
    )


def ensure_participants(
    db: Session, *, conversation_id: int, user_a: int, user_b: int
) -> None:
    now = utcnow()
    for uid in (int(user_a), int(user_b)):
        exists = get_participant(
            db, conversation_id=conversation_id, user_id=uid
        )
        if exists is None:
            db.add(
                ConversationParticipant(
                    conversation_id=conversation_id,
                    user_id=uid,
                    joined_at=now,
                    last_read_at=None,
                )
            )
    db.commit()


def get_or_create_conversation(
    db: Session, *, viewer_id: int, peer_id: int
) -> Conversation:
    if int(viewer_id) == int(peer_id):
        raise DmError("Cannot message yourself.", status_code=400)

    peer = db.query(Athlete).filter(Athlete.id == peer_id).one_or_none()
    if peer is None:
        raise DmError("Athlete not found.", status_code=404)

    require_mutual(db, viewer_id, peer_id)

    existing = find_conversation_between(db, viewer_id, peer_id)
    if existing is not None:
        ensure_participants(
            db,
            conversation_id=existing.id,
            user_a=viewer_id,
            user_b=peer_id,
        )
        db.refresh(existing)
        return existing

    now = utcnow()
    conv = Conversation(
        pair_key=pair_key_for(viewer_id, peer_id),
        created_at=now,
        updated_at=now,
        last_message_at=None,
    )
    db.add(conv)
    try:
        db.flush()
        for uid in (viewer_id, peer_id):
            db.add(
                ConversationParticipant(
                    conversation_id=conv.id,
                    user_id=uid,
                    joined_at=now,
                    last_read_at=None,
                )
            )
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = find_conversation_between(db, viewer_id, peer_id)
        if existing is None:
            raise DmError("Could not open conversation.", status_code=409)
        ensure_participants(
            db,
            conversation_id=existing.id,
            user_a=viewer_id,
            user_b=peer_id,
        )
        return existing

    db.refresh(conv)
    return conv


def unread_count_for(
    db: Session,
    *,
    conversation_id: int,
    viewer_id: int,
    last_read_at: datetime | None,
) -> int:
    q = db.query(func.count(DirectMessage.id)).filter(
        DirectMessage.conversation_id == conversation_id,
        DirectMessage.sender_id != viewer_id,
    )
    if last_read_at is not None:
        q = q.filter(DirectMessage.created_at > last_read_at)
    return int(q.scalar() or 0)


def last_message_for(
    db: Session, conversation_id: int
) -> DirectMessage | None:
    return (
        db.query(DirectMessage)
        .filter(DirectMessage.conversation_id == conversation_id)
        .order_by(DirectMessage.created_at.desc(), DirectMessage.id.desc())
        .first()
    )


def serialize_conversation_summary(
    db: Session,
    *,
    conversation: Conversation,
    viewer_id: int,
) -> dict:
    peer_id = other_participant_id(
        db, conversation_id=conversation.id, viewer_id=viewer_id
    )
    peer = (
        db.query(Athlete).filter(Athlete.id == peer_id).one_or_none()
        if peer_id
        else None
    )
    me_part = get_participant(
        db, conversation_id=conversation.id, user_id=viewer_id
    )
    last = last_message_for(db, conversation.id)
    unread = unread_count_for(
        db,
        conversation_id=conversation.id,
        viewer_id=viewer_id,
        last_read_at=me_part.last_read_at if me_part else None,
    )
    can_send = bool(peer_id and can_message(db, viewer_id, peer_id))
    return {
        "id": conversation.id,
        "conversation_type": getattr(conversation, "conversation_type", "direct"),
        "peer": _serialize_person(peer) if peer else None,
        "last_message": serialize_message(last, viewer_id) if last else None,
        "last_message_at": (
            (last.created_at if last else conversation.last_message_at)
            or conversation.updated_at
        ),
        "unread_count": unread,
        "can_send": can_send,
        "is_mutual": can_send,
        "updated_at": conversation.updated_at,
        "created_at": conversation.created_at,
    }


def serialize_message(msg: DirectMessage, viewer_id: int) -> dict:
    return {
        "id": msg.id,
        "conversation_id": msg.conversation_id,
        "sender_id": msg.sender_id,
        "content": msg.content,
        "created_at": msg.created_at,
        "read_at": msg.read_at,
        "is_mine": int(msg.sender_id) == int(viewer_id),
    }


def list_conversations(
    db: Session, *, viewer_id: int, limit: int = 40
) -> list[dict]:
    safe_limit = max(1, min(int(limit), 80))
    mine_ids = [
        int(r[0])
        for r in db.query(ConversationParticipant.conversation_id)
        .filter(ConversationParticipant.user_id == viewer_id)
        .all()
    ]
    if not mine_ids:
        return []
    rows = (
        db.query(Conversation)
        .filter(Conversation.id.in_(mine_ids))
        .order_by(
            Conversation.last_message_at.desc().nullslast(),
            Conversation.updated_at.desc(),
        )
        .limit(safe_limit)
        .all()
    )
    return [
        serialize_conversation_summary(
            db, conversation=c, viewer_id=viewer_id
        )
        for c in rows
    ]


def get_conversation_for_viewer(
    db: Session, *, conversation_id: int, viewer_id: int
) -> dict:
    require_participant(
        db, conversation_id=conversation_id, user_id=viewer_id
    )
    conv = get_conversation(db, conversation_id)
    if conv is None:
        raise DmError("Conversation not found.", status_code=404)
    return serialize_conversation_summary(
        db, conversation=conv, viewer_id=viewer_id
    )


def list_messages(
    db: Session,
    *,
    conversation_id: int,
    viewer_id: int,
    limit: int = DEFAULT_MESSAGE_LIMIT,
    before_id: int | None = None,
) -> list[dict]:
    require_participant(
        db, conversation_id=conversation_id, user_id=viewer_id
    )
    safe_limit = max(1, min(int(limit), MAX_MESSAGE_LIMIT))
    q = db.query(DirectMessage).filter(
        DirectMessage.conversation_id == conversation_id
    )
    if before_id is not None:
        anchor = (
            db.query(DirectMessage)
            .filter(
                DirectMessage.id == before_id,
                DirectMessage.conversation_id == conversation_id,
            )
            .one_or_none()
        )
        if anchor is not None:
            q = q.filter(
                or_(
                    DirectMessage.created_at < anchor.created_at,
                    and_(
                        DirectMessage.created_at == anchor.created_at,
                        DirectMessage.id < anchor.id,
                    ),
                )
            )
    rows = (
        q.order_by(DirectMessage.created_at.desc(), DirectMessage.id.desc())
        .limit(safe_limit)
        .all()
    )
    rows.reverse()
    return [serialize_message(m, viewer_id) for m in rows]


def send_message(
    db: Session,
    *,
    conversation_id: int,
    sender_id: int,
    content: str,
) -> DirectMessage:
    require_participant(
        db, conversation_id=conversation_id, user_id=sender_id
    )
    peer_id = other_participant_id(
        db, conversation_id=conversation_id, viewer_id=sender_id
    )
    if peer_id is None:
        raise DmError("Conversation not found.", status_code=404)
    require_mutual(db, sender_id, peer_id)

    text = (content or "").strip()
    if not text:
        raise DmError("Message required.", status_code=400)
    if len(text) > MAX_MESSAGE_LEN:
        raise DmError("Message too long.", status_code=400)

    conv = get_conversation(db, conversation_id)
    if conv is None:
        raise DmError("Conversation not found.", status_code=404)

    now = utcnow()
    msg = DirectMessage(
        conversation_id=conversation_id,
        sender_id=sender_id,
        content=text,
        created_at=now,
        read_at=None,
    )
    db.add(msg)
    conv.last_message_at = now
    conv.updated_at = now

    # Sender has effectively "read" up to this send.
    me = get_participant(
        db, conversation_id=conversation_id, user_id=sender_id
    )
    if me is not None:
        me.last_read_at = now

    db.commit()
    db.refresh(msg)
    return msg


def mark_conversation_read(
    db: Session, *, conversation_id: int, viewer_id: int
) -> dict:
    part = require_participant(
        db, conversation_id=conversation_id, user_id=viewer_id
    )
    now = utcnow()
    part.last_read_at = now

    # Stamp unread inbound messages as read.
    (
        db.query(DirectMessage)
        .filter(
            DirectMessage.conversation_id == conversation_id,
            DirectMessage.sender_id != viewer_id,
            DirectMessage.read_at.is_(None),
        )
        .update({DirectMessage.read_at: now}, synchronize_session=False)
    )
    db.commit()
    return {"ok": True, "read_at": now}


def total_unread(db: Session, *, viewer_id: int) -> int:
    parts = (
        db.query(ConversationParticipant)
        .filter(ConversationParticipant.user_id == viewer_id)
        .all()
    )
    total = 0
    for part in parts:
        total += unread_count_for(
            db,
            conversation_id=part.conversation_id,
            viewer_id=viewer_id,
            last_read_at=part.last_read_at,
        )
    return total


def delete_dms_for_athlete(db: Session, athlete_id: int) -> dict:
    """Remove DM participation and orphaned conversations for account delete."""
    part_ids = [
        int(r[0])
        for r in db.query(ConversationParticipant.conversation_id)
        .filter(ConversationParticipant.user_id == athlete_id)
        .all()
    ]
    messages_deleted = (
        db.query(DirectMessage)
        .filter(DirectMessage.sender_id == athlete_id)
        .delete(synchronize_session=False)
    )
    parts_deleted = (
        db.query(ConversationParticipant)
        .filter(ConversationParticipant.user_id == athlete_id)
        .delete(synchronize_session=False)
    )
    convs_deleted = 0
    for cid in part_ids:
        remaining = (
            db.query(func.count(ConversationParticipant.id))
            .filter(ConversationParticipant.conversation_id == cid)
            .scalar()
            or 0
        )
        if remaining == 0:
            db.query(DirectMessage).filter(
                DirectMessage.conversation_id == cid
            ).delete(synchronize_session=False)
            convs_deleted += (
                db.query(Conversation)
                .filter(Conversation.id == cid)
                .delete(synchronize_session=False)
            )
    return {
        "messages_deleted": int(messages_deleted),
        "participants_deleted": int(parts_deleted),
        "conversations_deleted": int(convs_deleted),
    }
