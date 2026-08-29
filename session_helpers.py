import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from user_session import UserSession, utcnow


SESSION_COOKIE_NAME = "session_id"
SESSION_TTL_DAYS = 30


def hash_session_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_session(
    db,
    athlete_id: int,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> str:
    raw_token = secrets.token_urlsafe(32)
    now = utcnow()

    row = UserSession(
        token_hash=hash_session_token(raw_token),
        athlete_id=athlete_id,
        created_at=now,
        expires_at=now + timedelta(days=SESSION_TTL_DAYS),
        last_seen_at=now,
        revoked_at=None,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(row)
    db.commit()
    return raw_token


def resolve_athlete_id(db, raw_token: str | None) -> int | None:
    if not raw_token:
        return None

    token_hash = hash_session_token(raw_token)
    row = (
        db.query(UserSession)
        .filter(UserSession.token_hash == token_hash)
        .one_or_none()
    )

    if row is None:
        return None

    if row.revoked_at is not None:
        return None

    now = utcnow()
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        return None

    row.last_seen_at = now
    db.commit()
    return row.athlete_id


def revoke_session(db, raw_token: str | None) -> None:
    if not raw_token:
        return

    token_hash = hash_session_token(raw_token)
    row = (
        db.query(UserSession)
        .filter(UserSession.token_hash == token_hash)
        .one_or_none()
    )

    if row is None:
        return

    if row.revoked_at is None:
        row.revoked_at = utcnow()
        db.commit()
