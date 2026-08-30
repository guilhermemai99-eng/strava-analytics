"""Runs API — create, discover, join, leave, my runs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _login(client, make_session, athlete_id: int):
    raw, cookie = make_session(athlete_id)
    client.cookies.set(cookie, raw)
    return raw, cookie


def _create_run_payload(**overrides):
    meeting = datetime.now(timezone.utc) + timedelta(days=2)
    payload = {
        "title": "Sunday Long Run",
        "description": "Easy long run along the river.",
        "location_name": "Foz, Porto",
        "meeting_time": meeting.replace(microsecond=0).isoformat(),
        "distance_km": 18.0,
        "pace_min": "4:50",
        "pace_max": "5:20",
        "run_type": "long",
        "visibility": "everyone",
    }
    payload.update(overrides)
    return payload


def test_create_run_and_join(client, make_session, make_athlete):
    make_athlete(920001, firstname="Host", lastname="Runner")
    make_athlete(920002, firstname="Guest", lastname="Runner")
    _login(client, make_session, 920001)

    create = client.post("/api/runs", json=_create_run_payload())
    assert create.status_code == 200
    data = create.json()
    assert data["title"] == "Sunday Long Run"
    assert data["is_host"] is True
    assert data["is_going"] is True
    assert data["participant_count"] == 1
    run_id = data["id"]

    discover = client.get("/api/runs?tab=discover")
    assert discover.status_code == 200
    assert any(item["id"] == run_id for item in discover.json()["items"])

    _login(client, make_session, 920002)
    detail = client.get(f"/api/runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["can_join"] is True
    assert "compatibility" in detail.json()

    joined = client.post(f"/api/runs/{run_id}/join")
    assert joined.status_code == 200
    assert joined.json()["is_going"] is True
    assert joined.json()["participant_count"] == 2

    parts = client.get(f"/api/runs/{run_id}/participants")
    assert parts.status_code == 200
    assert len(parts.json()["items"]) == 2

    upcoming = client.get("/api/runs?tab=upcoming")
    assert upcoming.status_code == 200
    assert any(item["id"] == run_id for item in upcoming.json()["items"])

    left = client.post(f"/api/runs/{run_id}/leave")
    assert left.status_code == 200
    assert left.json()["is_going"] is False


def test_host_can_cancel_run(client, make_session, make_athlete):
    make_athlete(920010, firstname="Host", lastname="Only")
    _login(client, make_session, 920010)

    create = client.post("/api/runs", json=_create_run_payload(title="Tempo Tuesday"))
    run_id = create.json()["id"]

    cancel = client.delete(f"/api/runs/{run_id}")
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"

    hosting = client.get("/api/runs?tab=hosting")
    assert hosting.status_code == 200
    assert any(item["id"] == run_id for item in hosting.json()["items"])


def test_non_host_cannot_cancel(client, make_session, make_athlete):
    make_athlete(920020, firstname="Host", lastname="A")
    make_athlete(920021, firstname="Guest", lastname="B")
    _login(client, make_session, 920020)
    run_id = client.post("/api/runs", json=_create_run_payload()).json()["id"]

    _login(client, make_session, 920021)
    client.post(f"/api/runs/{run_id}/join")
    cancel = client.delete(f"/api/runs/{run_id}")
    assert cancel.status_code == 403


def test_running_profile_endpoint(client, make_session, make_athlete, make_activity):
    make_athlete(920030, firstname="Pace", lastname="Tester")
    make_activity(
        920030,
        strava_id=92003001,
        name="Easy Run",
    )
    _login(client, make_session, 920030)

    profile = client.get("/api/runs/profile")
    assert profile.status_code == 200
    body = profile.json()
    assert "easy_pace_label" in body
    assert "sample_activities" in body
