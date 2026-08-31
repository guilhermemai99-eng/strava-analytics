"""API 401 contract for protected routes; page redirects preserved."""

from __future__ import annotations

PROTECTED = [
    ("GET", "/activities"),
    ("GET", "/api/feed"),
    ("GET", "/api/feed/following-ids"),
    ("GET", "/api/explore"),
    ("GET", "/api/explore/search"),
    ("GET", "/api/athletes/1/profile"),
    ("GET", "/api/athletes/1/avatar"),
    ("GET", "/api/activities/1"),
    ("GET", "/api/profiles/suggestions"),
    ("GET", "/api/profiles/demo"),
    ("GET", "/api/profiles/demo/relationship"),
    ("GET", "/api/profiles/demo/followers"),
    ("GET", "/api/profiles/demo/following"),
    ("POST", "/api/profiles/demo/follow"),
    ("DELETE", "/api/profiles/demo/follow"),
    ("GET", "/api/users/1/relationship"),
    ("GET", "/api/users/1/followers"),
    ("GET", "/api/users/1/following"),
    ("GET", "/api/follow-requests"),
    ("POST", "/api/users/1/follow-request/accept"),
    ("POST", "/api/users/1/follow-request/decline"),
    ("GET", "/api/coach/messages"),
    ("POST", "/api/coach/chat"),
    ("DELETE", "/api/coach/messages"),
    ("GET", "/api/dms"),
    ("GET", "/api/dms/unread-count"),
    ("POST", "/api/dms/with/1"),
    ("GET", "/api/dms/1"),
    ("GET", "/api/dms/1/messages"),
    ("POST", "/api/dms/1/messages"),
    ("POST", "/api/dms/1/read"),
    ("GET", "/api/notifications"),
    ("GET", "/api/notifications/unread-count"),
    ("POST", "/api/notifications/read"),
    ("GET", "/api/runs"),
    ("GET", "/api/runs/nearby"),
    ("GET", "/api/runs/profile"),
    ("POST", "/api/runs"),
    ("GET", "/api/runs/1"),
    ("PATCH", "/api/runs/1"),
    ("DELETE", "/api/runs/1"),
    ("POST", "/api/runs/1/join"),
    ("POST", "/api/runs/1/leave"),
    ("POST", "/api/runs/1/invite"),
    ("GET", "/api/runs/1/participants"),
    ("GET", "/api/people/matches"),
    ("GET", "/api/people/1/compatibility"),
    ("GET", "/api/people/1/run-together"),
    ("POST", "/api/activities/1/like"),
    ("GET", "/api/activities/1/likes"),
    ("GET", "/api/activities/1/comments"),
    ("POST", "/api/activities/1/comments"),
    ("PATCH", "/api/activities/1/comments/1"),
    ("DELETE", "/api/activities/1/comments/1"),
    ("POST", "/api/activities/1/hide"),
    ("POST", "/api/activities/1/unhide"),
    ("PATCH", "/api/activities/1/visibility"),
    ("PATCH", "/api/activities/1/caption"),
    ("DELETE", "/api/activities/1"),
    ("POST", "/api/activities/1/report"),
    ("POST", "/api/activities/1/share"),
    ("GET", "/api/clubs"),
    ("POST", "/api/clubs"),
    ("GET", "/api/clubs/1"),
    ("POST", "/api/clubs/1/join"),
    ("POST", "/api/clubs/1/leave"),
    ("POST", "/api/clubs/1/transfer"),
    ("PATCH", "/api/clubs/1/members/1"),
    ("DELETE", "/api/clubs/1"),
    ("GET", "/api/clubs/1/runs"),
    ("GET", "/api/clubs/1/members"),
    ("GET", "/api/clubs/1/cover"),
    ("DELETE", "/api/clubs/1/cover"),
    ("GET", "/api/clubs/1/invites"),
    ("POST", "/api/clubs/1/invites"),
    ("POST", "/api/clubs/1/invites/1/cancel"),
    ("POST", "/api/clubs/1/invite-link"),
    ("GET", "/api/club-invites"),
    ("POST", "/api/club-invites/1/accept"),
    ("POST", "/api/club-invites/1/decline"),
    ("POST", "/api/club-invites/redeem"),
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
    ("GET", "/api/media/proxy?url=https://dgalywyr863hv.cloudfront.net/x.jpg"),
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
        elif method == "PATCH" and path.endswith("/visibility"):
            resp = client.patch(path, json={"visibility": "public"})
        elif method == "PATCH" and "/comments/" in path:
            resp = client.patch(path, json={"body": "nice"})
        elif method == "PATCH" and "/members/" in path:
            resp = client.patch(path, json={"role": "admin"})
        elif method == "PATCH":
            resp = client.patch(path, json={})
        elif method == "DELETE":
            resp = client.delete(path)
        elif method == "POST" and path == "/api/coach/chat":
            resp = client.post(path, json={"message": "hi"})
        elif method == "POST" and path.endswith("/messages"):
            resp = client.post(path, json={"content": "hi"})
        elif method == "POST" and path.endswith("/comments"):
            resp = client.post(path, json={"body": "nice"})
        elif method == "POST" and path.endswith("/share"):
            resp = client.post(path, json={"athlete_ids": [1]})
        elif method == "POST" and path == "/api/runs":
            resp = client.post(
                path,
                json={
                    "title": "Test",
                    "location_name": "Porto",
                    "meeting_time": "2030-01-01T09:00:00+00:00",
                    "distance_km": 10,
                },
            )
        elif method == "POST" and path == "/api/clubs":
            resp = client.post(
                path,
                json={"name": "Test Club", "visibility": "public"},
            )
        elif method == "POST" and path.endswith("/invites"):
            resp = client.post(path, json={"handle": "someone"})
        elif method == "POST" and path == "/api/club-invites/redeem":
            resp = client.post(path, json={"token": "x"})
        elif method == "POST" and path.endswith("/transfer"):
            resp = client.post(path, json={"athlete_id": 1})
        elif method == "POST" and path.endswith("/invite"):
            resp = client.post(path, json={"athlete_id": 1})
        elif method == "POST" and path.endswith("/follow"):
            resp = client.post(path)
        else:
            resp = client.post(path)
        assert resp.status_code == 401, f"{method} {path} -> {resp.status_code}"
        assert "detail" in resp.json()


def test_home_still_serves_login(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    assert "PULSE" in body
    assert "RUN TOGETHER" in body
    assert "ENTRAR COM STRAVA" in body
    assert 'href="/auth/strava"' in body
    assert "/static/pulse/login.css" in body
    assert "login-hero.jpg" in body
