"""Strava sync media helpers: polyline extract + photo URL pick."""

from __future__ import annotations

from import_strava import _extract_primary_photo_url, _map_polyline


def test_map_polyline_from_list_payload():
    assert _map_polyline({"map": {"summary_polyline": "abc"}}) == "abc"
    assert _map_polyline({"map": {}}) is None
    assert _map_polyline({}) is None


def test_extract_primary_photo_prefers_600():
    detail = {
        "photos": {
            "count": 2,
            "primary": {
                "urls": {
                    "100": "https://cdn.example/100.jpg",
                    "600": "https://cdn.example/600.jpg",
                }
            },
        }
    }
    url, count = _extract_primary_photo_url(detail)
    assert url == "https://cdn.example/600.jpg"
    assert count == 2


def test_extract_primary_photo_empty():
    url, count = _extract_primary_photo_url({"photos": {"count": 0}})
    assert url is None
    assert count == 0
