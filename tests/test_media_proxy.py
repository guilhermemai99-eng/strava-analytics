"""Media proxy allowlist + URL wrapping."""

from __future__ import annotations

from media_helpers import is_allowed_media_url, proxied_media_url


def test_proxy_wraps_strava_cloudfront():
    src = "https://dgalywyr863hv.cloudfront.net/pictures/athletes/1/2/3/large.jpg"
    out = proxied_media_url(src)
    assert out.startswith("/api/media/proxy?url=")
    assert "large.jpg" in out


def test_proxy_passes_app_paths():
    assert proxied_media_url("/api/me/avatar?v=1") == "/api/me/avatar?v=1"


def test_allowlist_rejects_random_hosts():
    assert is_allowed_media_url("https://evil.example/x.jpg") is False
    assert proxied_media_url("https://evil.example/x.jpg") == "https://evil.example/x.jpg"
