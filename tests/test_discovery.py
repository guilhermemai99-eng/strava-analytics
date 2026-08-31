"""Discovery swipe, match, and preferences API."""

from __future__ import annotations


def _login(client, make_session, athlete_id: int):
    raw, cookie = make_session(athlete_id)
    client.cookies.set(cookie, raw)
    return raw, cookie


def test_discovery_next_and_swipe_match(client, make_session, make_athlete, make_activity):
    make_athlete(
        940001,
        firstname="Alice",
        lastname="Runner",
        city="Porto",
        country="Portugal",
        is_profile_public=True,
    )
    make_athlete(
        940002,
        firstname="Bob",
        lastname="Runner",
        city="Porto",
        country="Portugal",
        is_profile_public=True,
    )
    make_activity(940001, strava_id=94000101, name="Easy Run")
    make_activity(940002, strava_id=94000201, name="Easy Run")

    _login(client, make_session, 940001)
    next_resp = client.get("/api/discovery/next")
    assert next_resp.status_code == 200
    body = next_resp.json()
    assert body.get("person") is not None
    assert body["person"]["athlete_id"] == 940002
    assert "latitude" not in body["person"]
    assert "longitude" not in body["person"]

    like_a_first = client.post(
        "/api/discovery/swipe",
        json={"target_id": 940002, "action": "like"},
    )
    assert like_a_first.status_code == 200
    assert like_a_first.json()["is_match"] is False

    _login(client, make_session, 940002)
    like_b = client.post(
        "/api/discovery/swipe",
        json={"target_id": 940001, "action": "like"},
    )
    assert like_b.status_code == 200
    data = like_b.json()
    assert data["is_match"] is True
    assert data["match"]["person"]["athlete_id"] == 940001

    matches = client.get("/api/discovery/matches")
    assert matches.status_code == 200
    assert matches.json()["count"] >= 1


def test_discovery_pass(client, make_session, make_athlete):
    make_athlete(
        940003,
        firstname="C",
        lastname="One",
        city="Braga",
        country="Portugal",
        is_profile_public=True,
    )
    make_athlete(
        940004,
        firstname="D",
        lastname="Two",
        city="Braga",
        country="Portugal",
        is_profile_public=True,
    )
    _login(client, make_session, 940003)
    nxt = client.get("/api/discovery/next").json()
    assert nxt.get("person")
    tid = nxt["person"]["athlete_id"]
    resp = client.post(
        "/api/discovery/swipe",
        json={"target_id": tid, "action": "pass"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_match"] is False


def test_discovery_preferences(client, make_session, make_athlete):
    make_athlete(940010, firstname="Pref", lastname="User", is_profile_public=True)
    _login(client, make_session, 940010)

    get_resp = client.get("/api/discovery/preferences")
    assert get_resp.status_code == 200
    assert get_resp.json()["radius_km"] == 25

    put_resp = client.put(
        "/api/discovery/preferences",
        json={
            "radius_km": 10,
            "manual_city": "Leiria",
            "discovery_bio": "Looking for easy 10k runs",
        },
    )
    assert put_resp.status_code == 200
    prefs = put_resp.json()
    assert prefs["radius_km"] == 10
    assert prefs["manual_city"] == "Leiria"
    assert prefs["discovery_bio"] == "Looking for easy 10k runs"
    assert "private_lat" not in prefs


def test_discovery_endpoints_require_auth(client):
    assert client.get("/api/discovery/next").status_code == 401
    assert (
        client.post(
            "/api/discovery/swipe", json={"target_id": 1, "action": "like"}
        ).status_code
        == 401
    )
    assert client.get("/api/discovery/preferences").status_code == 401
