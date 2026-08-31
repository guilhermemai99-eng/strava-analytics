"""Home feed social: likes, comments, hide, privacy, reports, share."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from activity_social import (
    ACTIVITY_VISIBILITIES,
    ActivityComment,
    ActivityLike,
    ActivityReport,
    HiddenActivity,
)
from athlete import Athlete
from follow_helpers import followed_athlete_ids, is_following
from models import Activity
from profile_helpers import display_name_for, initials_for, public_avatar_url_for


class SocialError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_activity(db: Session, activity_id: int) -> Activity | None:
    return db.query(Activity).filter(Activity.id == activity_id).one_or_none()


def activity_visibility(activity: Activity) -> str:
    value = (getattr(activity, "visibility", None) or "public").strip().lower()
    return value if value in ACTIVITY_VISIBILITIES else "public"


def is_deleted(activity: Activity) -> bool:
    return getattr(activity, "deleted_at", None) is not None


def can_view_activity(
    db: Session, activity: Activity, *, viewer_id: int
) -> bool:
    if is_deleted(activity) and activity.athlete_id != viewer_id:
        return False
    if activity.athlete_id == viewer_id:
        return not is_deleted(activity)
    vis = activity_visibility(activity)
    if vis == "public":
        return True
    if vis == "followers":
        return is_following(
            db, follower_id=viewer_id, following_id=activity.athlete_id
        )
    return False


def require_viewable_activity(
    db: Session, activity_id: int, *, viewer_id: int
) -> Activity:
    activity = get_activity(db, activity_id)
    if activity is None or not can_view_activity(db, activity, viewer_id=viewer_id):
        raise SocialError("Post not found.", status_code=404)
    return activity


def validate_visibility(raw: str) -> str:
    value = (raw or "public").strip().lower()
    if value not in ACTIVITY_VISIBILITIES:
        raise SocialError("Visibility must be public, followers, or private.")
    return value


def _counts_for(db: Session, activity_ids: list[int]) -> tuple[dict, dict, set]:
    if not activity_ids:
        return {}, {}, set()
    like_rows = (
        db.query(ActivityLike.activity_id, func.count(ActivityLike.id))
        .filter(ActivityLike.activity_id.in_(activity_ids))
        .group_by(ActivityLike.activity_id)
        .all()
    )
    comment_rows = (
        db.query(ActivityComment.activity_id, func.count(ActivityComment.id))
        .filter(ActivityComment.activity_id.in_(activity_ids))
        .group_by(ActivityComment.activity_id)
        .all()
    )
    likes = {int(i): int(c) for i, c in like_rows}
    comments = {int(i): int(c) for i, c in comment_rows}
    return likes, comments, set()


def liked_ids_for_viewer(
    db: Session, *, viewer_id: int, activity_ids: list[int]
) -> set[int]:
    if not activity_ids:
        return set()
    rows = (
        db.query(ActivityLike.activity_id)
        .filter(
            ActivityLike.athlete_id == viewer_id,
            ActivityLike.activity_id.in_(activity_ids),
        )
        .all()
    )
    return {int(r[0]) for r in rows}


def social_payload(
    db: Session,
    activity: Activity,
    *,
    viewer_id: int,
    like_count: int | None = None,
    comment_count: int | None = None,
    is_liked: bool | None = None,
) -> dict:
    aid = activity.id
    if like_count is None:
        like_count = (
            db.query(func.count(ActivityLike.id))
            .filter(ActivityLike.activity_id == aid)
            .scalar()
            or 0
        )
    if comment_count is None:
        comment_count = (
            db.query(func.count(ActivityComment.id))
            .filter(ActivityComment.activity_id == aid)
            .scalar()
            or 0
        )
    if is_liked is None:
        is_liked = (
            db.query(ActivityLike.id)
            .filter(
                ActivityLike.activity_id == aid,
                ActivityLike.athlete_id == viewer_id,
            )
            .first()
            is not None
        )
    return {
        "visibility": activity_visibility(activity),
        "caption": (getattr(activity, "caption", None) or "").strip() or None,
        "like_count": int(like_count),
        "comment_count": int(comment_count),
        "is_liked": bool(is_liked),
        "is_own": activity.athlete_id == viewer_id,
        "can_edit": activity.athlete_id == viewer_id,
    }


def list_home_feed_activities(
    db: Session, *, viewer_id: int, limit: int = 30
) -> list[tuple[Activity, Athlete]]:
    following = followed_athlete_ids(db, viewer_id)
    if not following:
        return []
    author_ids = list(following)
    hidden_ids = [
        int(r[0])
        for r in db.query(HiddenActivity.activity_id)
        .filter(HiddenActivity.athlete_id == viewer_id)
        .all()
    ]
    filters = [
        Activity.athlete_id.in_(author_ids),
        Activity.deleted_at.is_(None),
        Activity.visibility.in_(("public", "followers")),
    ]
    if hidden_ids:
        filters.append(~Activity.id.in_(hidden_ids))
    rows = (
        db.query(Activity, Athlete)
        .join(Athlete, Athlete.id == Activity.athlete_id)
        .filter(*filters)
        .order_by(Activity.start_date_local.desc())
        .limit(min(max(limit, 1), 50))
        .all()
    )
    return rows


def list_visible_profile_activities(
    db: Session, *, target_id: int, viewer_id: int, limit: int = 24
) -> list[Activity]:
    q = db.query(Activity).filter(
        Activity.athlete_id == target_id,
        Activity.deleted_at.is_(None),
    )
    if target_id != viewer_id:
        follows = is_following(
            db, follower_id=viewer_id, following_id=target_id
        )
        if follows:
            q = q.filter(Activity.visibility.in_(("public", "followers")))
        else:
            q = q.filter(Activity.visibility == "public")
    return q.order_by(Activity.start_date_local.desc()).limit(
        min(max(limit, 1), 50)
    ).all()


def toggle_like(db: Session, *, activity: Activity, viewer_id: int) -> dict:
    existing = (
        db.query(ActivityLike)
        .filter(
            ActivityLike.activity_id == activity.id,
            ActivityLike.athlete_id == viewer_id,
        )
        .one_or_none()
    )
    if existing:
        db.delete(existing)
        db.commit()
        liked = False
    else:
        db.add(ActivityLike(activity_id=activity.id, athlete_id=viewer_id))
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise SocialError("Already liked.") from exc
        liked = True
        if activity.athlete_id != viewer_id:
            from notification_helpers import create_notification, KIND_LIKE
            from profile_helpers import display_name_for as _name

            actor = db.query(Athlete).filter(Athlete.id == viewer_id).one_or_none()
            if actor is not None:
                create_notification(
                    db,
                    recipient_id=activity.athlete_id,
                    actor_id=viewer_id,
                    kind=KIND_LIKE,
                    body=f"{_name(actor)} liked your run.",
                    target_type="activity",
                    target_id=activity.id,
                )
                db.commit()
    return social_payload(db, activity, viewer_id=viewer_id, is_liked=liked)


def list_likers(db: Session, *, activity_id: int, limit: int = 40) -> list[dict]:
    rows = (
        db.query(ActivityLike, Athlete)
        .join(Athlete, Athlete.id == ActivityLike.athlete_id)
        .filter(ActivityLike.activity_id == activity_id)
        .order_by(ActivityLike.created_at.desc())
        .limit(min(limit, 80))
        .all()
    )
    return [
        {
            "athlete_id": athlete.id,
            "name": display_name_for(athlete),
            "handle": athlete.handle,
            "avatar_url": public_avatar_url_for(athlete),
            "initials": initials_for(athlete),
        }
        for _like, athlete in rows
    ]


def serialize_comment(
    comment: ActivityComment, athlete: Athlete, *, viewer_id: int
) -> dict:
    return {
        "id": comment.id,
        "body": comment.body,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
        "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
        "is_own": comment.athlete_id == viewer_id,
        "author": {
            "athlete_id": athlete.id,
            "name": display_name_for(athlete),
            "handle": athlete.handle,
            "avatar_url": public_avatar_url_for(athlete),
            "initials": initials_for(athlete),
        },
    }


def list_comments(
    db: Session, *, activity_id: int, viewer_id: int, limit: int = 50
) -> list[dict]:
    rows = (
        db.query(ActivityComment, Athlete)
        .join(Athlete, Athlete.id == ActivityComment.athlete_id)
        .filter(ActivityComment.activity_id == activity_id)
        .order_by(ActivityComment.created_at.asc())
        .limit(min(limit, 100))
        .all()
    )
    return [
        serialize_comment(comment, athlete, viewer_id=viewer_id)
        for comment, athlete in rows
    ]


def add_comment(
    db: Session, *, activity: Activity, viewer_id: int, body: str
) -> ActivityComment:
    text = (body or "").strip()
    if not text:
        raise SocialError("Write a comment first.")
    if len(text) > 500:
        raise SocialError("Comment is too long.")
    row = ActivityComment(
        activity_id=activity.id,
        athlete_id=viewer_id,
        body=text,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    if activity.athlete_id != viewer_id:
        from notification_helpers import create_notification, KIND_COMMENT

        actor = db.query(Athlete).filter(Athlete.id == viewer_id).one_or_none()
        if actor is not None:
            create_notification(
                db,
                recipient_id=activity.athlete_id,
                actor_id=viewer_id,
                kind=KIND_COMMENT,
                body=f"{display_name_for(actor)} commented on your run.",
                target_type="activity",
                target_id=activity.id,
            )
            db.commit()
    return row


def get_comment(db: Session, comment_id: int) -> ActivityComment | None:
    return (
        db.query(ActivityComment)
        .filter(ActivityComment.id == comment_id)
        .one_or_none()
    )


def edit_comment(
    db: Session, *, comment: ActivityComment, viewer_id: int, body: str
) -> ActivityComment:
    if comment.athlete_id != viewer_id:
        raise SocialError("You can only edit your comment.", status_code=403)
    text = (body or "").strip()
    if not text:
        raise SocialError("Comment cannot be empty.")
    if len(text) > 500:
        raise SocialError("Comment is too long.")
    comment.body = text
    comment.updated_at = _utcnow()
    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(
    db: Session, *, comment: ActivityComment, viewer_id: int, activity: Activity
) -> None:
    if comment.athlete_id != viewer_id and activity.athlete_id != viewer_id:
        raise SocialError("You can only delete your comment.", status_code=403)
    db.delete(comment)
    db.commit()


def hide_activity(db: Session, *, activity_id: int, viewer_id: int) -> None:
    existing = (
        db.query(HiddenActivity)
        .filter(
            HiddenActivity.activity_id == activity_id,
            HiddenActivity.athlete_id == viewer_id,
        )
        .one_or_none()
    )
    if existing:
        return
    db.add(HiddenActivity(activity_id=activity_id, athlete_id=viewer_id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()


def unhide_activity(db: Session, *, activity_id: int, viewer_id: int) -> None:
    row = (
        db.query(HiddenActivity)
        .filter(
            HiddenActivity.activity_id == activity_id,
            HiddenActivity.athlete_id == viewer_id,
        )
        .one_or_none()
    )
    if row:
        db.delete(row)
        db.commit()


def set_visibility(
    db: Session, *, activity: Activity, viewer_id: int, visibility: str
) -> Activity:
    if activity.athlete_id != viewer_id:
        raise SocialError("Only the author can change privacy.", status_code=403)
    activity.visibility = validate_visibility(visibility)
    db.commit()
    db.refresh(activity)
    return activity


def set_caption(
    db: Session, *, activity: Activity, viewer_id: int, caption: str | None
) -> Activity:
    if activity.athlete_id != viewer_id:
        raise SocialError("Only the author can edit this post.", status_code=403)
    text = (caption or "").strip()
    activity.caption = text or None
    db.commit()
    db.refresh(activity)
    return activity


def soft_delete_activity(
    db: Session, *, activity: Activity, viewer_id: int
) -> None:
    if activity.athlete_id != viewer_id:
        raise SocialError("Only the author can delete this post.", status_code=403)
    activity.deleted_at = _utcnow()
    db.commit()


def report_activity(db: Session, *, activity_id: int, viewer_id: int) -> None:
    db.add(ActivityReport(activity_id=activity_id, reporter_id=viewer_id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()


def share_activity_via_dm(
    db: Session,
    *,
    activity: Activity,
    viewer_id: int,
    peer_ids: list[int],
) -> dict:
    from dm_helpers import DmError, get_or_create_conversation, send_message
    from feed_helpers import format_duration, format_pace
    from feed_titles import pulse_title_for_activity

    if not peer_ids:
        raise SocialError("Pick someone to send this to.")
    title = pulse_title_for_activity(
        activity.id,
        distance_m=activity.distance_m,
        moving_time_s=activity.moving_time_s,
        sport_type=activity.sport_type,
        name=activity.name,
    )
    km = (
        f"{round(float(activity.distance_m) / 1000.0, 1)} km"
        if activity.distance_m
        else ""
    )
    pace = format_pace(activity.distance_m, activity.moving_time_s) or ""
    duration = format_duration(activity.moving_time_s) or ""
    bits = [p for p in (km, duration, f"{pace}/km" if pace else "") if p]
    line = " · ".join(bits)
    content = f"Shared a run: {title}\n{line}\n#activity/{activity.id}".strip()

    sent = 0
    skipped = []
    unique_ids = []
    for raw in peer_ids:
        try:
            pid = int(raw)
        except (TypeError, ValueError):
            continue
        if pid == viewer_id or pid in unique_ids:
            continue
        unique_ids.append(pid)
    for peer_id in unique_ids[:12]:
        try:
            conv = get_or_create_conversation(
                db, viewer_id=viewer_id, peer_id=peer_id
            )
            send_message(
                db,
                conversation_id=conv.id,
                sender_id=viewer_id,
                content=content,
            )
            sent += 1
        except DmError as exc:
            skipped.append({"athlete_id": peer_id, "reason": str(exc)})
    if sent == 0:
        raise SocialError(
            skipped[0]["reason"] if skipped else "Could not send.",
            status_code=403 if skipped else 400,
        )
    return {"sent": sent, "skipped": skipped}
