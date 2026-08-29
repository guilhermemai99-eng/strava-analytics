from datetime import datetime, timedelta, timezone

from oauth_state import OAuthState, utcnow


OAUTH_STATE_TTL_MINUTES = 10


def create_oauth_state(db, state: str) -> OAuthState:
    now = utcnow()
    row = OAuthState(
        state=state,
        created_at=now,
        expires_at=now + timedelta(minutes=OAUTH_STATE_TTL_MINUTES),
        consumed_at=None,
    )
    db.add(row)
    db.commit()
    return row


def consume_oauth_state(db, state: str) -> bool:
    """
    Validate and consume a one-time OAuth state.
    Returns True if valid, False otherwise.
    """

    if not state:
        return False

    row = (
        db.query(OAuthState)
        .filter(OAuthState.state == state)
        .one_or_none()
    )

    if row is None:
        return False

    now = utcnow()

    if row.consumed_at is not None:
        return False

    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        return False

    row.consumed_at = now
    db.commit()
    return True


def cleanup_expired_oauth_states(db) -> None:
    now = utcnow()
    (
        db.query(OAuthState)
        .filter(OAuthState.expires_at < now)
        .delete(synchronize_session=False)
    )
    db.commit()
