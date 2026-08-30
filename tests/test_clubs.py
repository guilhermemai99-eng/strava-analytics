"""Run clubs — create, join, leave, club runs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _login(client, make_session, athlete_id: int):
    raw, cookie = make_session(athlete_id)
    client.cookies.set(cookie, raw)
    return raw, cookie


def _run_payload(**overrides):
    meeting = datetime.now(timezone.utc) + timedelta(days=2)
    payload = {
        "title": "Tuesday Easy Run",
        "location_name": "Foz, Porto",
        "meeting_time": meeting.replace(microsecond=0).isoformat(),
        "distance_km": 8.0,
        "pace_min": "5:15",
        "pace_max": "5:45",
        "run_type": "easy",
        "visibility": "everyone",
    }
    payload.update(overrides)
    return payload


def test_create_join_leave_club(client, make_session, make_athlete):
    make_athlete(940001, firstname="Owner", lastname="Club")
    make_athlete(940002, firstname="Member", lastname="Club")
    _login(client, make_session, 940001)

    created = client.post(
        "/api/clubs",
        json={
            "name": "Porto Sunrise Runners",
            "description": "Easy mornings by the river.",
            "location_name": "Porto",
            "visibility": "public",
        },
    )
    assert created.status_code == 200, created.text
    club = created.json()
    assert club["name"] == "Porto Sunrise Runners"
    assert club["is_owner"] is True
    assert club["member_count"] == 1
    club_id = club["id"]

    discover = client.get("/api/clubs?tab=discover")
    assert discover.status_code == 200
    assert any(item["id"] == club_id for item in discover.json()["items"])

    _login(client, make_session, 940002)
    joined = client.post(f"/api/clubs/{club_id}/join")
    assert joined.status_code == 200
    assert joined.json()["is_member"] is True
    assert joined.json()["member_count"] == 2

    members = client.get(f"/api/clubs/{club_id}/members")
    assert members.status_code == 200
    assert len(members.json()["items"]) == 2

    left = client.post(f"/api/clubs/{club_id}/leave")
    assert left.status_code == 200
    assert left.json()["is_member"] is False


def test_owner_cannot_leave(client, make_session, make_athlete):
    make_athlete(940010, firstname="Owner", lastname="Stay")
    _login(client, make_session, 940010)
    club_id = client.post(
        "/api/clubs", json={"name": "Stay Club", "visibility": "public"}
    ).json()["id"]
    leave = client.post(f"/api/clubs/{club_id}/leave")
    assert leave.status_code == 400


def test_private_club_hidden_from_non_members(client, make_session, make_athlete):
    make_athlete(940020, firstname="Owner", lastname="Private")
    make_athlete(940021, firstname="Outsider", lastname="Private")
    _login(client, make_session, 940020)
    club_id = client.post(
        "/api/clubs",
        json={"name": "Secret Miles", "visibility": "private"},
    ).json()["id"]

    _login(client, make_session, 940021)
    discover = client.get("/api/clubs?tab=discover")
    assert all(item["id"] != club_id for item in discover.json()["items"])
    detail = client.get(f"/api/clubs/{club_id}")
    assert detail.status_code == 404
    join = client.post(f"/api/clubs/{club_id}/join")
    assert join.status_code == 403


def test_club_run_hosted_by_admin(client, make_session, make_athlete):
    make_athlete(940030, firstname="Host", lastname="Club")
    make_athlete(940031, firstname="Guest", lastname="Club")
    _login(client, make_session, 940030)
    club_id = client.post(
        "/api/clubs",
        json={"name": "Porto Sunrise Runners", "visibility": "public"},
    ).json()["id"]

    created = client.post("/api/runs", json=_run_payload(club_id=club_id))
    assert created.status_code == 200, created.text
    run = created.json()
    assert run["club_id"] == club_id
    assert run["club"]["name"] == "Porto Sunrise Runners"

    upcoming = client.get(f"/api/clubs/{club_id}/runs?tab=upcoming")
    assert upcoming.status_code == 200
    assert any(item["id"] == run["id"] for item in upcoming.json()["items"])

    _login(client, make_session, 940031)
    forbidden = client.post("/api/runs", json=_run_payload(club_id=club_id, title="Nope"))
    assert forbidden.status_code == 403


def test_list_mine_and_admin_clubs(client, make_session, make_athlete):
    make_athlete(940040, firstname="Admin", lastname="List")
    make_athlete(940041, firstname="Joiner", lastname="List")
    _login(client, make_session, 940040)
    club_id = client.post(
        "/api/clubs",
        json={"name": "Foz Crew", "location_name": "Porto", "visibility": "public"},
    ).json()["id"]

    mine = client.get("/api/clubs?tab=mine")
    assert mine.status_code == 200
    assert any(item["id"] == club_id for item in mine.json()["items"])

    admin = client.get("/api/clubs?tab=admin")
    assert admin.status_code == 200
    assert any(item["id"] == club_id and item["can_manage"] for item in admin.json()["items"])

    _login(client, make_session, 940041)
    assert client.post(f"/api/clubs/{club_id}/join").status_code == 200
    mine_joiner = client.get("/api/clubs?tab=mine")
    assert any(item["id"] == club_id for item in mine_joiner.json()["items"])
    admin_joiner = client.get("/api/clubs?tab=admin")
    assert all(item["id"] != club_id for item in admin_joiner.json()["items"])


def test_transfer_promote_and_delete_club(client, make_session, make_athlete):
    make_athlete(940050, firstname="Owner", lastname="Life")
    make_athlete(940051, firstname="Next", lastname="Owner")
    make_athlete(940052, firstname="Member", lastname="Life")
    _login(client, make_session, 940050)
    club_id = client.post(
        "/api/clubs",
        json={"name": "Lifecycle Crew", "visibility": "public"},
    ).json()["id"]

    _login(client, make_session, 940051)
    assert client.post(f"/api/clubs/{club_id}/join").status_code == 200
    _login(client, make_session, 940052)
    assert client.post(f"/api/clubs/{club_id}/join").status_code == 200

    _login(client, make_session, 940050)
    promote = client.patch(
        f"/api/clubs/{club_id}/members/940052",
        json={"role": "admin"},
    )
    assert promote.status_code == 200, promote.text
    assert promote.json()["role"] == "admin"

    transfer = client.post(
        f"/api/clubs/{club_id}/transfer",
        json={"athlete_id": 940051},
    )
    assert transfer.status_code == 200, transfer.text
    body = transfer.json()
    assert body["is_owner"] is False
    assert body["role"] == "admin"

    _login(client, make_session, 940051)
    detail = client.get(f"/api/clubs/{club_id}")
    assert detail.status_code == 200
    assert detail.json()["is_owner"] is True

    notifs = client.get("/api/notifications")
    assert notifs.status_code == 200
    assert any(
        n.get("kind") == "club_ownership" and n.get("target_id") == club_id
        for n in notifs.json().get("items", [])
    )

    _login(client, make_session, 940050)
    forbidden = client.delete(f"/api/clubs/{club_id}")
    assert forbidden.status_code == 403

    _login(client, make_session, 940051)
    deleted = client.delete(f"/api/clubs/{club_id}")
    assert deleted.status_code == 200, deleted.text
    assert client.get(f"/api/clubs/{club_id}").status_code == 404


def test_non_owner_cannot_transfer_or_promote(client, make_session, make_athlete):
    make_athlete(940060, firstname="Boss", lastname="Club")
    make_athlete(940061, firstname="Joiner", lastname="Club")
    _login(client, make_session, 940060)
    club_id = client.post(
        "/api/clubs", json={"name": "No Power", "visibility": "public"}
    ).json()["id"]
    _login(client, make_session, 940061)
    assert client.post(f"/api/clubs/{club_id}/join").status_code == 200
    assert (
        client.post(
            f"/api/clubs/{club_id}/transfer", json={"athlete_id": 940061}
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/clubs/{club_id}/members/940060", json={"role": "admin"}
        ).status_code
        == 403
    )