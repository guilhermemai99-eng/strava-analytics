"""Direct messages: mutual-follow gate, isolation, read-only after unfollow."""

from __future__ import annotations

from follow_helpers import create_follow, delete_follow
from models import Activity  # noqa: F401 — ensure models registered


def _login(client, make_session, athlete_id: int):
    raw, cookie = make_session(athlete_id)
    client.cookies.set(cookie, raw)
    return raw, cookie


def test_dms_require_auth(client):
    assert client.get("/api/dms").status_code == 401
    assert client.post("/api/dms/with/1").status_code == 401
    assert client.get("/api/dms/1").status_code == 401
    assert client.get("/api/dms/1/messages").status_code == 401
    assert client.post("/api/dms/1/messages", json={"content": "hi"}).status_code == 401


def test_unilateral_follow_blocks_chat(
    client, make_session, make_athlete, db_session
):
    make_athlete(970001, firstname="A", handle="dm_a", is_profile_public=True)
    make_athlete(970002, firstname="B", handle="dm_b", is_profile_public=True)
    create_follow(db_session, follower_id=970001, following_id=970002)

    _login(client, make_session, 970001)
    resp = client.post("/api/dms/with/970002")
    assert resp.status_code == 403
    assert "follow" in resp.json()["detail"].lower()


def test_mutual_follow_allows_chat_and_dedupes(
    client, make_session, make_athlete, db_session
):
    make_athlete(970010, firstname="MutualA", handle="dm_ma", is_profile_public=True)
    make_athlete(970011, firstname="MutualB", handle="dm_mb", is_profile_public=True)
    create_follow(db_session, follower_id=970010, following_id=970011)
    create_follow(db_session, follower_id=970011, following_id=970010)

    _login(client, make_session, 970010)
    first = client.post("/api/dms/with/970011")
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["can_send"] is True
    assert body["peer"]["athlete_id"] == 970011
    conv_id = body["id"]

    second = client.post("/api/dms/with/970011")
    assert second.status_code == 200
    assert second.json()["id"] == conv_id

    sent = client.post(
        f"/api/dms/{conv_id}/messages",
        json={"content": "Morning miles?"},
    )
    assert sent.status_code == 200, sent.text
    assert sent.json()["content"] == "Morning miles?"
    assert sent.json()["is_mine"] is True

    # Peer sees inbox + unread
    _login(client, make_session, 970011)
    inbox = client.get("/api/dms")
    assert inbox.status_code == 200
    items = inbox.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == conv_id
    assert items[0]["unread_count"] >= 1
    assert items[0]["last_message"]["content"] == "Morning miles?"

    thread = client.get(f"/api/dms/{conv_id}/messages")
    assert thread.status_code == 200
    msgs = thread.json()["messages"]
    assert len(msgs) == 1
    assert msgs[0]["is_mine"] is False

    read = client.post(f"/api/dms/{conv_id}/read")
    assert read.status_code == 200
    inbox2 = client.get("/api/dms").json()["items"][0]
    assert inbox2["unread_count"] == 0


def test_outsider_cannot_access_thread(
    client, make_session, make_athlete, db_session
):
    make_athlete(970020, firstname="X", handle="dm_x", is_profile_public=True)
    make_athlete(970021, firstname="Y", handle="dm_y", is_profile_public=True)
    make_athlete(970022, firstname="Z", handle="dm_z", is_profile_public=True)
    create_follow(db_session, follower_id=970020, following_id=970021)
    create_follow(db_session, follower_id=970021, following_id=970020)

    _login(client, make_session, 970020)
    conv_id = client.post("/api/dms/with/970021").json()["id"]
    client.post(f"/api/dms/{conv_id}/messages", json={"content": "secret"})

    _login(client, make_session, 970022)
    assert client.get(f"/api/dms/{conv_id}").status_code == 404
    assert client.get(f"/api/dms/{conv_id}/messages").status_code == 404
    assert (
        client.post(
            f"/api/dms/{conv_id}/messages", json={"content": "intrude"}
        ).status_code
        == 404
    )


def test_unfollow_blocks_send_keeps_history(
    client, make_session, make_athlete, db_session
):
    make_athlete(970030, firstname="KeepA", handle="dm_ka", is_profile_public=True)
    make_athlete(970031, firstname="KeepB", handle="dm_kb", is_profile_public=True)
    create_follow(db_session, follower_id=970030, following_id=970031)
    create_follow(db_session, follower_id=970031, following_id=970030)

    _login(client, make_session, 970030)
    conv_id = client.post("/api/dms/with/970031").json()["id"]
    client.post(f"/api/dms/{conv_id}/messages", json={"content": "before unfollow"})

    delete_follow(db_session, follower_id=970030, following_id=970031)

    blocked = client.post(
        f"/api/dms/{conv_id}/messages", json={"content": "after unfollow"}
    )
    assert blocked.status_code == 403

    # History still readable
    hist = client.get(f"/api/dms/{conv_id}/messages")
    assert hist.status_code == 200
    assert hist.json()["conversation"]["can_send"] is False
    assert len(hist.json()["messages"]) == 1

    # Cannot create a new conversation either
    assert client.post("/api/dms/with/970031").status_code == 403
