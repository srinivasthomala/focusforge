"""DELETE /account: removes all of the user's rows, then their Supabase sign-in."""

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.auth import get_current_web_user
from app.config import get_settings
from app.database import get_db
from app.db_models import ActivityLog, ApiKey, UserSettings
from app.main import app
from app.routers import account
from tests.conftest import TEST_USER

OTHER = "other-user"


def _seed(db):
    for user in (TEST_USER, OTHER):
        db.add(ActivityLog(user_id=user, occurred_at=datetime(2026, 11, 7, tzinfo=timezone.utc), url="session-end",
                           domain="system", minutes_active=25, is_focus_session=True,
                           is_distraction_attempt=False))
        db.add(UserSettings(user_id=user, blocklist=json.dumps(["reddit.com"]), blocking_mode="focus-only"))
        db.add(ApiKey(user_id=user, label="laptop", key_hash=f"hash-{user}", prefix="ff_abc"))
    db.commit()


def _count(db, model, user):
    return db.scalar(select(func.count()).select_from(model).where(model.user_id == user))


@pytest.fixture
def web_client(db_session, monkeypatch):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_web_user] = lambda: TEST_USER
    monkeypatch.setattr(get_settings(), "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(get_settings(), "supabase_secret_key", "sb_secret_test")
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_delete_account_removes_only_this_users_data(web_client, db_session, monkeypatch):
    _seed(db_session)
    deleted = []
    monkeypatch.setattr(account, "delete_supabase_user", deleted.append)

    r = web_client.delete("/account")

    assert r.status_code == 204
    assert deleted == [TEST_USER]
    for model in (ActivityLog, UserSettings, ApiKey):
        assert _count(db_session, model, TEST_USER) == 0
        assert _count(db_session, model, OTHER) == 1


def test_supabase_failure_deletes_nothing(web_client, db_session, monkeypatch):
    _seed(db_session)

    def fail(user_id):
        raise RuntimeError("Supabase admin delete returned 500")

    monkeypatch.setattr(account, "delete_supabase_user", fail)

    r = web_client.delete("/account")

    assert r.status_code == 502
    assert "Nothing was removed" in r.json()["detail"]
    assert _count(db_session, ActivityLog, TEST_USER) == 1
    assert _count(db_session, ApiKey, TEST_USER) == 1


def test_not_configured_returns_503(web_client, db_session, monkeypatch):
    _seed(db_session)
    monkeypatch.setattr(get_settings(), "supabase_secret_key", "")

    r = web_client.delete("/account")

    assert r.status_code == 503
    assert _count(db_session, ActivityLog, TEST_USER) == 1


def test_extension_key_cannot_delete_account(anon_client, db_session):
    _seed(db_session)

    r = anon_client.delete("/account", headers={"Authorization": "Bearer ff_somekey"})

    assert r.status_code == 401
    assert _count(db_session, ActivityLog, TEST_USER) == 1
