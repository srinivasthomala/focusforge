"""Per-user timezone handling: local days, DST, and header persistence."""
from datetime import date, datetime, timezone

from app.db_models import ActivityLog, UserSettings
from app.timezones import day_range_utc, parse_zone, resolve_user_timezone

IST = parse_zone("Asia/Kolkata")
NY = parse_zone("America/New_York")


def test_local_day_range_in_utc():
    start, end = day_range_utc(date(2026, 7, 4), date(2026, 7, 4), IST)
    assert start == datetime(2026, 7, 3, 18, 30, tzinfo=timezone.utc)
    assert end == datetime(2026, 7, 4, 18, 30, tzinfo=timezone.utc)


def test_dst_day_is_23_hours():
    # US clocks spring forward on 2026-03-08.
    start, end = day_range_utc(date(2026, 3, 8), date(2026, 3, 8), NY)
    assert (end - start).total_seconds() == 23 * 3600


def test_invalid_zone_names_are_rejected():
    assert parse_zone("Mars/Olympus") is None
    assert parse_zone("") is None
    assert parse_zone("x" * 100) is None


def test_header_zone_is_saved_and_reused(db_session):
    assert resolve_user_timezone(db_session, "u", "Asia/Kolkata") == IST
    assert db_session.get(UserSettings, "u").timezone == "Asia/Kolkata"
    # Later calls without a header (e.g. a server-side job) use the stored zone.
    assert resolve_user_timezone(db_session, "u", None) == IST
    # A garbage header doesn't overwrite it.
    assert resolve_user_timezone(db_session, "u", "Not/AZone") == IST


def test_unknown_user_defaults_to_utc(db_session):
    assert resolve_user_timezone(db_session, "nobody", None) == timezone.utc


def _add_log(db, when, minutes=30.0):
    db.add(
        ActivityLog(
            user_id="test-user",
            occurred_at=when,
            url="session-end",
            domain="x",
            minutes_active=minutes,
            is_focus_session=True,
            is_distraction_attempt=False,
        )
    )
    db.commit()


def test_dashboard_uses_the_callers_local_day(client, db_session):
    # 20:00 UTC on Jul 4 is 01:30 on Jul 5 in India.
    _add_log(db_session, datetime(2026, 7, 4, 20, 0, tzinfo=timezone.utc))

    utc = client.get("/dashboard").json()
    assert utc["asOf"] == "2026-07-04"

    ist = client.get("/dashboard", headers={"X-Timezone": "Asia/Kolkata"}).json()
    assert ist["asOf"] == "2026-07-05"
    assert ist["todayFocusMinutes"] == 30
    assert ist["week"][-1] == {"date": "2026-07-05", "minutes": 30}
