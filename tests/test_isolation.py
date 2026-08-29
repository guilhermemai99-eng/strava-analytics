"""Cross-athlete isolation on activities and summary."""

from __future__ import annotations


def test_athlete_cannot_read_other_activities(
    client,
    make_session,
    make_activity,
):
    make_activity(740001, strava_id=19900000001, name="A run")
    make_activity(740002, strava_id=19900000002, name="B run")

    raw_a, cookie = make_session(740001)
    client.cookies.set(cookie, raw_a)

    resp = client.get("/activities")
    assert resp.status_code == 200
    payload = resp.json()
    names = {item["name"] for item in payload}
    assert "A run" in names
    assert "B run" not in names
    assert all(item["athlete_id"] == 740001 for item in payload)


def test_summary_is_scoped_to_session_athlete(
    client,
    make_session,
    make_activity,
):
    make_activity(740011, strava_id=19900000011, name="A1")
    make_activity(740011, strava_id=19900000012, name="A2")
    make_activity(740012, strava_id=19900000013, name="B1")

    raw_a, cookie = make_session(740011)
    client.cookies.set(cookie, raw_a)

    summary = client.get("/analytics/summary")
    assert summary.status_code == 200
    data = summary.json()
    assert data.get("error") is None
    # summary should reflect only athlete 740011's two activities
    assert data["total_activities"] == 2
