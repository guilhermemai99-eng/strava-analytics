"""Strava sync media helpers: polyline extract + HQ photo URL pick."""

from __future__ import annotations

from import_strava import (
    _extract_photo_url_from_photos_list,
    _extract_primary_photo_url,
    _map_polyline,
    is_low_res_photo_url,
)


def test_map_polyline_from_list_payload():
    assert _map_polyline({"map": {"summary_polyline": "abc"}}) == "abc"
    assert _map_polyline({"map": {"polyline": "fullroute"}}) == "fullroute"
    # Prefer full polyline when both are present.
    assert (
        _map_polyline(
            {"map": {"summary_polyline": "short", "polyline": "fullroute"}}
        )
        == "fullroute"
    )
    assert _map_polyline({"map": {}}) is None
    assert _map_polyline({}) is None


def test_encode_polyline_roundtrip_shape():
    from import_strava import encode_polyline, _polyline_from_latlng_stream

    coords = [(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]
    encoded = encode_polyline(coords)
    assert isinstance(encoded, str) and len(encoded) > 5

    from_stream = _polyline_from_latlng_stream(
        {"latlng": {"data": [[38.5, -120.2], [40.7, -120.95], [43.252, -126.453]]}}
    )
    assert from_stream == encoded

    assert _polyline_from_latlng_stream({"latlng": {"data": []}}) is None
    assert _polyline_from_latlng_stream(None) is None


def test_extract_primary_photo_prefers_largest():
    detail = {
        "photos": {
            "count": 2,
            "primary": {
                "urls": {
                    "100": "https://cdn.example/100.jpg",
                    "600": "https://cdn.example/600.jpg",
                    "2048": "https://cdn.example/2048.jpg",
                }
            },
        }
    }
    url, count = _extract_primary_photo_url(detail)
    assert url == "https://cdn.example/2048.jpg"
    assert count == 2


def test_extract_primary_photo_empty():
    url, count = _extract_primary_photo_url({"photos": {"count": 0}})
    assert url is None
    assert count == 0


def test_photos_list_endpoint_prefers_native_hq():
    photos = [
        {
            "source": 2,
            "urls": {"2048": "https://cdn.example/ig.jpg"},
        },
        {
            "source": 1,
            "default_photo": True,
            "urls": {
                "600": "https://cdn.example/600.jpg",
                "2048": "https://cdn.example/native-2048.jpg",
            },
        },
    ]
    url, count = _extract_photo_url_from_photos_list(photos)
    assert url == "https://cdn.example/native-2048.jpg"
    assert count == 2


def test_low_res_photo_detection():
    assert is_low_res_photo_url("https://dgalywyr863hv.cloudfront.net/photos/1-100.jpg")
    assert is_low_res_photo_url("https://cdn.example/foo-600.jpeg")
    assert not is_low_res_photo_url("https://cdn.example/foo-2048.jpg")
    assert is_low_res_photo_url(None)
