from datetime import date, datetime, timedelta
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import select, cast, Date
from sqlalchemy.orm import Session

from app.activity import resolve_dashboard_date
from app.auth import get_current_user
from app.models import DashboardResponse, LogEntry, WeekData
from app.ai_summary import FALLBACK_MODEL, deterministic_summary_from_logs
from app.database import get_db
from app.db_models import ActivityLog, AISummary, activity_log_to_log_entry

router = APIRouter()


def _log_date(log: LogEntry) -> date | None:
    """Parse a log's ISO timestamp to a date, tolerating a trailing 'Z'."""
    try:
        t = log.timestamp
        if t.endswith("Z"):
            t = t.replace("Z", "+00:00")
        return datetime.fromisoformat(t).date()
    except (ValueError, OSError, TypeError):
        return None


def filter_today(logs: list[LogEntry], today: date) -> list[LogEntry]:
    return [log for log in logs if _log_date(log) == today]


def build_dashboard(
    stored_logs: list[LogEntry],
    today: date,
    ai_summary: str,
    is_today: bool = True,
) -> DashboardResponse:
    """Pure aggregation of a week's logs into the dashboard payload. ``today`` is
    the reference day the metrics center on (see resolve_dashboard_date). Kept
    free of DB access so it can be unit-tested (see tests/test_dashboard.py)."""
    today_logs = filter_today(stored_logs, today)

    today_focus_minutes = sum(
        log.minutesActive for log in today_logs if log.isFocusSession
    )
    today_sessions = sum(1 for log in today_logs if log.url == "session-start")
    distraction_attempts = sum(1 for log in today_logs if log.isDistractionAttempt)

    distracted_domains = [log.domain for log in today_logs if log.isDistractionAttempt]
    top_distractions = [
        domain for domain, _ in Counter(distracted_domains).most_common(2)
    ]

    # Weekly focus minutes, one bucket per day for the last 7 days.
    week_data = []
    for i in range(7):
        target_date = today - timedelta(days=6 - i)
        day_minutes = sum(
            log.minutesActive
            for log in stored_logs
            if log.isFocusSession and _log_date(log) == target_date
        )
        week_data.append(
            WeekData(date=target_date.strftime("%Y-%m-%d"), minutes=int(day_minutes))
        )

    return DashboardResponse(
        todayFocusMinutes=int(today_focus_minutes),
        todaySessions=today_sessions,
        distractionAttempts=distraction_attempts,
        topDistractions=top_distractions,
        aiSummary=ai_summary,
        week=week_data,
        asOf=today.isoformat(),
        isToday=is_today,
    )


def get_real_dashboard_data(db: Session, user_id: str) -> DashboardResponse:
    """Aggregate the 7-day window ending on the user's reference day (today, or
    their most recent active day if today is empty) for the dashboard."""
    reference, is_today = resolve_dashboard_date(db, user_id)
    week_start = reference - timedelta(days=6)

    # Limit to this user and the 7-day window the chart and metrics need.
    stmt = select(ActivityLog).where(
        ActivityLog.user_id == user_id,
        cast(ActivityLog.occurred_at, Date) >= week_start,
        cast(ActivityLog.occurred_at, Date) <= reference,
    )
    stored_logs = [activity_log_to_log_entry(r) for r in db.scalars(stmt).all()]

    # Live deterministic summary by default; surface a cached summary only if it
    # came from a real Claude call (fallback rows are ignored so the summary
    # always tracks the live headline stats). We never call Claude on load.
    ai_summary = deterministic_summary_from_logs(filter_today(stored_logs, reference))
    cached_summary = db.scalars(
        select(AISummary).where(
            AISummary.user_id == user_id,
            AISummary.summary_date == reference,
        )
    ).first()
    if cached_summary is not None and cached_summary.model != FALLBACK_MODEL:
        ai_summary = cached_summary.summary

    return build_dashboard(stored_logs, reference, ai_summary, is_today)


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get dashboard data including today's metrics and weekly chart, scoped to the
    authenticated user.
    """
    return get_real_dashboard_data(db, user_id)
