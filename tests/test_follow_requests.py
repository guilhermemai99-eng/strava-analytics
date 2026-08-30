"""Follow requests for private accounts."""

from __future__ import annotations


def _login(client, make_session, athlete_id: int):
    raw, cookie = make_session(athlete_id)
    client.cookies.set(cookie, raw)
    return raw, cookie


def test_private_follow_is_request_then_accept(
    client, make_session, make_athlete, make_activity
):
    make_athlete(
        941001,
        firstname="Open",
        handle="req_open",
        is_profile_public=True,
    )
    make_athlete(
        941002,
        firstname="Closed",
        handle="req_closed",
        is_profile_public=False,
        bio="Secret miles.",
        city="Porto",
    )
    make_activity(941002, strava_id=94100201, name="Ghost run")

    _login(client, make_session, 941001)
    requested = client.post("/api/users/941002/follow")
    assert requested.status_code == 200
    body = requested.json()
    assert body["is_follow_requested"] is True
    assert body["is_following"] is False
    assert body["is_private_locked"] is True
    assert body["activities"] == []
    assert body.get("bio") in (None, "")

    followers = client.get("/api/users/941002/followers")
    assert followers.status_code == 404

    _login(client, make_session, 941002)
    inbox = client.get("/api/notifications").json()
    kinds = {item["kind"] for item in inbox["items"]}
    assert "follow_request" in kinds
    incoming = client.get("/api/follow-requests").json()
    assert incoming["count"] == 1
    assert incoming["items"][0]["requester_id"] == 941001

    accepted = client.post("/api/users/941001/follow-request/accept")
    assert accepted.status_code == 200
    assert accepted.json()["is_followed_by"] is True

    _login(client, make_session, 941001)
    opened = client.get("/api/users/941002")
    assert opened.status_code == 200
    full = opened.json()
    assert full["is_private_locked"] is False
    assert full["is_following"] is True
    assert len(full["activities"]) == 1
    assert full["bio"] == "Secret miles."

    notif = client.get("/api/notifications").json()
    assert "follow_accepted" in {item["kind"] for item in notif["items"]}


def test_private_follow_request_cancel_and_decline(
    client, make_session, make_athlete
):
    make_athlete(941010, handle="can_a", is_profile_public=True)
    make_athlete(941011, handle="can_b", is_profile_public=False)

    _login(client, make_session, 941010)
    assert client.post("/api/users/941011/follow").json()["is_follow_requested"] is True
    cancel = client.delete("/api/users/941011/follow")
    assert cancel.status_code == 200
    assert cancel.json()["is_follow_requested"] is False

    assert client.post("/api/profiles/can_b/follow").json()["is_follow_requested"] is True

    _login(client, make_session, 941011)
    declined = client.post("/api/users/941010/follow-request/decline")
    assert declined.status_code == 200
    assert declined.json()["declined"] is True
    assert client.get("/api/follow-requests").json()["count"] == 0

    _login(client, make_session, 941010)
    again = client.get("/api/users/941011").json()
    assert again["is_follow_requested"] is False
    assert again["is_private_locked"] is True


def test_follow_back_on_private_is_instant(client, make_session, make_athlete):
    make_athlete(941020, handle="back_public", is_profile_public=True)
    make_athlete(941021, handle="back_private", is_profile_public=False)

    # Private user follows a public runner first.
    _login(client, make_session, 941021)
    back = client.post("/api/users/941020/follow")
    assert back.status_code == 200
    assert back.json()["is_following"] is True

    # Public runner following them back should be instant, not a request.
    _login(client, make_session, 941020)
    instant = client.post("/api/users/941021/follow")
    assert instant.status_code == 200
    assert instant.json()["is_following"] is True
    assert instant.json()["is_follow_requested"] is False
    assert instant.json()["is_mutual"] is True
    assert instant.json()["is_private_locked"] is False


def test_explore_matches_are_people_not_activities(
    client, make_session, make_athlete, make_activity
):
    make_athlete(
        941030,
        firstname="Viewer",
        city="Porto",
        country="Portugal",
        is_profile_public=True,
    )
    make_athlete(
        941031,
        firstname="Matchy",
        handle="matchy_run",
        city="Porto",
        country="Portugal",
        is_profile_public=True,
    )
    make_activity(941030, strava_id=94103001, name="Easy")
    make_activity(941031, strava_id=94103101, name="Easy")

    _login(client, make_session, 941030)
    data = client.get("/api/explore").json()
    assert "matches" in data
    assert "items" not in data
    ids = [m["athlete_id"] for m in data["matches"]]
    assert 941031 in ids
    assert 941030 not in ids
    for match in data["matches"]:
        assert "latitude" not in match
        assert "longitude" not in match
