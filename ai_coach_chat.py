"""Pulse AI Coach chat — irreverent, funny, data-aware."""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from ai_context import build_ai_context


load_dotenv()

MODEL = os.getenv("OPENAI_COACH_MODEL") or "gpt-5.6-luna"
MAX_HISTORY = 16
MAX_USER_CHARS = 1200

SYSTEM_PROMPT = """
You are the Pulse AI Coach — a running coach with attitude.

Personality:
- Irreverent, witty, confident, slightly provocative.
- Sound like a sharp friend who actually knows training.
- Funny without being childish, meme-spammy, or mean.
- Never offensive about body, gender, race, or health conditions.
- Roast bad habits gently. Celebrate real work.
- Short replies: 2–5 sentences. Occasional one-liners welcome.
- No corporate fitness speak. No “synergy”. No fake hustle porn.
- No medical diagnosis. No injury treatment plans — tell them to see a pro.
- Don’t invent PRs, injuries, or workouts that aren’t in the data.
- If data is thin, admit it with personality (“My crystal ball is still on a rest day”).
- Match the user’s language: Portuguese (Portugal) if they write in Portuguese; English otherwise.
- Prefer Portuguese of Portugal when matching Portuguese.
- No markdown fences. No bullet walls unless the user asks for a plan.
- You may tease skipping recovery, ego paces, and “easy” runs that weren’t easy.

You receive JSON athlete context and recent chat turns.
Use the numbers. Make the advice useful AND entertaining.
""".strip()


FALLBACK_REPLIES = (
    "I tried to be profound and the servers yawned. Ask me again — I’m still stretching.",
    "Brain cramp. Not the athletic kind. Hit me with that question one more time.",
    "That didn’t go the distance. Try again while I retie my metaphorical laces.",
)


class CoachChatError(Exception):
    pass


def _client() -> OpenAI:
    return OpenAI()


def build_coach_context(
    *,
    weekly_data,
    performance_data,
    summary_data,
    evolution_data,
    performance_comparison,
    recommendation=None,
    athlete_score=None,
) -> dict[str, Any]:
    context = build_ai_context(weekly_data, performance_data, summary_data)
    context["evolution"] = evolution_data
    context["performance_comparison"] = performance_comparison
    if recommendation is not None:
        context["session_recommendation"] = recommendation
    if athlete_score is not None:
        context["athlete_score"] = {
            "overall": athlete_score.get("overall"),
            "categories": {
                key: {
                    "score": (val or {}).get("score"),
                    "trend": (val or {}).get("trend"),
                }
                for key, val in (athlete_score.get("categories") or {}).items()
            },
        }
    return context


def _fallback_reply(seed: str = "") -> str:
    idx = sum(ord(c) for c in seed) % len(FALLBACK_REPLIES) if seed else 0
    return FALLBACK_REPLIES[idx]


def generate_coach_reply(
    *,
    user_message: str,
    history: list[dict[str, str]],
    context: dict[str, Any],
) -> str:
    message = (user_message or "").strip()
    if not message:
        raise CoachChatError("Empty message.")
    if len(message) > MAX_USER_CHARS:
        raise CoachChatError("Message too long.")

    trimmed_history = history[-MAX_HISTORY:]

    # Prefer Responses API like ai_insights; fall back to chat.completions.
    input_payload = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": (
                "Athlete context JSON:\n"
                + json.dumps(context, ensure_ascii=False, default=str)
            ),
        },
    ]
    for turn in trimmed_history:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            input_payload.append({"role": role, "content": content})
    input_payload.append({"role": "user", "content": message})

    try:
        client = _client()
        try:
            response = client.responses.create(
                model=MODEL,
                input=input_payload,
            )
            text = (response.output_text or "").strip()
        except Exception:
            # Older/newer SDK shape safety net.
            chat = client.chat.completions.create(
                model=MODEL,
                messages=input_payload,
            )
            text = (chat.choices[0].message.content or "").strip()
    except Exception:
        return _fallback_reply(message)

    if not text:
        return _fallback_reply(message)

    # Soft trim runaway essays.
    if len(text) > 1800:
        text = text[:1800].rsplit(" ", 1)[0] + "…"
    return text


def welcome_message() -> str:
    return (
        "Shoes on. Ego optional. I’m your Pulse coach — "
        "equal parts advice and mild roasting. "
        "Ask me about pace, recovery, long runs, or why yesterday felt illegal."
    )
