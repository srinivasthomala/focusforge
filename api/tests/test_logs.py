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
