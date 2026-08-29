"""Profile & settings API tests."""

from __future__ import annotations

import io

from athlete import Athlete
from session_helpers import SESSION_COOKIE_NAME


def test_profile_requires_auth(client):
    assert client.get("/api/me/profile").status_code == 401
    assert client.patch("/api/me/profile", json={"display_name": "X"}).status_code == 401
    assert client.post(
        "/api/me/avatar",
        files={"file": ("a.jpg", b"\xff\xd8\xff\x00", "image/jpeg")},
    ).status_code == 401
    assert client.delete("/api/me/avatar").status_code == 401


def test_get_own_profile(client, make_session, make_athlete, db_session):
    make_athlete(810001, firstname="Guilherme", lastname="Campos")
    raw, cookie = make_session(810001)
    client.cookies.set(cookie, raw)

    resp = client.get("/api/me/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["athlete_id"] == 810001
    assert data["display_name"] == "Guilherme Campos"
    assert data["initials"] == "GC"
    assert data["handle"] == "guilherme_campos"
    assert data["follower_count"] == 0
    assert data["following_count"] == 0
    assert data["has_custom_avatar"] is False
    assert data["strava"]["connected"] is True
    assert "stats" in data
    assert "total_activities" in data["stats"]


def test_patch_own_profile_and_handle_uniqueness(
    client,
    make_session,
    make_athlete,
    db_session,
):
    make_athlete(810002, firstname="A")
    make_athlete(810003, firstname="B")

    raw_a, cookie = make_session(810002)
    client.cookies.set(cookie, raw_a)

    ok = client.patch(
        "/api/me/profile",
        json={"display_name": "Runner One", "handle": "runner_one"},
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["display_name"] == "Runner One"
    assert body["handle"] == "runner_one"

    bad = client.patch("/api/me/profile", json={"handle": "AB"})
    assert bad.status_code == 400

    reserved = client.patch("/api/me/profile", json={"handle": "admin"})
    assert reserved.status_code == 400

    raw_b, cookie_b = make_session(810003)
    client.cookies.set(cookie_b, raw_b)
    clash = client.patch("/api/me/profile", json={"handle": "runner_one"})
    assert clash.status_code == 400
    assert "já está em uso" in clash.json()["detail"]


def test_cannot_patch_another_athlete_via_body(
    client,
    make_session,
    make_athlete,
):
    """athlete_id in JSON must be ignored; session decides identity."""
    make_athlete(810004, firstname="Self")
    make_athlete(810005, firstname="Other")
    raw, cookie = make_session(810004)
    client.cookies.set(cookie, raw)

    resp = client.patch(
        "/api/me/profile",
        json={
            "display_name": "Only Me",
            "athlete_id": 810005,
            "handle": "only_me",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["athlete_id"] == 810004
    assert resp.json()["display_name"] == "Only Me"


def test_avatar_upload_and_fallback(
    client,
    make_session,
    make_athlete,
    db_session,
):
    make_athlete(
        810006,
        firstname="Avatar",
        lastname="User",
        profile_medium="https://example.com/strava.jpg",
    )
    raw, cookie = make_session(810006)
    client.cookies.set(cookie, raw)

    before = client.get("/api/me/profile").json()
    assert before["has_custom_avatar"] is False
    assert before["avatar_url"] == "https://example.com/strava.jpg"

    # Valid tiny JPEG via Pillow (upload path now re-encodes images).
    import io as _io

    from PIL import Image

    buf = _io.BytesIO()
    Image.new("RGB", (32, 32), color=(40, 180, 90)).save(buf, format="JPEG", quality=90)
    jpeg = buf.getvalue()
    up = client.post(
        "/api/me/avatar",
        files={"file": ("avatar.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert up.status_code == 200, up.text
    assert up.json()["has_custom_avatar"] is True
    assert up.json()["avatar_url"].startswith("/api/me/avatar")

    avatar = client.get("/api/me/avatar")
    assert avatar.status_code == 200
    assert avatar.headers["content-type"].startswith("image/jpeg")
    assert avatar.content.startswith(b"\xff\xd8\xff")
    # Stored image should be a processed JPEG (not empty).
    assert len(avatar.content) > 100

    deleted = client.delete("/api/me/avatar")
    assert deleted.status_code == 200
    assert deleted.json()["has_custom_avatar"] is False
    assert deleted.json()["avatar_url"] == "https://example.com/strava.jpg"


def test_avatar_process_accepts_large_png(tmp_path):
    from avatar_helpers import process_avatar_image, validate_avatar_upload

    from PIL import Image

    buf = io.BytesIO()
    # Noisy image so PNG is non-trivial; still under upload cap.
    img = Image.new("RGB", (2000, 1500))
    pixels = img.load()
    for y in range(0, 1500, 3):
        for x in range(0, 2000, 3):
            pixels[x, y] = ((x * 17) % 256, (y * 13) % 256, 90)
    img.save(buf, format="PNG")
    raw = buf.getvalue()
    validate_avatar_upload(raw, "image/png")
    processed, ctype = process_avatar_image(raw)
    assert ctype == "image/jpeg"
    assert processed.startswith(b"\xff\xd8\xff")
    # Longest edge capped at 1600 → stored JPEG stays compact.
    assert len(processed) < 900_000
    out = Image.open(io.BytesIO(processed))
    assert max(out.size) <= 1600


def test_avatar_rejects_invalid_file(client, make_session, make_athlete):
    make_athlete(810007)
    raw, cookie = make_session(810007)
    client.cookies.set(cookie, raw)

    bad = client.post(
        "/api/me/avatar",
        files={"file": ("x.txt", io.BytesIO(b"not-an-image"), "text/plain")},
    )
    assert bad.status_code == 400


def test_profile_without_photo_uses_initials(
    client,
    make_session,
    make_athlete,
):
    make_athlete(810008, firstname="Solo")
    raw, cookie = make_session(810008)
    client.cookies.set(cookie, raw)
    data = client.get("/api/me/profile").json()
    assert data["avatar_url"] is None
    assert data["initials"] == "SO"
