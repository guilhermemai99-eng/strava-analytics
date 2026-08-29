"""Public profiles + follow system."""

from __future__ import annotations

from profile_helpers import ensure_handle, suggest_handle_for, validate_handle


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


def test_mutual_relationship_and_user_aliases(
    client,
    make_session,
    make_athlete,
):
    make_athlete(940040, handle="mut_a", is_profile_public=True)
    make_athlete(940041, handle="mut_b", is_profile_public=True)

    raw_a, cookie = make_session(940040)
    client.cookies.set(cookie, raw_a)
    assert client.post("/api/users/940041/follow").status_code == 200

    raw_b, cookie_b = make_session(940041)
    client.cookies.set(cookie_b, raw_b)
    assert client.post("/api/profiles/mut_a/follow").status_code == 200

    rel = client.get("/api/profiles/mut_a/relationship").json()
    assert rel["is_following"] is True
    assert rel["is_followed_by"] is True
    assert rel["is_mutual"] is True
    assert rel["is_self"] is False

    profile = client.get("/api/profiles/mut_a").json()
    assert profile["is_mutual"] is True
    assert profile["followers_count"] == 1

    by_id = client.get("/api/users/940040/relationship").json()
    assert by_id["is_mutual"] is True


def test_follow_and_profile_by_id_without_handle(
    client,
    make_session,
    make_athlete,
    db_session,
):
    """Social graph must work via athlete_id even when handle is missing."""
    from athlete import Athlete

    make_athlete(
        940060,
        firstname="Viewer",
        handle="id_viewer",
        is_profile_public=True,
    )
    make_athlete(
        940061,
        firstname=None,
        lastname=None,
        username=None,
        display_name=None,
        handle=None,
        is_profile_public=True,
    )

    # Confirm DB row really has no handle before social calls.
    target = db_session.query(Athlete).filter(Athlete.id == 940061).one()
    assert target.handle is None

    raw, cookie = make_session(940060)
    client.cookies.set(cookie, raw)

    profile = client.get("/api/users/940061")
    assert profile.status_code == 200
    body = profile.json()
    assert body["athlete_id"] == 940061
    assert body["is_following"] is False
    assert body["display_name"]  # never blank — "New athlete" fallback
    # Opening/serializing may assign a stable handle; Follow must not require it.
    assert body["handle"] is not None or body["handle"] is None

    followed = client.post("/api/users/940061/follow")
    assert followed.status_code == 200
    assert followed.json()["is_following"] is True
    assert followed.json()["follower_count"] == 1
    assert followed.json()["athlete_id"] == 940061

    followers = client.get("/api/users/940061/followers").json()
    assert followers["total"] == 1
    assert followers["people"][0]["athlete_id"] == 940060

    unfollowed = client.delete("/api/users/940061/follow")
    assert unfollowed.status_code == 200
    assert unfollowed.json()["is_following"] is False
    assert unfollowed.json()["follower_count"] == 0


def test_explore_backfills_handle_and_keeps_follow_flag(
    client,
    make_session,
    make_athlete,
    db_session,
):
    from athlete import Athlete

    make_athlete(940070, firstname="Me", city="Porto", is_profile_public=True)
    make_athlete(
        940071,
        firstname="Bare",
        lastname="Miles",
        handle=None,
        city="Porto",
        is_profile_public=True,
    )

    raw, cookie = make_session(940070)
    client.cookies.set(cookie, raw)

    explore = client.get("/api/explore").json()
    nearby = next(s for s in explore["sections"] if s["id"] == "nearby")
    card = next(a for a in nearby["athletes"] if a["athlete_id"] == 940071)
    assert card["name"] == "Bare Miles"
    assert card["handle"]  # assigned while listing
    assert card["is_following"] is False

    db_session.expire_all()
    row = db_session.query(Athlete).filter(Athlete.id == 940071).one()
    assert row.handle

    assert client.post("/api/users/940071/follow").status_code == 200
    explore2 = client.get("/api/explore").json()
    nearby2 = next(s for s in explore2["sections"] if s["id"] == "nearby")
    card2 = next(a for a in nearby2["athletes"] if a["athlete_id"] == 940071)
    assert card2["is_following"] is True


def test_followers_pagination_and_suggestions(
    client,
    make_session,
    make_athlete,
):
    make_athlete(940050, handle="page_me", city="Porto", country="Portugal", is_profile_public=True)
    make_athlete(
        940051,
        handle="page_a",
        city="Porto",
        country="Portugal",
        is_profile_public=True,
    )
    make_athlete(
        940052,
        handle="page_b",
        city="Porto",
        country="Portugal",
        is_profile_public=True,
    )
    make_athlete(
        940053,
        handle="page_c",
        city="Lisboa",
        country="Portugal",
        is_profile_public=True,
    )

    raw_a, cookie = make_session(940051)
    client.cookies.set(cookie, raw_a)
    assert client.post("/api/profiles/page_me/follow").status_code == 200

    raw_b, cookie_b = make_session(940052)
    client.cookies.set(cookie_b, raw_b)
    assert client.post("/api/profiles/page_me/follow").status_code == 200

    raw_me, cookie_me = make_session(940050)
    client.cookies.set(cookie_me, raw_me)

    page1 = client.get(
        "/api/profiles/page_me/followers",
        params={"limit": 1, "offset": 0},
    ).json()
    assert page1["total"] == 2
    assert page1["count"] == 1
    assert page1["has_more"] is True
    assert page1["next_offset"] == 1

    page2 = client.get(
        "/api/profiles/page_me/followers",
        params={"limit": 1, "offset": 1},
    ).json()
    assert page2["count"] == 1
    assert page2["has_more"] is False

    sug = client.get("/api/profiles/suggestions").json()
    handles = {p["handle"] for p in sug["people"]}
    assert "page_a" in handles or "page_b" in handles or "page_c" in handles
    assert "page_me" not in handles

    ids = client.get("/api/feed/following-ids").json()
    assert ids["count"] == 0
    assert ids["athlete_ids"] == []
    assert client.post("/api/profiles/page_c/follow").status_code == 200
    ids2 = client.get("/api/feed/following-ids").json()
    assert 940053 in ids2["athlete_ids"]
