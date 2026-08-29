#!/usr/bin/env python3
"""Phase F: protected APIs return 401; pages keep redirects; /auth/me stays 200."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Avoid OpenAI client init failure during import of main
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-used")

from fastapi.testclient import TestClient
from main import app


PROTECTED = [
    ("GET", "/activities"),
    ("POST", "/activities"),
    ("POST", "/strava/sync"),
    ("GET", "/analytics/summary"),
    ("GET", "/analytics/weekly"),
    ("GET", "/analytics/performance"),
    ("GET", "/analytics/running-performance"),
    ("GET", "/analytics/insights"),
    ("GET", "/analytics/training-load"),
    ("GET", "/analytics/evolution"),
    ("GET", "/analytics/performance-comparison"),
    ("GET", "/analytics/ai-context"),
    ("GET", "/analytics/ai-insights"),
    ("GET", "/analytics/athlete-score"),
    ("GET", "/analytics/ai-coach"),
    ("GET", "/analytics/weekly-training-plan"),
]


def main() -> int:
    client = TestClient(app, follow_redirects=False)

    # /auth/me stays 200 with authenticated=false
    me = client.get("/auth/me")
    assert me.status_code == 200, me.status_code
    assert me.json() == {"authenticated": False}
    print("PASS /auth/me -> 200 authenticated=false")

    # /dashboard without session -> 302 /
    dash = client.get("/dashboard")
    assert dash.status_code == 302, dash.status_code
    assert dash.headers.get("location") == "/"
    print("PASS /dashboard -> 302 /")

    # Protected APIs -> 401
    for method, path in PROTECTED:
        if method == "GET":
            resp = client.get(path)
        elif path == "/activities":
            resp = client.post(
                path,
                json={
                    "name": "x",
                    "distance_km": 1,
                    "time_minutes": 10,
                    "average_heart_rate": 120,
                },
            )
        else:
            resp = client.post(path)
        assert resp.status_code == 401, f"{method} {path} -> {resp.status_code} {resp.text}"
        body = resp.json()
        assert "detail" in body, body
        print(f"PASS {method} {path} -> 401")

    # Home still 200 login page when anonymous
    home = client.get("/")
    assert home.status_code == 200
    print("PASS / -> 200 login")

    print("ALL PHASE F CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
