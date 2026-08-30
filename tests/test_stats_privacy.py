"""Activity stats respect visibility + soft-delete."""

from __future__ import annotations

from datetime import datetime, timezone


def test_profile_stats_hide_private_and_deleted_runs(
    client,
    make_session,
    make_athlete,
    make_activity,
    db_session,
):
    make_athlete(960001, firstname="Viewer")
    make_athlete(
        960002,
        firstname="Author",
        handle="stats_author",
        is_profile_public=True,
    )
    public = make_activity(960002, strava_id=96000201, name="Public Easy")
    private = make_activity(960002, strava_id=96000202, name="Secret Intervals")
    deleted = make_activity(960002, strava_id=96000203, name="Gone Long")

    private.visibility = "private"
    deleted.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    raw, cookie = make_session(960001)
    client.cookies.set(cookie, raw)

    body = client.get("/api/profiles/stats_author").json()
    assert body["stats"]["activity_count"] == 1
    assert body["posts_count"] == 1
    assert len(body["activities"]) == 1
    assert body["activities"][0]["id"] == public.id

    # Owner still sees private (non-deleted) in their own stats.
    raw_owner, cookie_owner = make_session(960002)
    client.cookies.set(cookie_owner, raw_owner)
    own = client.get("/api/profiles/stats_author").json()
    assert own["stats"]["activity_count"] == 2
    assert own["posts_count"] == 2


def test_explore_stats_count_public_only(
    client,
    make_session,
    make_athlete,
    make_activity,
    db_session,
):
    make_athlete(960010, firstname="Seeker", handle="seeker", is_profile_public=True)
    make_athlete(
        960011,
        firstname="Shown",
        handle="shown_runner",
        city="Lisboa",
        country="Portugal",
        is_profile_public=True,
    )
    make_activity(960011, strava_id=96001101, name="Public")
    hidden = make_activity(960011, strava_id=96001102, name="Private")
    hidden.visibility = "private"
    db_session.commit()

    raw, cookie = make_session(960010)
    client.cookies.set(cookie, raw)
    res = client.get("/api/explore/search", params={"q": "shown"})
    assert res.status_code == 200
    rows = res.json().get("athletes") or res.json().get("items") or res.json()
    if isinstance(rows, dict):
        rows = rows.get("results") or rows.get("athletes") or []
    match = next((r for r in rows if r.get("handle") == "shown_runner"), None)
    assert match is not None
    assert match["stats"]["activity_count"] == 1
