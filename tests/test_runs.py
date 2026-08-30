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


def test_cancel_notifies_goers(client, make_session, make_athlete):
    make_athlete(920012, firstname="Host", lastname="Cancel")
    make_athlete(920013, firstname="Guest", lastname="Cancel")
    _login(client, make_session, 920012)
    run_id = client.post(
        "/api/runs", json=_create_run_payload(title="Dawn Cancel")
    ).json()["id"]

    _login(client, make_session, 920013)
    assert client.post(f"/api/runs/{run_id}/join").status_code == 200

    _login(client, make_session, 920012)
    cancel = client.delete(f"/api/runs/{run_id}")
    assert cancel.status_code == 200

    _login(client, make_session, 920013)
    inbox = client.get("/api/notifications").json()
    kinds = {item["kind"] for item in inbox["items"]}
    assert "run_cancelled" in kinds
    row = next(i for i in inbox["items"] if i["kind"] == "run_cancelled")
    assert row["target_id"] == run_id
    assert "cancelled" in row["body"].lower()


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


def test_invite_only_blocks_open_join(client, make_session, make_athlete):
    make_athlete(920040, firstname="Host", lastname="Invite")
    make_athlete(920041, firstname="Out", lastname="Sider")
    _login(client, make_session, 920040)
    run_id = client.post(
        "/api/runs",
        json=_create_run_payload(visibility="invite_only", title="Secret Miles"),
    ).json()["id"]

    discover = client.get("/api/runs?tab=discover")
    assert all(item["id"] != run_id for item in discover.json()["items"])

    _login(client, make_session, 920041)
    assert client.get(f"/api/runs/{run_id}").status_code == 404
    assert client.post(f"/api/runs/{run_id}/join").status_code in (403, 404)


def test_host_invite_and_create_with_peer(client, make_session, make_athlete):
    make_athlete(920050, firstname="Host", lastname="Peer")
    make_athlete(920051, firstname="Peer", lastname="Runner")
    make_athlete(920052, firstname="Later", lastname="Invite")
    _login(client, make_session, 920050)

    created = client.post(
        "/api/runs",
        json=_create_run_payload(
            visibility="invite_only",
            title="Run with Peer",
            invite_athlete_ids=[920051],
        ),
    )
    assert created.status_code == 200, created.text
    run = created.json()
    assert run["participant_count"] == 2
    assert any(p["athlete_id"] == 920051 for p in run["participants"])
    run_id = run["id"]

    _login(client, make_session, 920051)
    detail = client.get(f"/api/runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["is_going"] is True
    inbox = client.get("/api/notifications").json()
    assert any(
        n.get("kind") == "run_invite" and n.get("target_id") == run_id
        for n in inbox["items"]
    )

    _login(client, make_session, 920050)
    invited = client.post(
        f"/api/runs/{run_id}/invite",
        json={"athlete_id": 920052},
    )
    assert invited.status_code == 200, invited.text
    assert invited.json()["participant_count"] == 3

    _login(client, make_session, 920052)
    assert client.get(f"/api/runs/{run_id}").json()["is_going"] is True


def test_non_host_cannot_invite(client, make_session, make_athlete):
    make_athlete(920060, firstname="Host", lastname="Gate")
    make_athlete(920061, firstname="Guest", lastname="Gate")
    make_athlete(920062, firstname="Target", lastname="Gate")
    _login(client, make_session, 920060)
    run_id = client.post("/api/runs", json=_create_run_payload()).json()["id"]
    _login(client, make_session, 920061)
    assert client.post(f"/api/runs/{run_id}/join").status_code == 200
    denied = client.post(
        f"/api/runs/{run_id}/invite", json={"athlete_id": 920062}
    )
    assert denied.status_code == 403
