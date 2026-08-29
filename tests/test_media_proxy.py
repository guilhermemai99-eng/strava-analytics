"""Media proxy helpers for Strava CDN images."""

from __future__ import annotations

from media_helpers import is_allowed_media_url, proxied_media_url


def test_proxied_media_url_wraps_strava_cdn():
    raw = "https://dgalywyr863hv.cloudfront.net/photos/abc/2048.jpg"
    out = proxied_media_url(raw)
    assert out is not None
    assert out.startswith("/api/media/proxy?url=")
    assert "cloudfront.net" in out


def test_proxied_media_url_passthrough_relative():
    assert proxied_media_url("/api/me/avatar") == "/api/me/avatar"


def test_is_allowed_media_url_cloudfront():
    assert is_allowed_media_url("https://foo.cloudfront.net/x.jpg")


def test_is_allowed_media_url_rejects_unknown():
    assert not is_allowed_media_url("https://evil.example/photo.jpg")
