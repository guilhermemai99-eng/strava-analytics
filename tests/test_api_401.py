"""API 401 contract for protected routes; page redirects preserved."""

from __future__ import annotations

PROTECTED = [
    ("GET", "/activities"),
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
    ("GET", "/api/me/profile"),
    ("PATCH", "/api/me/profile"),
    ("GET", "/api/me/avatar"),
    ("DELETE", "/api/me/avatar"),
]


def test_auth_me_anonymous_contract(client):
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json() == {"authenticated": False}


def test_dashboard_redirects_when_anonymous(client):
    dash = client.get("/dashboard")
    assert dash.status_code == 302
    assert dash.headers.get("location") == "/"


def test_protected_apis_return_401_without_session(client):
    for method, path in PROTECTED:
        if method == "GET":
            resp = client.get(path)
        elif method == "PATCH":
            resp = client.patch(path, json={})
        elif method == "DELETE":
            resp = client.delete(path)
        else:
            resp = client.post(path)
        assert resp.status_code == 401, f"{method} {path} -> {resp.status_code}"
        assert "detail" in resp.json()


def test_home_still_serves_login(client):
    assert client.get("/").status_code == 200
