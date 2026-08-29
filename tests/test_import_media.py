"""Strava sync media helpers: polyline extract + photo URL pick."""

from __future__ import annotations

from import_strava import (
    _extract_primary_photo_url,
    _map_polyline,
    _photo_url_looks_small,
)


def test_map_polyline_from_list_payload():
    assert _map_polyline({"map": {"summary_polyline": "abc"}}) == "abc"
    assert _map_polyline({"map": {}}) is None
    assert _map_polyline({}) is None


def test_extract_primary_photo_prefers_largest():
    detail = {
        "photos": {
            "count": 2,
            "primary": {
                "urls": {
                    "100": "https://cdn.example/100.jpg",
                    "600": "https://cdn.example/600.jpg",
                    "1200": "https://cdn.example/1200.jpg",
                }
            },
        }
    }
    url, count = _extract_primary_photo_url(detail)
    assert url == "https://cdn.example/1200.jpg"
    assert count == 2


def test_map_polyline_prefers_detailed():
    assert (
        _map_polyline(
            {"map": {"polyline": "detailed", "summary_polyline": "summary"}}
        )
        == "detailed"
    )
    assert _map_polyline({"map": {"summary_polyline": "summary"}}) == "summary"


def test_extract_primary_photo_empty():
    url, count = _extract_primary_photo_url({"photos": {"count": 0}})
    assert url is None
    assert count == 0


def test_photo_url_looks_small():
    assert _photo_url_looks_small(None) is True
    assert _photo_url_looks_small("https://cdn.example/photo-600x600.jpg") is True
    assert _photo_url_looks_small("https://cdn.example/photo-1200x900.jpg") is False
    assert _photo_url_looks_small("https://cdn.example/photos/600.jpg") is True
    assert _photo_url_looks_small("https://cdn.example/photos/2048.jpg") is False
