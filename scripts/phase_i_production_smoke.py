#!/usr/bin/env python3
"""Foundation V2 Phase I — production anonymous smoke against Railway.

Authenticated Strava OAuth / sync must be verified manually after deploy:
  1) Snapshot Postgres
  2) Set TOKEN_ENCRYPTION_KEY (if not set)
  3) Deploy this release (alembic upgrade head via start.sh)
  4) Run: python scripts/encrypt_strava_tokens.py
  5) Login with Strava → dashboard boot sync → analytics → logout

Usage:
  PHASE_I_BASE_URL=https://web-production-c4ff9.up.railway.app \\
    python scripts/phase_i_production_smoke.py
"""

from __future__ import annotations

import os
import sys

import requests

BASE = os.getenv(
    "PHASE_I_BASE_URL",
    "https://web-production-c4ff9.up.railway.app",
).rstrip("/")


def _ok(msg: str) -> None:
    print(f"PASS {msg}")


def _fail(msg: str) -> None:
    print(f"FAIL {msg}", file=sys.stderr)


def main() -> int:
    failed = 0

    home = requests.get(f"{BASE}/", timeout=30)
    if home.status_code == 200 and ("Pulse" in home.text or "Strava" in home.text):
        _ok(f"GET / -> 200 ({BASE})")
    else:
        _fail(f"GET / -> {home.status_code}")
        failed += 1

    me = requests.get(f"{BASE}/auth/me", timeout=30)
    if me.status_code == 200 and me.json().get("authenticated") is False:
        _ok("/auth/me anonymous contract")
    else:
        _fail(f"/auth/me -> {me.status_code} {me.text[:200]}")
        failed += 1

    dash = requests.get(f"{BASE}/dashboard", allow_redirects=False, timeout=30)
    loc = dash.headers.get("location", "")
    if dash.status_code in {302, 307} and loc.endswith("/"):
        _ok("/dashboard redirects to /")
    else:
        _fail(f"/dashboard -> {dash.status_code} location={loc}")
        failed += 1

    # After Phase F deploy this must be 401. Older prod may still return 200+error.
    summary = requests.get(f"{BASE}/analytics/summary", timeout=30)
    if summary.status_code == 401:
        _ok("/analytics/summary -> 401 (Phase F live)")
    elif summary.status_code == 200 and "não autenticado" in summary.text:
        _ok(
            "/analytics/summary still 200+error "
            "(Phase F not deployed yet — expected until merge)"
        )
    else:
        _fail(f"/analytics/summary -> {summary.status_code} {summary.text[:200]}")
        failed += 1

    sync = requests.post(f"{BASE}/strava/sync", timeout=30)
    if sync.status_code == 401:
        _ok("/strava/sync -> 401 (Phase F live)")
    elif sync.status_code == 200 and "não autenticado" in sync.text:
        _ok("/strava/sync still 200+error (Phase F not deployed yet)")
    else:
        _fail(f"/strava/sync -> {sync.status_code} {sync.text[:200]}")
        failed += 1

    print()
    print("Manual checklist after deploy + encrypt job:")
    print("  [ ] TOKEN_ENCRYPTION_KEY set on Railway web service")
    print("  [ ] Deploy logs show alembic upgrade to 0004_token_encryption_ready")
    print("  [ ] DATABASE_URL host is Railway Postgres (not localhost)")
    print("  [ ] python scripts/encrypt_strava_tokens.py  -> plaintext_v0=0")
    print("  [ ] Strava OAuth login -> /dashboard?boot=1")
    print("  [ ] /auth/me authenticated + athlete_id")
    print("  [ ] Sync imports athlete activities")
    print("  [ ] Analytics pages load (summary, score, coach, plan)")
    print("  [ ] Logout clears session")
    print("  [ ] Redeploy does not wipe sessions/tokens")

    if failed:
        print(f"\n{failed} automated check(s) failed")
        return 1

    print("\nALL PHASE I PRODUCTION ANONYMOUS CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
