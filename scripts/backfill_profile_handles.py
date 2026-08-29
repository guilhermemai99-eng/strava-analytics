#!/usr/bin/env python3
"""Assign stable unique handles to athletes that still lack one.

Safe to re-run. Does not overwrite existing handles or display names.
Follow relationships already use athlete.id — this only improves public @urls.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    if not os.environ.get("DATABASE_URL"):
        print("DATABASE_URL is required", file=sys.stderr)
        return 1

    from athlete import Athlete
    from database import SessionLocal
    from profile_helpers import ensure_handle

    db = SessionLocal()
    try:
        missing = (
            db.query(Athlete)
            .filter((Athlete.handle.is_(None)) | (Athlete.handle == ""))
            .order_by(Athlete.id.asc())
            .all()
        )
        print(f"[backfill] athletes without handle: {len(missing)}")
        for athlete in missing:
            before = athlete.handle
            ensure_handle(db, athlete)
            print(f"  id={athlete.id} {before!r} -> {athlete.handle!r}")
        print("[backfill] done")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
