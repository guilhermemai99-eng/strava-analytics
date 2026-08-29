"""Avatar URL prefers higher-res Strava profile when available."""

from __future__ import annotations

from athlete import Athlete
from profile_helpers import avatar_url_for, public_avatar_url_for


def test_avatar_prefers_profile_over_medium():
    athlete = Athlete(
        id=1,
        profile="https://cdn.example/profile-124.jpg",
        profile_medium="https://cdn.example/profile-62.jpg",
    )
    assert avatar_url_for(athlete) == "https://cdn.example/profile-124.jpg"
    assert public_avatar_url_for(athlete) == "https://cdn.example/profile-124.jpg"


def test_avatar_falls_back_to_medium():
    athlete = Athlete(id=2, profile_medium="https://cdn.example/profile-62.jpg")
    assert avatar_url_for(athlete) == "https://cdn.example/profile-62.jpg"
    assert public_avatar_url_for(athlete) == "https://cdn.example/profile-62.jpg"
