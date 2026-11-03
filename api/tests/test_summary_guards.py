"""Tests for the AI generation quota (global daily cap + per-user limit)."""
import pytest
from fastapi import HTTPException

import app.routers.summary as summary
from app.config import Settings
from app.db_models import AIGenerationEvent


@pytest.fixture
def limits(monkeypatch):
    def set_limits(daily=50, per_user=5):
        s = Settings(ai_daily_generation_limit=daily, ai_rate_limit_per_user=per_user)
        monkeypatch.setattr(summary, "get_settings", lambda: s)

    return set_limits


def _events(db):
    return db.query(AIGenerationEvent).count()


def test_per_user_limit(db_session, limits):
    limits(per_user=2)
    summary._reserve_generation(db_session, "alice", "1.1.1.1")
    summary._reserve_generation(db_session, "alice", "2.2.2.2")
    with pytest.raises(HTTPException) as e:
        # A different IP does not help: the limit is keyed on the user.
        summary._reserve_generation(db_session, "alice", "3.3.3.3")
    assert e.value.status_code == 429
    # The rejected attempt released its slot; another user is unaffected.
    assert _events(db_session) == 2
    summary._reserve_generation(db_session, "bob", "1.1.1.1")


def test_global_daily_cap(db_session, limits):
    limits(daily=2)
    summary._reserve_generation(db_session, "a", "ip")
    summary._reserve_generation(db_session, "b", "ip")
    with pytest.raises(HTTPException):
        summary._reserve_generation(db_session, "c", "ip")
    assert _events(db_session) == 2


def test_release_returns_the_slot(db_session, limits):
    limits(per_user=1)
    event = summary._reserve_generation(db_session, "alice", "ip")
    summary._release(db_session, event)
    summary._reserve_generation(db_session, "alice", "ip")  # does not raise


def test_old_env_name_still_works(monkeypatch):
    monkeypatch.setenv("AI_RATE_LIMIT_PER_IP", "7")
    assert Settings().ai_rate_limit_per_user == 7


def test_forwarded_for_is_ignored_for_the_audit_ip():
    class Req:
        headers = {"x-forwarded-for": "6.6.6.6", "fly-client-ip": "9.9.9.9"}
        client = None

    assert summary._client_ip(Req()) == "9.9.9.9"
