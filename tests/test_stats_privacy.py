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


def test_followers_only_hidden_from_strangers(
    client,
    make_session,
    make_athlete,
    make_activity,
    db_session,
):
    make_athlete(960020, firstname="Stranger", handle="stranger_x")
    make_athlete(
        960021,
        firstname="Author",
        handle="followers_only",
        is_profile_public=True,
    )
    make_activity(960021, strava_id=96002101, name="Public")
    followers = make_activity(960021, strava_id=96002102, name="Crew Only")
    followers.visibility = "followers"
    db_session.commit()

    raw, cookie = make_session(960020)
    client.cookies.set(cookie, raw)
    body = client.get("/api/profiles/followers_only").json()
    assert body["stats"]["activity_count"] == 1
    assert body["posts_count"] == 1


def test_own_activities_endpoint_skips_deleted(
    client,
    make_session,
    make_athlete,
    make_activity,
    db_session,
):
    make_athlete(960030, firstname="Owner")
    keep = make_activity(960030, strava_id=96003001, name="Keep")
    gone = make_activity(960030, strava_id=96003002, name="Gone")
    gone.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    raw, cookie = make_session(960030)
    client.cookies.set(cookie, raw)
    rows = client.get("/activities").json()
    ids = {row["id"] for row in rows}
    assert keep.id in ids
    assert gone.id not in ids


def test_activity_deep_link_api(
    client,
    make_session,
    make_athlete,
    make_activity,
):
    make_athlete(960040, firstname="Deep", is_profile_public=True)
    make_athlete(960041, firstname="Viewer")
    activity = make_activity(960040, strava_id=96004001, name="Deep Easy")
    raw, cookie = make_session(960041)
    client.cookies.set(cookie, raw)
    res = client.get(f"/api/activities/{activity.id}")
    assert res.status_code == 200
    body = res.json()
    assert body["activity"]["id"] == activity.id
    assert client.get("/api/activities/99999999").status_code == 404
