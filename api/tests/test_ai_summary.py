"""Tests for the deterministic AI summary path (no Anthropic key needed)."""

from app.ai_summary import (
    FALLBACK_MODEL,
    DailyStats,
    aggregate_stats,
    build_deterministic_summary,
    generate_summary,
)
from app.models import LogEntry


def log(url="x", domain="x", minutes=0.0, focus=True, distraction=False):
    return LogEntry(
        timestamp="2026-07-04T10:00:00Z",
        url=url,
        domain=domain,
        minutesActive=minutes,
        isFocusSession=focus,
        isDistractionAttempt=distraction,
    )


def test_aggregate_counts_sessions_minutes_and_distractions():
    logs = [
        log(url="session-start", minutes=0),
        log(url="session-end", minutes=15.0),
        log(domain="youtube.com", distraction=True, focus=False),
    ]
    stats = aggregate_stats(logs)
    assert stats.total_minutes == 15
    assert stats.focus_sessions == 1
    assert stats.distraction_attempts == 1
    assert stats.top_distractions == ["youtube.com"]


def test_deterministic_summary_has_no_em_dashes():
    stats = DailyStats(
        total_minutes=50, focus_sessions=3, distraction_attempts=1, entry_count=5
    )
    text = build_deterministic_summary(stats)
    assert "—" not in text  # em-dash
    assert "session" in text.lower()


def test_summary_formats_hours_past_sixty_minutes():
    stats = DailyStats(
        total_minutes=75, focus_sessions=2, distraction_attempts=0, entry_count=3
    )
    assert "1h 15m" in build_deterministic_summary(stats)


def test_empty_day_summary():
    assert "No activity" in build_deterministic_summary(DailyStats())


def test_generate_summary_empty_day_uses_fallback():
    # An empty day never calls Claude (nothing to summarize), so it always
    # returns the deterministic fallback regardless of API-key config.
    text, model = generate_summary([])
    assert model == FALLBACK_MODEL
    assert isinstance(text, str) and text


def test_truncated_claude_reply_falls_back(monkeypatch):
    # A max_tokens cut-off must not be served (and cached) as a real summary.
    import sys
    import types

    from app import ai_summary
    from app.config import Settings

    class FakeMessages:
        def create(self, **_):
            block = types.SimpleNamespace(type="text", text="You focused for")
            return types.SimpleNamespace(stop_reason="max_tokens", content=[block])

    fake = types.SimpleNamespace(
        Anthropic=lambda **_: types.SimpleNamespace(messages=FakeMessages())
    )
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    monkeypatch.setattr(ai_summary, "get_settings", lambda: Settings(anthropic_api_key="k"))
    logs = [
        types.SimpleNamespace(
            minutesActive=30, isFocusSession=True, isDistractionAttempt=False,
            domain="docs.python.org", url="https://docs.python.org",
            timestamp="2026-07-04T10:00:00Z",
        )
    ]
    _, model = ai_summary.generate_summary(logs)
    assert model == ai_summary.FALLBACK_MODEL
