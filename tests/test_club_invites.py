"""Club covers and invites."""

from __future__ import annotations

import io

from PIL import Image


def _login(client, make_session, athlete_id: int):
    raw, cookie = make_session(athlete_id)
    client.cookies.set(cookie, raw)
    return raw, cookie


def _jpeg_bytes(color=(40, 180, 90)) -> bytes:
    img = Image.new("RGB", (120, 120), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def test_club_cover_upload_and_serve(client, make_session, make_athlete):
    make_athlete(941100, firstname="Cover", lastname="Owner", handle="cover_owner")
    make_athlete(941101, firstname="Cover", lastname="Guest", handle="cover_guest")
    _login(client, make_session, 941100)
    club_id = client.post(
        "/api/clubs",
        json={"name": "Cover Club", "visibility": "public"},
    ).json()["id"]

    upload = client.post(
        f"/api/clubs/{club_id}/cover",
        files={"file": ("cover.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert upload.status_code == 200, upload.text
    body = upload.json()
    assert body["cover_url"]
    assert f"/api/clubs/{club_id}/cover" in body["cover_url"]

    served = client.get(body["cover_url"].split("?", 1)[0])
    assert served.status_code == 200
    assert served.headers["content-type"].startswith("image/")
    assert len(served.content) > 32

    _login(client, make_session, 941101)
    assert client.post(
        f"/api/clubs/{club_id}/cover",
        files={"file": ("nope.jpg", _jpeg_bytes((200, 40, 40)), "image/jpeg")},
    ).status_code == 403

    _login(client, make_session, 941100)
    deleted = client.delete(f"/api/clubs/{club_id}/cover")
    assert deleted.status_code == 200
    assert deleted.json()["cover_url"] is None


def test_direct_invite_private_club(client, make_session, make_athlete):
    make_athlete(941110, firstname="Owner", lastname="Inv", handle="inv_owner")
    make_athlete(941111, firstname="Guest", lastname="Inv", handle="inv_guest")
    _login(client, make_session, 941110)
    club_id = client.post(
        "/api/clubs",
        json={"name": "Private Pace", "visibility": "private"},
    ).json()["id"]

    _login(client, make_session, 941111)
    assert client.post(f"/api/clubs/{club_id}/join").status_code == 403
    assert client.get(f"/api/clubs/{club_id}").status_code == 404

    _login(client, make_session, 941110)
    invited = client.post(
        f"/api/clubs/{club_id}/invites",
        json={"handle": "inv_guest"},
    )
    assert invited.status_code == 200, invited.text
    invite_id = invited.json()["id"]

    _login(client, make_session, 941111)
    inbox = client.get("/api/notifications").json()
    assert any(i["kind"] == "club_invite" for i in inbox["items"])
    incoming = client.get("/api/club-invites").json()["items"]
    assert any(i["id"] == invite_id for i in incoming)

    accepted = client.post(f"/api/club-invites/{invite_id}/accept")
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["is_member"] is True
    assert accepted.json()["member_count"] == 2

    detail = client.get(f"/api/clubs/{club_id}")
    assert detail.status_code == 200


def test_invite_link_redeems_into_private_club(
    client, make_session, make_athlete
):
    make_athlete(941120, firstname="Link", lastname="Owner", handle="link_owner")
    make_athlete(941121, firstname="Link", lastname="Guest", handle="link_guest")
    _login(client, make_session, 941120)
    club_id = client.post(
        "/api/clubs",
        json={"name": "Link Only Club", "visibility": "private"},
    ).json()["id"]

    link = client.post(f"/api/clubs/{club_id}/invite-link")
    assert link.status_code == 200, link.text
    token = link.json()["token"]
    assert "club_invite=" in link.json()["path"]

    _login(client, make_session, 941121)
    redeemed = client.post(
        "/api/club-invites/redeem", json={"token": token}
    )
    assert redeemed.status_code == 200, redeemed.text
    assert redeemed.json()["is_member"] is True
    assert redeemed.json()["id"] == club_id

    # Idempotent re-redeem
    again = client.post("/api/club-invites/redeem", json={"token": token})
    assert again.status_code == 200
    assert again.json()["is_member"] is True


def test_decline_and_cancel_invite(client, make_session, make_athlete):
    make_athlete(941130, firstname="Own", lastname="Dec", handle="dec_owner")
    make_athlete(941131, firstname="Gue", lastname="Dec", handle="dec_guest")
    make_athlete(941132, firstname="Gue2", lastname="Dec", handle="dec_guest2")
    _login(client, make_session, 941130)
    club_id = client.post(
        "/api/clubs",
        json={"name": "Decline Club", "visibility": "public"},
    ).json()["id"]

    inv1 = client.post(
        f"/api/clubs/{club_id}/invites", json={"handle": "dec_guest"}
    ).json()["id"]
    inv2 = client.post(
        f"/api/clubs/{club_id}/invites", json={"handle": "dec_guest2"}
    ).json()["id"]

    cancel = client.post(f"/api/clubs/{club_id}/invites/{inv2}/cancel")
    assert cancel.status_code == 200

    _login(client, make_session, 941131)
    declined = client.post(f"/api/club-invites/{inv1}/decline")
    assert declined.status_code == 200
    assert client.get("/api/club-invites").json()["items"] == []
