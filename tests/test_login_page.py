"""Anonymous home serves the Figma-aligned PULSE login landing."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_anonymous_home_serves_login_landing(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    body = response.text
    assert "PULSE" in body
    assert "RUN TOGETHER" in body
    assert "GET BETTER" in body
    assert 'href="/auth/strava"' in body
    assert "ENTRAR COM STRAVA" in body
    assert "/static/pulse/login.css" in body
    assert "/static/pulse/photos/login-hero.jpg" in body
    assert "FEED" in body
    assert "RUNS" in body
    assert "DISCOVER" in body
    assert "PROFILE" in body


def test_login_stylesheet_uses_figma_tokens(client):
    response = client.get("/static/pulse/login.css")
    assert response.status_code == 200
    css = response.text
    assert "#f5f3ee" in css
    assert "#d6ff2e" in css
    assert "#000000" in css
    assert "Archivo" in css
    assert "IBM Plex Mono" in css


def test_login_hero_is_served(client):
    response = client.get("/static/pulse/photos/login-hero.jpg")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("image/")


def test_login_files_exist_on_disk():
    assert (ROOT / "static/login.html").exists()
    assert (ROOT / "static/pulse/login.css").exists()
    assert (ROOT / "static/pulse/photos/login-hero.jpg").exists()


def test_authenticated_home_skips_login(client, make_session):
    raw, cookie = make_session(880301)
    response = client.get("/", cookies={cookie: raw}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers.get("location") == "/dashboard"
