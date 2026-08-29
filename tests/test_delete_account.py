"""Account deletion: auth gate, cascade cleanup, session wipe."""

from __future__ import annotations


def test_delete_account_requires_auth(client):
    assert client.delete("/api/me/account").status_code == 401


def test_delete_account_removes_data_and_session(
    client,
    make_session,
    make_athlete,
    make_activity,
    db_session,
):
    from athlete import Athlete
    from follow import Follow
    from models import Activity
    from session_helpers import SESSION_COOKIE_NAME, resolve_athlete_id
    from strava_auth import StravaAuth
    from user_session import UserSession

    make_athlete(960001, firstname="Gone", handle="gone_runner", is_profile_public=True)
    make_athlete(960002, firstname="Stays", handle="stays_here", is_profile_public=True)
    make_activity(960001, strava_id=96000101, name="Last Run")

    raw_other, cookie = make_session(960002)
    client.cookies.set(cookie, raw_other)
    assert client.post("/api/users/960001/follow").status_code == 200

    raw, cookie_me = make_session(960001)
    client.cookies.set(cookie_me, raw)
    assert client.post("/api/users/960002/follow").status_code == 200

    # Seed a strava_auth row like production.
    db_session.add(
        StravaAuth(
            athlete_id=960001,
            access_token="x",
            refresh_token="y",
            expires_at=0,
        )
    )
    db_session.commit()

    resp = client.delete("/api/me/account")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["athlete_id"] == 960001
    assert body["activities_deleted"] >= 1
    assert body["follows_deleted"] >= 1

    # Cookie cleared — authenticated routes fail.
    assert client.get("/api/me/profile").status_code == 401

    db_session.expire_all()
    assert db_session.query(Athlete).filter(Athlete.id == 960001).one_or_none() is None
    assert (
        db_session.query(Activity).filter(Activity.athlete_id == 960001).count() == 0
    )
    assert (
        db_session.query(Follow)
        .filter((Follow.follower_id == 960001) | (Follow.following_id == 960001))
        .count()
        == 0
    )
    assert (
        db_session.query(StravaAuth).filter(StravaAuth.athlete_id == 960001).count()
        == 0
    )
    assert (
        db_session.query(UserSession).filter(UserSession.athlete_id == 960001).count()
        == 0
    )

    # Other athlete untouched.
    assert db_session.query(Athlete).filter(Athlete.id == 960002).one_or_none()
    assert resolve_athlete_id(db_session, raw) is None


def test_delete_account_only_deletes_self(
    client,
    make_session,
    make_athlete,
    db_session,
):
    from athlete import Athlete

    make_athlete(960010, handle="del_a", is_profile_public=True)
    make_athlete(960011, handle="del_b", is_profile_public=True)

    raw, cookie = make_session(960010)
    client.cookies.set(cookie, raw)
    resp = client.request("DELETE", "/api/me/account", json={"athlete_id": 960011})
    assert resp.status_code == 200
    assert resp.json()["athlete_id"] == 960010

    db_session.expire_all()
    assert db_session.query(Athlete).filter(Athlete.id == 960010).one_or_none() is None
    assert db_session.query(Athlete).filter(Athlete.id == 960011).one_or_none()
