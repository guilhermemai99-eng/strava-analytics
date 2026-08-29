"""Pulse activity feed: auth, isolation, titles, media fallbacks."""

from __future__ import annotations

from feed_titles import pulse_title_for_activity
from models import Activity


SENSITIVE_KEYS = {
    "access_token",
    "refresh_token",
    "start_lat",
    "start_lng",
    "end_lat",
    "end_lng",
    "TOKEN_ENCRYPTION_KEY",
}


def _flatten_keys(obj, acc=None):
    if acc is None:
        acc = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            acc.add(key)
            _flatten_keys(value, acc)
    elif isinstance(obj, list):
        for item in obj:
            _flatten_keys(item, acc)
    return acc


def test_feed_requires_auth(client):
    assert client.get("/api/feed").status_code == 401


def test_feed_returns_own_activities_only(
    client,
    make_session,
    make_athlete,
    make_activity,
    db_session,
):
    make_athlete(920001, firstname="Feed", lastname="Owner", city="Porto", country="Portugal")
    make_athlete(920002, firstname="Other", lastname="Runner")
    make_activity(920001, strava_id=92000101, name="Morning Run")
    make_activity(920002, strava_id=92000201, name="Should Not Appear")

    raw, cookie = make_session(920001)
    client.cookies.set(cookie, raw)

    resp = client.get("/api/feed")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["scope"] == "self"
    assert payload["count"] == 1
    assert payload["message"]["eyebrow"]
    item = payload["items"][0]
    assert item["kind"] == "activity"
    assert item["author"]["athlete_id"] == 920001
    assert item["author"]["name"] == "Feed Owner"
    assert item["activity"]["original_name"] == "Morning Run"
    assert item["activity"]["title"]
    assert item["location"]["display_name"] == "Porto, Portugal"
    assert "start_lat" not in _flatten_keys(payload)
    assert SENSITIVE_KEYS.isdisjoint(_flatten_keys(payload))


def test_feed_title_is_deterministic():
    a = pulse_title_for_activity(
        42,
        distance_m=12000,
        moving_time_s=3600,
        name="Morning Run",
        sport_type="Run",
    )
    b = pulse_title_for_activity(
        42,
        distance_m=12000,
        moving_time_s=3600,
        name="Morning Run",
        sport_type="Run",
    )
    c = pulse_title_for_activity(
        43,
        distance_m=12000,
        moving_time_s=3600,
        name="Morning Run",
        sport_type="Run",
    )
    assert a == b
    assert a  # non-empty
    # Different ids may collide rarely; just ensure function returns str.
    assert isinstance(c, str)


def test_feed_photo_and_map_fallback_fields(
    client,
    make_session,
    make_athlete,
    db_session,
):
    make_athlete(920010, firstname="Media", lastname="Runner")
    with_photo = Activity(
        athlete_id=920010,
        strava_id=92001001,
        name="Photo Run",
        sport_type="Run",
        distance_m=8000,
        moving_time_s=2400,
        start_date_local="2026-08-10T07:00:00Z",
        photo_url="https://example.com/photo.jpg",
        photo_count=2,
        summary_polyline=None,
        start_lat=41.15,
        start_lng=-8.61,
    )
    with_map = Activity(
        athlete_id=920010,
        strava_id=92001002,
        name="Map Run",
        sport_type="Run",
        distance_m=5000,
        moving_time_s=1500,
        start_date_local="2026-08-09T07:00:00Z",
        photo_url=None,
        summary_polyline="_p~iF~ps|U_ulLnnqC_mqNvxq`@",
    )
    db_session.add_all([with_photo, with_map])
    db_session.commit()

    raw, cookie = make_session(920010)
    client.cookies.set(cookie, raw)
    resp = client.get("/api/feed")
    assert resp.status_code == 200
    items = {i["activity"]["original_name"]: i for i in resp.json()["items"]}

    photo_item = items["Photo Run"]
    assert photo_item["media"]["has_photo"] is True
    assert photo_item["media"]["primary_image_url"] == "https://example.com/photo.jpg"
    assert photo_item["media"]["has_map"] is False

    map_item = items["Map Run"]
    assert map_item["media"]["has_photo"] is False
    assert map_item["media"]["has_map"] is True
    assert map_item["media"]["summary_polyline"]
    assert "start_lat" not in _flatten_keys(resp.json())
