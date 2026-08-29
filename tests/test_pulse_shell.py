"""Pulse social shell routes stay authenticated and serve the new UI."""

from __future__ import annotations


def test_dashboard_serves_pulse_shell(client, make_session, make_athlete):
    make_athlete(910001, firstname="Shell", lastname="Tester")
    raw, cookie = make_session(910001)

    response = client.get("/dashboard", cookies={cookie: raw})
    assert response.status_code == 200
    body = response.text
    assert "Pulse" in body
    assert "/static/js/pulse.js" in body
    assert "/static/css/pulse.css" in body
    assert 'data-nav="feed"' in body
    assert 'data-nav="explore"' in body
    assert 'data-nav="messages"' in body


def test_lab_keeps_legacy_analytics(client, make_session, make_athlete):
    make_athlete(910002, firstname="Lab", lastname="Tester")
    raw, cookie = make_session(910002)

    response = client.get("/lab", cookies={cookie: raw})
    assert response.status_code == 200
    assert (
        "bootOverlay" in response.text
        or "Athlete Score" in response.text
        or "Sincronizar Strava" in response.text
    )
    assert "← Home" in response.text
    assert 'href="/dashboard"' in response.text
    assert "lab-home-link" in response.text


def test_dashboard_requires_auth(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers.get("location") == "/"
