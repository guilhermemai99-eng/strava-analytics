"""Legacy removal checks from Foundation V2 Phase G."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REMOVED_FILES = [
    "seed.py",
    "query.py",
    "clean.py",
    "strava_api.py",
    "performance.py",
    "reset_db.py",
    "static/dashboard_backup.html",
]


def test_removed_legacy_files_are_gone():
    for rel in REMOVED_FILES:
        assert not (ROOT / rel).exists(), rel


def test_duplicate_modules_not_importable():
    import importlib

    for name in ("strava_api", "performance"):
        try:
            importlib.import_module(name)
            raise AssertionError(f"{name} still importable")
        except ModuleNotFoundError:
            pass


def test_post_activities_removed(client):
    resp = client.post(
        "/activities",
        json={
            "name": "x",
            "distance_km": 1,
            "time_minutes": 10,
            "average_heart_rate": 120,
        },
    )
    # GET /activities still exists, so Starlette returns 405.
    assert resp.status_code in {404, 405}


def test_active_frontend_files_present():
    assert (ROOT / "static/dashboard.html").exists()
    assert (ROOT / "static/login.html").exists()


def test_get_activities_still_registered(client, make_session):
    raw, cookie = make_session(750001)
    client.cookies.set(cookie, raw)
    assert client.get("/activities").status_code == 200
