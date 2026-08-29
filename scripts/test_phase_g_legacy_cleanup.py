#!/usr/bin/env python3
"""Phase G: confirm dead legacy surface is gone; live surface remains."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("OPENAI_API_KEY", "test-key-not-used")

from fastapi.testclient import TestClient
from main import app


REMOVED_FILES = [
    "seed.py",
    "query.py",
    "clean.py",
    "strava_api.py",
    "performance.py",
    "reset_db.py",
    "static/dashboard_backup.html",
]

LIVE_GET = [
    "/",
    "/auth/me",
    "/activities",
    "/analytics/summary",
    "/analytics/weekly",
    "/analytics/running-performance",
    "/analytics/insights",
    "/analytics/training-load",
    "/analytics/evolution",
    "/analytics/performance-comparison",
    "/analytics/ai-context",
    "/analytics/ai-insights",
    "/analytics/athlete-score",
    "/analytics/ai-coach",
    "/analytics/weekly-training-plan",
]


def main() -> int:
    for rel in REMOVED_FILES:
        path = ROOT / rel
        assert not path.exists(), f"still present: {rel}"
        print(f"PASS removed {rel}")

    # Duplicate Activity module must not import
    try:
        __import__("strava_api")
        raise AssertionError("strava_api still importable")
    except ModuleNotFoundError:
        print("PASS strava_api not importable")

    try:
        __import__("performance")
        raise AssertionError("performance still importable")
    except ModuleNotFoundError:
        print("PASS performance not importable")

    client = TestClient(app, follow_redirects=False)

    post = client.post(
        "/activities",
        json={
            "name": "x",
            "distance_km": 1,
            "time_minutes": 10,
            "average_heart_rate": 120,
        },
    )
    assert post.status_code in {404, 405}, post.status_code
    print(f"PASS POST /activities -> {post.status_code} (legacy create removed)")

    # Live routes still registered (auth may 200/401/302 depending on Phase F)
    for path in LIVE_GET:
        resp = client.get(path)
        assert resp.status_code != 404, f"{path} missing ({resp.status_code})"
        print(f"PASS GET {path} registered ({resp.status_code})")

    dash = client.get("/dashboard")
    assert dash.status_code in {200, 302}, dash.status_code
    print(f"PASS GET /dashboard registered ({dash.status_code})")

    sync = client.post("/strava/sync")
    assert sync.status_code != 404, sync.status_code
    print(f"PASS POST /strava/sync registered ({sync.status_code})")

    assert (ROOT / "static/dashboard.html").exists()
    assert (ROOT / "static/login.html").exists()
    print("PASS active frontend files present")

    print("ALL PHASE G CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
