"""Tests for the /logs ingest endpoint."""


def _log(**over):
    base = {
        "timestamp": "2026-07-04T10:00:00Z",
        "url": "https://youtube.com",
        "domain": "youtube.com",
        "minutesActive": 0,
        "isFocusSession": True,
        "isDistractionAttempt": True,
    }
    base.update(over)
    return base


def test_ingest_persists_and_counts(client):
    r = client.post("/logs", json={"logs": [_log(), _log()]})
    assert r.status_code == 200
    assert r.json()["received"] == 2
    assert client.get("/logs/count").json()["count"] == 2


def test_client_supplied_user_id_is_ignored(client, db_session):
    # A client trying to write logs under someone else's id must not succeed;
    # rows are always scoped to the authenticated user.
    client.post("/logs", json={"logs": [_log(userId="attacker")]})

    from app.db_models import ActivityLog

    rows = db_session.query(ActivityLog).all()
    assert len(rows) == 1
    assert rows[0].user_id == "test-user"


def test_bad_timestamp_is_rejected(client):
    r = client.post("/logs", json={"logs": [_log(timestamp="not-a-date")]})
    assert r.status_code == 400


def test_requires_auth(anon_client):
    assert anon_client.post("/logs", json={"logs": []}).status_code == 401


def test_total_stored_counts_only_the_callers_rows(client, db_session):
    # Another tenant's rows must not leak into this user's response.
    from datetime import datetime, timezone

    from app.db_models import ActivityLog

    db_session.add(
        ActivityLog(
            user_id="someone-else",
            occurred_at=datetime(2026, 7, 4, tzinfo=timezone.utc),
            url="https://x.com",
            domain="x.com",
            minutes_active=0,
            is_focus_session=False,
            is_distraction_attempt=False,
        )
    )
    db_session.commit()
    r = client.post("/logs", json={"logs": [_log()]})
    assert r.json()["total_stored"] == 1


def test_db_errors_are_not_echoed(client, db_session, monkeypatch):
    def boom():
        raise RuntimeError('relation "activity_logs" does not exist at host db.internal')

    monkeypatch.setattr(db_session, "commit", boom)
    r = client.post("/logs", json={"logs": [_log()]})
    assert r.status_code == 500
    assert "activity_logs" not in r.text and "db.internal" not in r.text


def test_oversized_batch_is_rejected(client):
    from app.models import MAX_LOGS_PER_BATCH

    r = client.post("/logs", json={"logs": [_log()] * (MAX_LOGS_PER_BATCH + 1)})
    assert r.status_code == 422


def test_long_url_is_trimmed_not_rejected(client, db_session):
    from app.db_models import ActivityLog
    from app.models import MAX_URL_LENGTH

    r = client.post("/logs", json={"logs": [_log(url="https://a.com/?q=" + "x" * 5000)]})
    assert r.status_code == 200
    assert len(db_session.query(ActivityLog).one().url) == MAX_URL_LENGTH


def test_minutes_are_clamped(client, db_session):
    from app.db_models import ActivityLog

    client.post("/logs", json={"logs": [_log(minutesActive=99999), _log(minutesActive=-5)]})
    mins = sorted(r.minutes_active for r in db_session.query(ActivityLog).all())
    assert mins == [0, 24 * 60]
