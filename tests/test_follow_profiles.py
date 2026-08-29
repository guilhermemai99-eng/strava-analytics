"""Public profiles + follow system."""

from __future__ import annotations

from profile_helpers import ensure_handle, suggest_handle_for, validate_handle
from session_helpers import SESSION_COOKIE_NAME


def test_profile_endpoints_require_auth(client):
    assert client.get("/api/profiles/someone").status_code == 401
    assert client.get("/api/profiles/someone/followers").status_code == 401
    assert client.get("/api/profiles/someone/following").status_code == 401
    assert client.post("/api/profiles/someone/follow").status_code == 401
    assert client.delete("/api/profiles/someone/follow").status_code == 401


def test_ensure_handle_is_stable(db_session, make_athlete):
    athlete = make_athlete(940001, firstname="João", lastname="Runs", username="joaoX")
    assert athlete.handle is None
    first = suggest_handle_for(athlete)
    assert first  # derived from username or name
    ensure_handle(db_session, athlete)
    db_session.refresh(athlete)
    handle = athlete.handle
    assert handle
    assert validate_handle(handle) == handle
    ensure_handle(db_session, athlete)
    db_session.refresh(athlete)
    assert athlete.handle == handle


def test_me_profile_assigns_handle(client, make_session, make_athlete):
    make_athlete(940002, firstname="Gui", lastname="Demo")
    raw, cookie = make_session(940002)
    client.cookies.set(cookie, raw)
    resp = client.get("/api/me/profile")
    assert resp.status_code == 200
    assert resp.json()["handle"]
    assert resp.json()["follower_count"] == 0
    assert resp.json()["following_count"] == 0


def test_public_profile_and_privacy(
    client,
    make_session,
    make_athlete,
    make_activity,
):
    make_athlete(940010, firstname="Viewer")
    make_athlete(
        940011,
        firstname="Public",
        handle="public_runner",
        is_profile_public=True,
        bio="Miles > meetings.",
        city="Porto",
        country="Portugal",
    )
    make_athlete(
        940012,
        firstname="Private",
        handle="private_runner",
        is_profile_public=False,
    )
    make_activity(940011, strava_id=94001101, name="Easy")

    raw, cookie = make_session(940010)
    client.cookies.set(cookie, raw)

    ok = client.get("/api/profiles/public_runner")
    assert ok.status_code == 200
    body = ok.json()
    assert body["handle"] == "public_runner"
    assert body["is_self"] is False
    assert body["is_following"] is False
    assert body["follower_count"] == 0
    assert body["stats"]["activity_count"] == 1
    assert len(body["activities"]) == 1
    flat = str(body)
    assert "access_token" not in flat
    assert "start_lat" not in flat
    assert "summary_polyline" not in flat

    assert client.get("/api/profiles/private_runner").status_code == 404
    assert client.get("/api/profiles/@public_runner").status_code == 200


def test_follow_unfollow_counts_and_self(
    client,
    make_session,
    make_athlete,
):
    make_athlete(940020, firstname="A", handle="follow_a", is_profile_public=True)
    make_athlete(940021, firstname="B", handle="follow_b", is_profile_public=True)

    raw_a, cookie = make_session(940020)
    client.cookies.set(cookie, raw_a)

    self_follow = client.post("/api/profiles/follow_a/follow")
    assert self_follow.status_code == 400

    followed = client.post("/api/profiles/follow_b/follow")
    assert followed.status_code == 200
    assert followed.json()["is_following"] is True
    assert followed.json()["follower_count"] == 1

    # Idempotent follow
    again = client.post("/api/profiles/follow_b/follow")
    assert again.status_code == 200
    assert again.json()["follower_count"] == 1

    # athlete_id in body must be ignored — session is source of truth
    sneaky = client.post(
        "/api/profiles/follow_b/follow",
        json={"athlete_id": 940021, "follower_id": 1},
    )
    assert sneaky.status_code == 200
    assert sneaky.json()["follower_count"] == 1

    followers = client.get("/api/profiles/follow_b/followers").json()
    assert followers["count"] == 1
    assert followers["people"][0]["handle"] == "follow_a"

    following = client.get("/api/profiles/follow_a/following").json()
    assert following["count"] == 1
    assert following["people"][0]["handle"] == "follow_b"

    me = client.get("/api/me/profile").json()
    assert me["following_count"] == 1

    unfollowed = client.delete("/api/profiles/follow_b/follow")
    assert unfollowed.status_code == 200
    assert unfollowed.json()["is_following"] is False
    assert unfollowed.json()["follower_count"] == 0


def test_follow_isolation_between_sessions(
    client,
    make_session,
    make_athlete,
):
    make_athlete(940030, handle="iso_a", is_profile_public=True)
    make_athlete(940031, handle="iso_b", is_profile_public=True)
    make_athlete(940032, handle="iso_c", is_profile_public=True)

    raw_a, cookie = make_session(940030)
    client.cookies.set(cookie, raw_a)
    assert client.post("/api/profiles/iso_c/follow").status_code == 200

    raw_b, cookie_b = make_session(940031)
    client.cookies.set(cookie_b, raw_b)
    profile = client.get("/api/profiles/iso_c").json()
    assert profile["follower_count"] == 1
    assert profile["is_following"] is False
    assert client.post("/api/profiles/iso_c/follow").status_code == 200
    assert client.get("/api/profiles/iso_c").json()["follower_count"] == 2
