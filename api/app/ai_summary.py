"""AI-generated focus summaries.

Wraps the Anthropic Claude API with a deterministic fallback so the app keeps
working when ``ANTHROPIC_API_KEY`` is unset (e.g. the public demo deployment) or
the API call fails. Aggregates are computed from activity logs and handed to
Claude as compact stats — we never ship raw browsing logs to the model.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

FALLBACK_MODEL = "deterministic-fallback"

SYSTEM_PROMPT = (
    "You are FocusForge, an encouraging productivity coach. Given a user's "
    "focus stats for a single day, write a short summary (2-3 sentences, plain "
    "text, no markdown or bullet points) that reflects the numbers back to them "
    "and offers one specific, actionable nudge. Reference the actual figures. "
    "Be warm and motivating, never preachy. Do not use em-dashes or hyphens to "
    "join clauses; use plain periods and short sentences."
)


@dataclass
class DailyStats:
    total_minutes: int = 0
    focus_sessions: int = 0
    distraction_attempts: int = 0
    top_distractions: list[str] = field(default_factory=list)
    entry_count: int = 0


def aggregate_stats(logs) -> DailyStats:
    """Roll a day's worth of log entries into the figures the summary needs."""
    total_minutes = int(sum(log.minutesActive for log in logs if log.isFocusSession))
    focus_sessions = sum(1 for log in logs if log.url == "session-start")
    distraction_attempts = sum(1 for log in logs if log.isDistractionAttempt)
    distracted_domains = [log.domain for log in logs if log.isDistractionAttempt]
    top_distractions = [d for d, _ in Counter(distracted_domains).most_common(3)]
    return DailyStats(
        total_minutes=total_minutes,
        focus_sessions=focus_sessions,
        distraction_attempts=distraction_attempts,
        top_distractions=top_distractions,
        entry_count=len(logs),
    )


def build_deterministic_summary(stats: DailyStats) -> str:
    """A respectable, zero-cost summary used as the fallback everywhere."""
    if stats.entry_count == 0:
        return (
            "No activity tracked yet today. Start a focus session and FocusForge "
            "will begin charting your progress!"
        )

    hours, minutes = divmod(stats.total_minutes, 60)
    time_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"

    parts = [
        f"You logged {time_str} of focused work across "
        f"{stats.focus_sessions} session(s)."
    ]
    if stats.distraction_attempts:
        parts.append(
            f"You pushed past {stats.distraction_attempts} distraction(s) "
            "along the way."
        )
    if stats.focus_sessions > 2:
        parts.append("Great consistency. Keep the streak alive tomorrow!")
    elif stats.focus_sessions > 0:
        parts.append("Nice start. Try stacking one more session tomorrow.")
    else:
        parts.append("Kick off a focus session to build momentum.")
    return " ".join(parts)


def deterministic_summary_from_logs(logs) -> str:
    """Convenience wrapper for callers that just have raw logs (e.g. dashboard)."""
    return build_deterministic_summary(aggregate_stats(logs))


def _format_stats_prompt(stats: DailyStats) -> str:
    hours, minutes = divmod(stats.total_minutes, 60)
    lines = [
        "Here are today's focus stats:",
        f"- Total focused minutes: {stats.total_minutes} ({hours}h {minutes}m)",
        f"- Focus sessions started: {stats.focus_sessions}",
        f"- Distraction attempts blocked: {stats.distraction_attempts}",
    ]
    if stats.top_distractions:
        lines.append(
            f"- Top distracting sites: {', '.join(stats.top_distractions)}"
        )
    lines.append("\nWrite the summary now.")
    return "\n".join(lines)


def _generate_with_claude(stats: DailyStats, settings: Settings) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _format_stats_prompt(stats)}],
    )
    text = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()
    if not text:
        raise ValueError("Claude returned an empty summary")
    return text


def generate_summary(logs) -> tuple[str, str]:
    """Return ``(summary_text, model)`` for the given day's logs.

    Falls back to the deterministic summary — and never raises — so a missing
    API key or a transient Anthropic error can't break the dashboard.
    """
    stats = aggregate_stats(logs)
    settings = get_settings()

    # Skip the API on empty days: nothing to summarize, and it saves budget.
    if stats.entry_count == 0 or not settings.anthropic_api_key:
        return build_deterministic_summary(stats), FALLBACK_MODEL

    try:
        return _generate_with_claude(stats, settings), settings.anthropic_model
    except Exception:  # noqa: BLE001 — a demo must never 500 on an API hiccup
        logger.exception("Claude summary generation failed; using fallback")
        return build_deterministic_summary(stats), FALLBACK_MODEL
