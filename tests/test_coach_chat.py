"""AI Coach chat endpoints: auth, persistence, mocked LLM reply."""

from __future__ import annotations

from unittest.mock import patch

from coach_message import CoachMessage


def test_coach_chat_requires_auth(client):
    assert client.get("/api/coach/messages").status_code == 401
    assert client.post("/api/coach/chat", json={"message": "hi"}).status_code == 401
    assert client.delete("/api/coach/messages").status_code == 401


def test_coach_chat_roundtrip(client, make_session, make_athlete, db_session):
    make_athlete(930001, firstname="Chat", lastname="Runner")
    raw, cookie = make_session(930001)
    client.cookies.set(cookie, raw)

    empty = client.get("/api/coach/messages")
    assert empty.status_code == 200
    assert empty.json()["welcome"]
    assert empty.json()["messages"] == []

    with patch(
        "main.generate_coach_reply",
        return_value="Easy runs are easy. Allegedly. Go for 6km conversational.",
    ):
        resp = client.post(
            "/api/coach/chat",
            json={"message": "What should I run tomorrow?"},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "Allegedly" in body["reply"]
    assert body["user_message"]["role"] == "user"
    assert body["assistant_message"]["role"] == "assistant"

    listed = client.get("/api/coach/messages").json()["messages"]
    assert len(listed) == 2
    assert listed[0]["content"] == "What should I run tomorrow?"
    assert "Allegedly" in listed[1]["content"]

    cleared = client.delete("/api/coach/messages")
    assert cleared.status_code == 200
    assert cleared.json()["deleted"] == 2
    assert client.get("/api/coach/messages").json()["messages"] == []


def test_coach_chat_rejects_empty_message(client, make_session, make_athlete):
    make_athlete(930002)
    raw, cookie = make_session(930002)
    client.cookies.set(cookie, raw)
    resp = client.post("/api/coach/chat", json={"message": "   "})
    assert resp.status_code == 400


def test_coach_messages_are_athlete_scoped(
    client,
    make_session,
    make_athlete,
    db_session,
):
    make_athlete(930010)
    make_athlete(930011)
    db_session.add(
        CoachMessage(
            athlete_id=930011,
            role="assistant",
            content="Secret roast for someone else",
        )
    )
    db_session.commit()

    raw, cookie = make_session(930010)
    client.cookies.set(cookie, raw)
    messages = client.get("/api/coach/messages").json()["messages"]
    assert messages == []
