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
