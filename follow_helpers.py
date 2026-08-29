"""Follow graph helpers: counts, follow/unfollow, lists, suggestions."""

from __future__ import annotations

from athlete import Athlete
from follow import Follow
from profile_helpers import display_name_for, initials_for, public_avatar_url_for
from sqlalchemy import func, or_
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


def get_athlete_by_id(db: Session, athlete_id: int) -> Athlete | None:
    return db.query(Athlete).filter(Athlete.id == athlete_id).one_or_none()


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


def relationship_payload(
    db: Session,
    *,
    viewer_id: int,
    target_id: int,
) -> dict:
    is_self = viewer_id == target_id
    following = (
        False
        if is_self
        else is_following(db, follower_id=viewer_id, following_id=target_id)
    )
    followed_by = (
        False
        if is_self
        else is_following(db, follower_id=target_id, following_id=viewer_id)
    )
    return {
        "is_self": is_self,
        "is_following": following,
        "is_followed_by": followed_by,
        "is_mutual": bool(following and followed_by),
    }


def followed_athlete_ids(db: Session, viewer_id: int) -> list[int]:
    """IDs the viewer follows — ready for a future Following Feed filter."""
    rows = (
        db.query(Follow.following_id)
        .filter(Follow.follower_id == viewer_id)
        .order_by(Follow.created_at.desc())
        .all()
    )
    return [int(r[0]) for r in rows]


def follow_counts_map(
    db: Session,
    athlete_ids: list[int],
) -> dict[int, dict[str, int]]:
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
        # Race: another request inserted the same edge.
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
    name = display_name_for(athlete)
    return {
        "id": athlete.id,
        "athlete_id": athlete.id,
        "name": name,
        "display_name": name,
        "handle": athlete.handle,
        "username": athlete.handle or athlete.username,
        "initials": initials_for(athlete),
        "avatar_url": public_avatar_url_for(athlete),
        "follower_count": int(follower_count_value),
        "following_count": int(following_count_value),
        "is_following": bool(viewer_follows) and not is_self,
        "is_self": bool(is_self),
    }


def _people_query_filter(q: str | None):
    needle = (q or "").strip().lstrip("@").lower()
    if len(needle) < 2:
        return None
    pattern = f"%{needle}%"
    return or_(
        func.lower(func.coalesce(Athlete.handle, "")).like(pattern),
        func.lower(func.coalesce(Athlete.display_name, "")).like(pattern),
        func.lower(func.coalesce(Athlete.username, "")).like(pattern),
        func.lower(func.coalesce(Athlete.firstname, "")).like(pattern),
        func.lower(func.coalesce(Athlete.lastname, "")).like(pattern),
    )


def list_followers(
    db: Session,
    *,
    athlete_id: int,
    viewer_id: int,
    limit: int = 30,
    offset: int = 0,
    q: str | None = None,
) -> dict:
    safe_limit = max(1, min(int(limit), 100))
    safe_offset = max(0, int(offset))
    base = (
        db.query(Athlete)
        .join(Follow, Follow.follower_id == Athlete.id)
        .filter(Follow.following_id == athlete_id)
    )
    search = _people_query_filter(q)
    if search is not None:
        base = base.filter(search)
    total = base.count()
    rows = (
        base.order_by(Follow.created_at.desc(), Athlete.id.desc())
        .offset(safe_offset)
        .limit(safe_limit)
        .all()
    )
    people = _serialize_people(db, rows, viewer_id=viewer_id)
    next_offset = safe_offset + len(people)
    return {
        "people": people,
        "count": len(people),
        "total": int(total),
        "limit": safe_limit,
        "offset": safe_offset,
        "has_more": next_offset < int(total),
        "next_offset": next_offset if next_offset < int(total) else None,
    }


def list_following(
    db: Session,
    *,
    athlete_id: int,
    viewer_id: int,
    limit: int = 30,
    offset: int = 0,
    q: str | None = None,
) -> dict:
    safe_limit = max(1, min(int(limit), 100))
    safe_offset = max(0, int(offset))
    base = (
        db.query(Athlete)
        .join(Follow, Follow.following_id == Athlete.id)
        .filter(Follow.follower_id == athlete_id)
    )
    search = _people_query_filter(q)
    if search is not None:
        base = base.filter(search)
    total = base.count()
    rows = (
        base.order_by(Follow.created_at.desc(), Athlete.id.desc())
        .offset(safe_offset)
        .limit(safe_limit)
        .all()
    )
    people = _serialize_people(db, rows, viewer_id=viewer_id)
    next_offset = safe_offset + len(people)
    return {
        "people": people,
        "count": len(people),
        "total": int(total),
        "limit": safe_limit,
        "offset": safe_offset,
        "has_more": next_offset < int(total),
        "next_offset": next_offset if next_offset < int(total) else None,
    }


def suggest_people(
    db: Session,
    *,
    viewer: Athlete,
    limit: int = 8,
) -> list[dict]:
    """Simple suggestions: public runners not yet followed (prefer same city/country)."""
    safe_limit = max(1, min(int(limit), 20))
    followed = set(followed_athlete_ids(db, viewer.id))
    followed.add(viewer.id)

    def _pick(extra_filters) -> list[Athlete]:
        filters = [Athlete.is_profile_public.is_(True), *extra_filters]
        if followed:
            filters.append(~Athlete.id.in_(list(followed)))
        return (
            db.query(Athlete)
            .filter(*filters)
            .order_by(Athlete.last_login_at.desc().nullslast(), Athlete.id.desc())
            .limit(safe_limit)
            .all()
        )

    city = (viewer.city or "").strip()
    country = (viewer.country or "").strip()
    picked: list[Athlete] = []
    if city:
        picked = _pick([func.lower(Athlete.city) == city.lower()])
    if len(picked) < safe_limit and country:
        more = _pick([func.lower(Athlete.country) == country.lower()])
        seen = {a.id for a in picked}
        for a in more:
            if a.id not in seen:
                picked.append(a)
                seen.add(a.id)
            if len(picked) >= safe_limit:
                break
    if len(picked) < safe_limit:
        more = _pick([])
        seen = {a.id for a in picked}
        for a in more:
            if a.id not in seen:
                picked.append(a)
                seen.add(a.id)
            if len(picked) >= safe_limit:
                break

    return _serialize_people(db, picked[:safe_limit], viewer_id=viewer.id)


def _serialize_people(
    db: Session,
    athletes: list[Athlete],
    *,
    viewer_id: int,
) -> list[dict]:
    from profile_helpers import ensure_handle

    # Assign stable public handles when missing so @urls work — Follow still
    # keys off athlete.id either way.
    for athlete in athletes:
        if not athlete.handle:
            ensure_handle(db, athlete)

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
