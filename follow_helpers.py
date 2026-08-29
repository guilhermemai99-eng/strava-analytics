"""Follow graph helpers: counts, follow/unfollow, list rows."""

from __future__ import annotations

from athlete import Athlete
from follow import Follow
from explore_helpers import public_avatar_url_for
from profile_helpers import display_name_for, initials_for
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class FollowError(ValueError):
    pass


def normalize_route_handle(raw: str) -> str:
    return (raw or "").strip().lstrip("@").lower()


def get_athlete_by_handle(db: Session, handle: str) -> Athlete | None:
    normalized = normalize_route_handle(handle)
    if not normalized:
        return None
    return (
        db.query(Athlete)
        .filter(Athlete.handle == normalized)
        .one_or_none()
    )


def follower_count(db: Session, athlete_id: int) -> int:
    return (
        db.query(func.count(Follow.id))
        .filter(Follow.following_id == athlete_id)
        .scalar()
        or 0
    )


def following_count(db: Session, athlete_id: int) -> int:
    return (
        db.query(func.count(Follow.id))
        .filter(Follow.follower_id == athlete_id)
        .scalar()
        or 0
    )


def is_following(db: Session, *, follower_id: int, following_id: int) -> bool:
    if follower_id == following_id:
        return False
    row = (
        db.query(Follow.id)
        .filter(
            Follow.follower_id == follower_id,
            Follow.following_id == following_id,
        )
        .first()
    )
    return row is not None


def follow_counts_map(
    db: Session,
    athlete_ids: list[int],
) -> dict[int, dict[str, int]]:
    """Batch follower/following counts for list rows (avoid N+1)."""
    ids = list({int(i) for i in athlete_ids})
    out = {i: {"follower_count": 0, "following_count": 0} for i in ids}
    if not ids:
        return out

    for athlete_id, count in (
        db.query(Follow.following_id, func.count(Follow.id))
        .filter(Follow.following_id.in_(ids))
        .group_by(Follow.following_id)
        .all()
    ):
        out[int(athlete_id)]["follower_count"] = int(count)

    for athlete_id, count in (
        db.query(Follow.follower_id, func.count(Follow.id))
        .filter(Follow.follower_id.in_(ids))
        .group_by(Follow.follower_id)
        .all()
    ):
        out[int(athlete_id)]["following_count"] = int(count)

    return out


def following_set(
    db: Session,
    *,
    viewer_id: int,
    target_ids: list[int],
) -> set[int]:
    if not target_ids:
        return set()
    rows = (
        db.query(Follow.following_id)
        .filter(
            Follow.follower_id == viewer_id,
            Follow.following_id.in_(target_ids),
        )
        .all()
    )
    return {int(r[0]) for r in rows}


def create_follow(db: Session, *, follower_id: int, following_id: int) -> Follow:
    if follower_id == following_id:
        raise FollowError("You can’t follow yourself. Bold, though.")
    existing = (
        db.query(Follow)
        .filter(
            Follow.follower_id == follower_id,
            Follow.following_id == following_id,
        )
        .one_or_none()
    )
    if existing is not None:
        return existing

    row = Follow(follower_id=follower_id, following_id=following_id)
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise FollowError("Couldn’t follow that runner.") from exc
    db.refresh(row)
    return row


def delete_follow(db: Session, *, follower_id: int, following_id: int) -> bool:
    row = (
        db.query(Follow)
        .filter(
            Follow.follower_id == follower_id,
            Follow.following_id == following_id,
        )
        .one_or_none()
    )
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def serialize_follow_person(
    athlete: Athlete,
    *,
    follower_count_value: int = 0,
    following_count_value: int = 0,
    viewer_follows: bool = False,
    is_self: bool = False,
) -> dict:
    return {
        "athlete_id": athlete.id,
        "display_name": display_name_for(athlete),
        "handle": athlete.handle,
        "username": athlete.handle or athlete.username,
        "initials": initials_for(athlete),
        "avatar_url": public_avatar_url_for(athlete),
        "follower_count": int(follower_count_value),
        "following_count": int(following_count_value),
        "is_following": bool(viewer_follows) and not is_self,
        "is_self": bool(is_self),
    }


def list_followers(
    db: Session,
    *,
    athlete_id: int,
    viewer_id: int,
    limit: int = 50,
) -> list[dict]:
    safe_limit = max(1, min(int(limit), 100))
    rows = (
        db.query(Athlete)
        .join(Follow, Follow.follower_id == Athlete.id)
        .filter(Follow.following_id == athlete_id)
        .order_by(Follow.created_at.desc(), Athlete.id.desc())
        .limit(safe_limit)
        .all()
    )
    return _serialize_people(db, rows, viewer_id=viewer_id)


def list_following(
    db: Session,
    *,
    athlete_id: int,
    viewer_id: int,
    limit: int = 50,
) -> list[dict]:
    safe_limit = max(1, min(int(limit), 100))
    rows = (
        db.query(Athlete)
        .join(Follow, Follow.following_id == Athlete.id)
        .filter(Follow.follower_id == athlete_id)
        .order_by(Follow.created_at.desc(), Athlete.id.desc())
        .limit(safe_limit)
        .all()
    )
    return _serialize_people(db, rows, viewer_id=viewer_id)


def _serialize_people(
    db: Session,
    athletes: list[Athlete],
    *,
    viewer_id: int,
) -> list[dict]:
    ids = [a.id for a in athletes]
    counts = follow_counts_map(db, ids)
    follows = following_set(db, viewer_id=viewer_id, target_ids=ids)
    return [
        serialize_follow_person(
            athlete,
            follower_count_value=counts.get(athlete.id, {}).get("follower_count", 0),
            following_count_value=counts.get(athlete.id, {}).get("following_count", 0),
            viewer_follows=athlete.id in follows,
            is_self=athlete.id == viewer_id,
        )
        for athlete in athletes
    ]
