"""Persist and serialize Pulse AI Coach chat messages."""

from __future__ import annotations

from coach_message import CoachMessage, utcnow
from sqlalchemy.orm import Session


MAX_STORED_MESSAGES = 80


def list_coach_messages(db: Session, athlete_id: int, *, limit: int = 40) -> list[CoachMessage]:
    safe = max(1, min(int(limit), 80))
    rows = (
        db.query(CoachMessage)
        .filter(CoachMessage.athlete_id == athlete_id)
        .order_by(CoachMessage.created_at.desc(), CoachMessage.id.desc())
        .limit(safe)
        .all()
    )
    return list(reversed(rows))


def serialize_coach_message(row: CoachMessage) -> dict:
    return {
        "id": row.id,
        "role": row.role,
        "content": row.content,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def add_coach_message(
    db: Session,
    athlete_id: int,
    role: str,
    content: str,
) -> CoachMessage:
    row = CoachMessage(
        athlete_id=athlete_id,
        role=role,
        content=content,
        created_at=utcnow(),
    )
    db.add(row)
    db.flush()
    return row


def trim_coach_messages(db: Session, athlete_id: int) -> None:
    rows = (
        db.query(CoachMessage)
        .filter(CoachMessage.athlete_id == athlete_id)
        .order_by(CoachMessage.created_at.desc(), CoachMessage.id.desc())
        .offset(MAX_STORED_MESSAGES)
        .all()
    )
    for row in rows:
        db.delete(row)


def clear_coach_messages(db: Session, athlete_id: int) -> int:
    rows = (
        db.query(CoachMessage)
        .filter(CoachMessage.athlete_id == athlete_id)
        .all()
    )
    count = len(rows)
    for row in rows:
        db.delete(row)
    return count


def history_for_model(rows: list[CoachMessage]) -> list[dict[str, str]]:
    out = []
    for row in rows:
        if row.role in {"user", "assistant"} and row.content:
            out.append({"role": row.role, "content": row.content})
    return out
