"""Notification API and follow/message triggers."""

from __future__ import annotations

from follow_helpers import create_follow
from notification_helpers import (
    list_notifications,
    mark_all_read,
    notify_follow,
    unread_count,
)


def test_notifications_require_auth(client):
    assert client.get("/api/notifications").status_code == 401
    assert client.get("/api/notifications/unread-count").status_code == 401
    assert client.post("/api/notifications/read").status_code == 401


def test_follow_creates_notification(
    client, make_session, make_athlete, db_session
):
    make_athlete(981001, handle="notif_a")
    make_athlete(981002, handle="notif_b", is_profile_public=True)
    raw_a, cookie_a = make_session(981001)
    raw_b, cookie_b = make_session(981002)

    resp = client.post(
        "/api/users/981002/follow",
        cookies={cookie_a: raw_a},
    )
    assert resp.status_code == 200

    inbox = client.get(
        "/api/notifications",
        cookies={cookie_b: raw_b},
    )
    assert inbox.status_code == 200
    data = inbox.json()
    assert data["unread_total"] >= 1
    kinds = {item["kind"] for item in data["items"]}
    assert "follow" in kinds


def test_mark_notifications_read(
    client, make_session, make_athlete, db_session
):
    make_athlete(981011, handle="read_a")
    make_athlete(981012, handle="read_b", is_profile_public=True)
    raw_a, cookie_a = make_session(981011)
    raw_b, cookie_b = make_session(981012)

    client.post("/api/users/981012/follow", cookies={cookie_a: raw_a})

    before = client.get(
        "/api/notifications/unread-count",
        cookies={cookie_b: raw_b},
    ).json()["unread_total"]
    assert before >= 1

    client.post("/api/notifications/read", cookies={cookie_b: raw_b})
    after = client.get(
        "/api/notifications/unread-count",
        cookies={cookie_b: raw_b},
    ).json()["unread_total"]
    assert after == 0


def test_run_join_notifies_host(client, make_session, make_athlete):
    from datetime import datetime, timedelta, timezone

    make_athlete(981020, handle="host_run", firstname="Host")
    make_athlete(981021, handle="guest_run", firstname="Guest")
    raw_h, cookie_h = make_session(981020)
    raw_g, cookie_g = make_session(981021)

    meeting = datetime.now(timezone.utc) + timedelta(days=2)
    created = client.post(
        "/api/runs",
        cookies={cookie_h: raw_h},
        json={
            "title": "Sunrise Easy",
            "location_name": "Foz",
            "meeting_time": meeting.replace(microsecond=0).isoformat(),
            "distance_km": 8,
            "visibility": "everyone",
        },
    )
    assert created.status_code == 200
    run_id = created.json()["id"]

    joined = client.post(
        f"/api/runs/{run_id}/join", cookies={cookie_g: raw_g}
    )
    assert joined.status_code == 200

    inbox = client.get("/api/notifications", cookies={cookie_h: raw_h}).json()
    kinds = {item["kind"] for item in inbox["items"]}
    assert "run_join" in kinds
    row = next(i for i in inbox["items"] if i["kind"] == "run_join")
    assert row["target_type"] == "run"
    assert row["target_id"] == run_id
    assert "joined" in row["body"].lower()

    # Rejoining while already going must not spam another notification.
    before = inbox["unread_total"]
    client.post(f"/api/runs/{run_id}/join", cookies={cookie_g: raw_g})
    after = client.get(
        "/api/notifications/unread-count", cookies={cookie_h: raw_h}
    ).json()["unread_total"]
    assert after == before


def test_run_leave_notifies_host(client, make_session, make_athlete):
    from datetime import datetime, timedelta, timezone

    make_athlete(981030, handle="host_leave", firstname="Host")
    make_athlete(981031, handle="guest_leave", firstname="Guest")
    raw_h, cookie_h = make_session(981030)
    raw_g, cookie_g = make_session(981031)

    meeting = datetime.now(timezone.utc) + timedelta(days=2)
    created = client.post(
        "/api/runs",
        cookies={cookie_h: raw_h},
        json={
            "title": "Leave Test Run",
            "location_name": "Foz",
            "meeting_time": meeting.replace(microsecond=0).isoformat(),
            "distance_km": 8,
            "visibility": "everyone",
        },
    )
    assert created.status_code == 200
    run_id = created.json()["id"]

    assert client.post(f"/api/runs/{run_id}/join", cookies={cookie_g: raw_g}).status_code == 200
    assert client.post(f"/api/runs/{run_id}/leave", cookies={cookie_g: raw_g}).status_code == 200

    inbox = client.get("/api/notifications", cookies={cookie_h: raw_h}).json()
    row = next((i for i in inbox["items"] if i["kind"] == "run_leave"), None)
    assert row is not None
    assert row["target_id"] == run_id
    assert "left" in row["body"].lower()


def test_club_join_and_club_run_notify(client, make_session, make_athlete):
    from datetime import datetime, timedelta, timezone

    make_athlete(981030, handle="club_owner", firstname="Owner")
    make_athlete(981031, handle="club_member", firstname="Member")
    raw_o, cookie_o = make_session(981030)
    raw_m, cookie_m = make_session(981031)

    club = client.post(
        "/api/clubs",
        cookies={cookie_o: raw_o},
        json={"name": "Foz Crew", "visibility": "public"},
    )
    assert club.status_code == 200
    club_id = club.json()["id"]

    joined = client.post(
        f"/api/clubs/{club_id}/join", cookies={cookie_m: raw_m}
    )
    assert joined.status_code == 200

    owner_inbox = client.get(
        "/api/notifications", cookies={cookie_o: raw_o}
    ).json()
    assert "club_join" in {i["kind"] for i in owner_inbox["items"]}
    join_row = next(i for i in owner_inbox["items"] if i["kind"] == "club_join")
    assert join_row["target_type"] == "club"
    assert join_row["target_id"] == club_id

    meeting = datetime.now(timezone.utc) + timedelta(days=3)
    run = client.post(
        "/api/runs",
        cookies={cookie_o: raw_o},
        json={
            "title": "Club Tempo",
            "location_name": "Foz",
            "meeting_time": meeting.replace(microsecond=0).isoformat(),
            "distance_km": 10,
            "visibility": "everyone",
            "club_id": club_id,
        },
    )
    assert run.status_code == 200
    run_id = run.json()["id"]

    member_inbox = client.get(
        "/api/notifications", cookies={cookie_m: raw_m}
    ).json()
    assert "club_run" in {i["kind"] for i in member_inbox["items"]}
    run_row = next(i for i in member_inbox["items"] if i["kind"] == "club_run")
    assert run_row["target_type"] == "run"
    assert run_row["target_id"] == run_id
