"""Explore discovery: auth, public-only, search, nearby."""

from __future__ import annotations


def test_explore_requires_auth(client):
    assert client.get("/api/explore").status_code == 401
    assert client.get("/api/explore/search", params={"q": "run"}).status_code == 401
    assert client.get("/api/athletes/1/profile").status_code == 401
    assert client.get("/api/athletes/1/avatar").status_code == 401


def test_explore_hides_private_and_self(
    client,
    make_session,
    make_athlete,
    make_activity,
):
    make_athlete(
        930001,
        firstname="Viewer",
        lastname="One",
        city="Porto",
        country="Portugal",
        handle="viewer_one",
        is_profile_public=True,
    )
    make_athlete(
        930002,
        firstname="Public",
        lastname="Porto",
        city="Porto",
        country="Portugal",
        handle="public_porto",
        display_name="Public Porto",
        is_profile_public=True,
    )
    make_athlete(
        930003,
        firstname="Private",
        lastname="Ghost",
        city="Porto",
        country="Portugal",
        handle="private_ghost",
        is_profile_public=False,
    )
    make_athlete(
        930004,
        firstname="Lisbon",
        lastname="Legs",
        city="Lisboa",
        country="Portugal",
        handle="lisbon_legs",
        is_profile_public=True,
    )
    make_activity(930002, strava_id=93000201, name="Public Run")
    make_activity(930004, strava_id=93000401, name="Lisbon Run")

    raw, cookie = make_session(930001)
    client.cookies.set(cookie, raw)

    resp = client.get("/api/explore")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["me"]["is_profile_public"] is True
    assert payload["me"]["city"] == "Porto"

    by_section = {s["id"]: s for s in payload["sections"]}
    nearby_ids = {a["athlete_id"] for a in by_section["nearby"]["athletes"]}
    recent_ids = {a["athlete_id"] for a in by_section["recent"]["athletes"]}
    new_ids = {a["athlete_id"] for a in by_section["new"]["athletes"]}

    assert 930001 not in nearby_ids | recent_ids | new_ids
    assert 930003 not in nearby_ids | recent_ids | new_ids
    assert 930002 in nearby_ids
    assert 930002 in recent_ids
    assert 930004 in recent_ids


def test_explore_search_public_only(
    client,
    make_session,
    make_athlete,
):
    make_athlete(930010, firstname="Me", handle="search_me")
    make_athlete(
        930011,
        firstname="Visible",
        handle="mile_machine",
        display_name="Mile Machine",
        is_profile_public=True,
        city="Porto",
    )
    make_athlete(
        930012,
        firstname="Hidden",
        handle="mile_secret",
        display_name="Mile Secret",
        is_profile_public=False,
    )

    raw, cookie = make_session(930010)
    client.cookies.set(cookie, raw)

    short = client.get("/api/explore/search", params={"q": "m"})
    assert short.status_code == 200
    assert short.json()["results"] == []

    hit = client.get("/api/explore/search", params={"q": "mile"})
    assert hit.status_code == 200
    ids = [a["athlete_id"] for a in hit.json()["results"]]
    assert ids == [930011]


def test_public_profile_and_avatar_gate(
    client,
    make_session,
    make_athlete,
):
    make_athlete(930020, firstname="Viewer")
    public = make_athlete(
        930021,
        firstname="Open",
        handle="open_runner",
        is_profile_public=True,
        bio="Legs first.",
        city="Porto",
        country="Portugal",
        avatar_data=b"\xff\xd8\xff\x00fake",
        avatar_content_type="image/jpeg",
    )
    make_athlete(
        930022,
        firstname="Closed",
        handle="closed_runner",
        is_profile_public=False,
        avatar_data=b"\xff\xd8\xff\x00fake",
        avatar_content_type="image/jpeg",
    )

    raw, cookie = make_session(930020)
    client.cookies.set(cookie, raw)

    ok = client.get(f"/api/athletes/{public.id}/profile")
    assert ok.status_code == 200
    body = ok.json()
    assert body["athlete_id"] == 930021
    assert body["bio"] == "Legs first."
    assert body["avatar_url"].startswith("/api/athletes/930021/avatar")

    assert client.get("/api/athletes/930022/profile").status_code == 404
    assert client.get("/api/athletes/930022/avatar").status_code == 404

    avatar = client.get("/api/athletes/930021/avatar")
    assert avatar.status_code == 200
    assert avatar.headers["content-type"].startswith("image/jpeg")


def test_toggle_show_in_explore(
    client,
    make_session,
    make_athlete,
):
    make_athlete(930030, firstname="Toggle", city="Braga")
    make_athlete(
        930031,
        firstname="Scout",
        handle="scout_run",
        is_profile_public=True,
        city="Braga",
        country="Portugal",
    )

    raw, cookie = make_session(930030)
    client.cookies.set(cookie, raw)

    before = client.get("/api/explore").json()
    nearby_before = {
        a["athlete_id"] for a in before["sections"][0]["athletes"]
    }
    assert 930031 in nearby_before
    assert before["me"]["is_profile_public"] is False

    patched = client.patch(
        "/api/me/profile",
        json={
            "is_profile_public": True,
            "city": "Braga",
            "country": "Portugal",
            "handle": "toggle_run",
        },
    )
    assert patched.status_code == 200
    assert patched.json()["is_profile_public"] is True
    assert patched.json()["location"]["city"] == "Braga"

    # Other viewer should now see 930030 in explore.
    raw_b, cookie_b = make_session(930031)
    client.cookies.set(cookie_b, raw_b)
    after = client.get("/api/explore").json()
    new_ids = {a["athlete_id"] for a in after["sections"][2]["athletes"]}
    nearby_ids = {a["athlete_id"] for a in after["sections"][0]["athletes"]}
    assert 930030 in new_ids | nearby_ids


def test_explore_cookie_isolation(client, make_session, make_athlete):
    make_athlete(
        930040,
        firstname="A",
        handle="explore_a",
        is_profile_public=True,
        city="Porto",
    )
    make_athlete(
        930041,
        firstname="B",
        handle="explore_b",
        is_profile_public=True,
        city="Porto",
    )

    raw_a, cookie = make_session(930040)
    client.cookies.set(cookie, raw_a)
    data_a = client.get("/api/explore").json()
    ids_a = {
        a["athlete_id"]
        for s in data_a["sections"]
        for a in s["athletes"]
    }
    assert 930040 not in ids_a
    assert 930041 in ids_a
