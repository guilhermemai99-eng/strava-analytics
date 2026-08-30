"""Activity likes, comments, hide, privacy, following feed."""

from __future__ import annotations

from follow_helpers import create_follow


def _login(client, make_session, athlete_id: int):
    raw, cookie = make_session(athlete_id)
    client.cookies.set(cookie, raw)


def test_like_comment_hide_and_privacy(
    client, make_session, make_athlete, make_activity, db_session
):
    make_athlete(950001, firstname="Author", lastname="Run", is_profile_public=True)
    make_athlete(950002, firstname="Friend", lastname="Run", is_profile_public=True)
    activity = make_activity(950001, strava_id=95000101, name="River Loop")

    _login(client, make_session, 950002)
    like = client.post(f"/api/activities/{activity.id}/like")
    assert like.status_code == 200, like.text
    assert like.json()["is_liked"] is True
    assert like.json()["like_count"] == 1
    unlike = client.post(f"/api/activities/{activity.id}/like")
    assert unlike.json()["is_liked"] is False
    client.post(f"/api/activities/{activity.id}/like")

    comment = client.post(
        f"/api/activities/{activity.id}/comments", json={"body": "See you Sunday"}
    )
    assert comment.status_code == 200, comment.text
    cid = comment.json()["id"]
    listed = client.get(f"/api/activities/{activity.id}/comments")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["body"] == "See you Sunday"

    edited = client.patch(
        f"/api/activities/{activity.id}/comments/{cid}",
        json={"body": "See you Saturday"},
    )
    assert edited.json()["body"] == "See you Saturday"

    deleted = client.delete(f"/api/activities/{activity.id}/comments/{cid}")
    assert deleted.status_code == 200

    hidden = client.post(f"/api/activities/{activity.id}/hide")
    assert hidden.status_code == 200
    create_follow(db_session, follower_id=950002, following_id=950001)
    feed = client.get("/api/feed")
    assert all(item["activity"]["id"] != activity.id for item in feed.json()["items"])

    client.post(f"/api/activities/{activity.id}/unhide")
    feed2 = client.get("/api/feed")
    assert any(item["activity"]["id"] == activity.id for item in feed2.json()["items"])

    _login(client, make_session, 950001)
    vis = client.patch(
        f"/api/activities/{activity.id}/visibility", json={"visibility": "private"}
    )
    assert vis.status_code == 200
    assert vis.json()["visibility"] == "private"

    _login(client, make_session, 950002)
    hidden_priv = client.get("/api/feed")
    assert all(
        item["activity"]["id"] != activity.id for item in hidden_priv.json()["items"]
    )
    assert client.get(f"/api/activities/{activity.id}/likes").status_code == 404


def test_following_appears_in_home_feed(
    client, make_session, make_athlete, make_activity, db_session
):
    make_athlete(950010, firstname="Me", lastname="Feed", is_profile_public=True)
    make_athlete(950011, firstname="You", lastname="Feed", is_profile_public=True)
    mine = make_activity(950010, strava_id=95001001, name="My Easy")
    yours = make_activity(950011, strava_id=95001101, name="Your Long")
    create_follow(db_session, follower_id=950010, following_id=950011)

    _login(client, make_session, 950010)
    feed = client.get("/api/feed")
    assert feed.status_code == 200
    ids = {item["activity"]["id"] for item in feed.json()["items"]}
    assert mine.id in ids
    assert yours.id in ids


def test_stranger_public_post_stays_off_home_feed(
    client, make_session, make_athlete, make_activity
):
    make_athlete(950020, firstname="Solo", lastname="Feed")
    make_athlete(950021, firstname="Stranger", lastname="Feed", is_profile_public=True)
    other = make_activity(950021, strava_id=95002101, name="Not In Feed")
    _login(client, make_session, 950020)
    feed = client.get("/api/feed")
    ids = {item["activity"]["id"] for item in feed.json()["items"]}
    assert other.id not in ids
