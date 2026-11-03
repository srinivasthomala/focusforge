"""Tests for the per-user settings endpoints."""


def test_defaults_when_never_set(client):
    r = client.get("/settings")
    assert r.status_code == 200
    body = r.json()
    assert body["blockingMode"] == "focus-only"
    assert body["blocklist"] == []  # nothing is blocked until the user chooses


def test_put_normalizes_dedupes_and_persists(client):
    r = client.put(
        "/settings",
        json={
            "blocklist": ["https://www.YouTube.com/feed", "youtube.com", " Reddit.com ", ""],
            "blockingMode": "always",
        },
    )
    assert r.status_code == 200
    assert r.json() == {"blocklist": ["youtube.com", "reddit.com"], "blockingMode": "always"}

    # Persisted: a fresh GET returns the saved, normalized values.
    assert client.get("/settings").json() == {
        "blocklist": ["youtube.com", "reddit.com"],
        "blockingMode": "always",
    }


def test_invalid_blocking_mode_is_rejected(client):
    r = client.put("/settings", json={"blocklist": [], "blockingMode": "nope"})
    assert r.status_code == 422


def test_requires_auth(anon_client):
    assert anon_client.get("/settings").status_code == 401
