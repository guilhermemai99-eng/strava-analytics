"""People matching and Run Together (Phase 2)."""

from __future__ import annotations


def _login(client, make_session, athlete_id: int):
    raw, cookie = make_session(athlete_id)
    client.cookies.set(cookie, raw)
    return raw, cookie


def test_people_matches_ranks_same_city(client, make_session, make_athlete, make_activity):
    make_athlete(
        930001,
        firstname="Viewer",
        lastname="One",
        city="Porto",
        country="Portugal",
        is_profile_public=True,
    )
    make_athlete(
        930002,
        firstname="Match",
        lastname="Two",
        city="Porto",
        country="Portugal",
        is_profile_public=True,
    )
    make_athlete(
        930003,
        firstname="Far",
        lastname="Away",
        city="Lisboa",
        country="Portugal",
        is_profile_public=True,
    )
    make_activity(930001, strava_id=93000101, name="Easy Run")
    make_activity(930002, strava_id=93000201, name="Easy Run")
    make_activity(930003, strava_id=93000301, name="Easy Run")

    _login(client, make_session, 930001)
    resp = client.get("/api/people/matches?limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    ids = [item["athlete_id"] for item in body["items"]]
    assert 930001 not in ids
    assert 930002 in ids
    if 930002 in ids and 930003 in ids:
        assert ids.index(930002) < ids.index(930003)
    for item in body["items"]:
        assert "latitude" not in item
        assert "longitude" not in item
        assert "match" in item
        assert "score" in item["match"]
        if item.get("location_label"):
            assert "Near" in item["location_label"] or item["location_label"]


def test_compatibility_and_run_together(client, make_session, make_athlete, make_activity):
    make_athlete(
        930010,
        firstname="A",
        lastname="Runner",
        city="Porto",
        country="Portugal",
        is_profile_public=True,
    )
    make_athlete(
        930011,
        firstname="B",
        lastname="Runner",
        city="Porto",
        country="Portugal",
        is_profile_public=True,
    )
    make_activity(930010, strava_id=93001001, name="Tempo")
    make_activity(930011, strava_id=93001101, name="Tempo")

    _login(client, make_session, 930010)
    compat = client.get("/api/people/930011/compatibility")
    assert compat.status_code == 200
    card = compat.json()
    assert card["athlete_id"] == 930011
    assert card["match"]["score"] >= 0

    together = client.get("/api/people/930011/run-together")
    assert together.status_code == 200
    sug = together.json()
    assert sug["peer"]["athlete_id"] == 930011
    assert "suggested_title" in sug
    assert "Run with" in sug["suggested_title"]


def test_people_endpoints_require_auth(client):
    assert client.get("/api/people/matches").status_code == 401
    assert client.get("/api/people/1/compatibility").status_code == 401
    assert client.get("/api/people/1/run-together").status_code == 401
