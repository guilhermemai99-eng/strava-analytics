"""Avatar URL prefers higher-res Strava profile when available."""

from __future__ import annotations

from athlete import Athlete
from profile_helpers import (
    avatar_url_for,
    best_strava_profile_url,
    public_avatar_url_for,
    upgrade_strava_profile_url,
)


def test_upgrade_medium_jpg_to_large():
    medium = (
        "https://dgalywyr863hv.cloudfront.net/pictures/athletes/1/2/3/medium.jpg"
    )
    large = (
        "https://dgalywyr863hv.cloudfront.net/pictures/athletes/1/2/3/large.jpg"
    )
    assert upgrade_strava_profile_url(medium) == large
    assert upgrade_strava_profile_url(large) == large
    assert upgrade_strava_profile_url(medium + "?v=1") == large + "?v=1"
    assert upgrade_strava_profile_url(None) is None
    assert upgrade_strava_profile_url("  ") is None


def test_best_strava_profile_prefers_profile_then_upgrades_medium():
    assert (
        best_strava_profile_url(
            "https://cdn.example/pictures/athletes/1/2/3/large.jpg",
            "https://cdn.example/pictures/athletes/1/2/3/medium.jpg",
        )
        == "https://cdn.example/pictures/athletes/1/2/3/large.jpg"
    )
    assert (
        best_strava_profile_url(
            None,
            "https://cdn.example/pictures/athletes/1/2/3/medium.jpg",
        )
        == "https://cdn.example/pictures/athletes/1/2/3/large.jpg"
    )


def test_avatar_prefers_profile_over_medium():
    athlete = Athlete(
        id=1,
        profile="https://cdn.example/profile-124.jpg",
        profile_medium="https://cdn.example/profile-62.jpg",
    )
    assert avatar_url_for(athlete) == "https://cdn.example/profile-124.jpg"
    assert public_avatar_url_for(athlete) == "https://cdn.example/profile-124.jpg"


def test_avatar_upgrades_medium_only():
    athlete = Athlete(
        id=2,
        profile_medium=(
            "https://dgalywyr863hv.cloudfront.net/pictures/athletes/9/9/1/medium.jpg"
        ),
    )
    expected = (
        "https://dgalywyr863hv.cloudfront.net/pictures/athletes/9/9/1/large.jpg"
    )
    assert avatar_url_for(athlete) == expected
    assert public_avatar_url_for(athlete) == expected
