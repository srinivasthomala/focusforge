"""Unit tests for the pure dashboard aggregation (no DB needed)."""

from datetime import date

from app.models import LogEntry
from app.routers.dashboard import build_dashboard, filter_today

TODAY = date(2026, 7, 4)


def log(ts, url="x", domain="x", minutes=0.0, focus=True, distraction=False):
    return LogEntry(
        timestamp=ts,
        url=url,
        domain=domain,
        minutesActive=minutes,
        isFocusSession=focus,
        isDistractionAttempt=distraction,
    )


def test_empty_logs_are_all_zero_with_seven_week_buckets():
    d = build_dashboard([], TODAY, "summary")
    assert d.todayFocusMinutes == 0
    assert d.todaySessions == 0
    assert d.distractionAttempts == 0
    assert d.topDistractions == []
    assert len(d.week) == 7
    assert d.aiSummary == "summary"


def test_focus_minutes_come_from_session_end_not_planned_duration():
    # A session-start marker carries 0 minutes; the session-end carries the real
    # elapsed time. Only the elapsed time should count (regression: used to be 25).
    logs = [
        log("2026-07-04T10:00:00Z", url="session-start", minutes=0),
        log("2026-07-04T10:12:00Z", url="session-end", minutes=12.0),
        log("2026-07-04T11:00:00Z", url="session-start", minutes=0),
        log("2026-07-04T11:08:00Z", url="session-end", minutes=8.0),
    ]
    d = build_dashboard(logs, TODAY, "s")
    assert d.todayFocusMinutes == 20  # 12 + 8, not 2 * 25
    assert d.todaySessions == 2  # two session-start markers


def test_distractions_counted_and_ranked():
    logs = [
        log("2026-07-04T10:00:00Z", domain="youtube.com", distraction=True, focus=False),
        log("2026-07-04T10:01:00Z", domain="youtube.com", distraction=True, focus=False),
        log("2026-07-04T10:02:00Z", domain="reddit.com", distraction=True, focus=False),
    ]
    d = build_dashboard(logs, TODAY, "s")
    assert d.distractionAttempts == 3
    assert d.topDistractions[0] == "youtube.com"  # most frequent first
    assert set(d.topDistractions) == {"youtube.com", "reddit.com"}


def test_other_days_excluded_from_today_but_counted_in_week():
    logs = [
        log("2026-07-04T10:12:00Z", url="session-end", minutes=10.0),  # today
        log("2026-07-01T09:00:00Z", url="session-end", minutes=30.0),  # earlier in week
    ]
    d = build_dashboard(logs, TODAY, "s")
    assert d.todayFocusMinutes == 10  # only today's
    week_minutes = {w.date: w.minutes for w in d.week}
    assert week_minutes["2026-07-04"] == 10
    assert week_minutes["2026-07-01"] == 30


def test_filter_today_ignores_unparseable_timestamps():
    logs = [log("not-a-date"), log("2026-07-04T10:00:00Z")]
    assert len(filter_today(logs, TODAY)) == 1
