from datetime import datetime, timedelta
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import select, cast, Date
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.models import DashboardResponse, WeekData
from app.ai_summary import FALLBACK_MODEL, deterministic_summary_from_logs
from app.database import get_db
from app.db_models import ActivityLog, AISummary, activity_log_to_log_entry

router = APIRouter()


def get_real_dashboard_data(db: Session, user_id: str) -> DashboardResponse:
    """
    Calculate dashboard data from the authenticated user's activity logs.
    """
    today = datetime.now().date()
    week_start = today - timedelta(days=6)

    # Limit to this user and the 7-day window the chart and metrics need
    stmt = select(ActivityLog).where(
        ActivityLog.user_id == user_id,
        cast(ActivityLog.occurred_at, Date) >= week_start,
        cast(ActivityLog.occurred_at, Date) <= today,
    )
    stored_logs = [activity_log_to_log_entry(r) for r in db.scalars(stmt).all()]

    # Filter logs for today
    today_logs = []
    for log in stored_logs:
        try:
            t = log.timestamp
            if t.endswith("Z"):
                t = t.replace("Z", "+00:00")
            log_date = datetime.fromisoformat(t).date()
            if log_date == today:
                today_logs.append(log)
        except (ValueError, OSError, TypeError):
            continue

    # Calculate metrics
    today_focus_minutes = sum(
        log.minutesActive for log in today_logs if log.isFocusSession
    )
    today_sessions = sum(1 for log in today_logs if log.url == "session-start")
    distraction_attempts = sum(
        1 for log in today_logs if log.isDistractionAttempt
    )

    # Get top distractions
    distracted_domains = [
        log.domain for log in today_logs if log.isDistractionAttempt
    ]
    top_distractions = [
        domain for domain, _ in Counter(distracted_domains).most_common(2)
    ]

    # Show the cached AI summary if one was generated today; otherwise fall back
    # to the free deterministic summary. We never call Claude on dashboard load.
    # Live deterministic summary by default; surface a cached summary only if it
    # came from a real Claude call (fallback rows are ignored so the summary
    # always tracks the live headline stats).
    ai_summary = deterministic_summary_from_logs(today_logs)
    cached_summary = db.scalars(
        select(AISummary).where(
            AISummary.user_id == user_id,
            AISummary.summary_date == today,
        )
    ).first()
    if cached_summary is not None and cached_summary.model != FALLBACK_MODEL:
        ai_summary = cached_summary.summary

    # Calculate weekly data (last 7 days)
    week_data = []
    for i in range(7):
        target_date = today - timedelta(days=6 - i)

        # Sum minutes for this specific day
        day_minutes = 0
        for log in stored_logs:
            try:
                t = log.timestamp
                if t.endswith("Z"):
                    t = t.replace("Z", "+00:00")
                log_date = datetime.fromisoformat(t).date()
                if log_date == target_date and log.isFocusSession:
                    day_minutes += log.minutesActive
            except (ValueError, OSError, TypeError):
                continue

        week_data.append(
            WeekData(
                date=target_date.strftime("%Y-%m-%d"),
                minutes=int(day_minutes),
            )
        )

    return DashboardResponse(
        todayFocusMinutes=int(today_focus_minutes),
        todaySessions=today_sessions,
        distractionAttempts=distraction_attempts,
        topDistractions=top_distractions,
        aiSummary=ai_summary,
        week=week_data,
    )


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
