"""Alembic migration smoke against a dedicated empty Postgres DB."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
SMOKE_URL = (
    "postgresql+psycopg://strava:strava@localhost:5432/strava_analytics_migrate_smoke"
)


def _ensure_smoke_db():
    admin = create_engine(
        "postgresql+psycopg://strava:strava@localhost:5432/postgres",
        isolation_level="AUTOCOMMIT",
    )
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname='strava_analytics_migrate_smoke'")
        ).scalar()
        if not exists:
            conn.execute(text("CREATE DATABASE strava_analytics_migrate_smoke OWNER strava"))
        conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname='strava_analytics_migrate_smoke' AND pid <> pg_backend_pid()"
            )
        )
    admin.dispose()

    engine = create_engine(SMOKE_URL, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO strava"))
    engine.dispose()


def test_alembic_upgrade_head_on_empty_database():
    _ensure_smoke_db()

    env = os.environ.copy()
    env["DATABASE_URL"] = SMOKE_URL
    # Fresh interpreter so database.py picks up SMOKE_URL.
    result = subprocess.run(
        [
            str(ROOT / ".venv/bin/python"),
            "-c",
            (
                "from alembic.config import Config; from alembic import command; "
                f"cfg=Config({str(ROOT / 'alembic.ini')!r}); command.upgrade(cfg, 'head')"
            ),
        ],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(result.stdout + "\n" + result.stderr)

    engine = create_engine(SMOKE_URL)
    with engine.connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public'"
                )
            )
        }
        cols = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='strava_auth'"
                )
            )
        }
        activity_cols = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='activities'"
                )
            )
        }
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()

    engine.dispose()

    assert {
        "activities",
        "athletes",
        "sessions",
        "oauth_states",
        "strava_auth",
        "alembic_version",
    }.issubset(tables)
    assert "token_version" in cols
    assert "updated_at" in cols
    assert "summary_polyline" in activity_cols
    assert "photo_url" in activity_cols
    assert "coach_messages" in tables
    assert "follows" in tables
    assert {
        "conversations",
        "conversation_participants",
        "direct_messages",
        "notifications",
        "runs",
        "run_participants",
    }.issubset(tables)
    assert version == "0011_runs"
