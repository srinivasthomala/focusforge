from datetime import datetime, timedelta
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import select, cast, Date
from sqlalchemy.orm import Session

from app.models import DashboardResponse, WeekData
from app.routers.summary import generate_fake_summary
from app.database import get_db
from app.db_models import ActivityLog, activity_log_to_log_entry

router = APIRouter()


def get_real_dashboard_data(db: Session) -> DashboardResponse:
    """
    Calculate dashboard data from activity logs in PostgreSQL.
    """
    today = datetime.now().date()
    week_start = today - timedelta(days=6)

    # Limit to the 7-day window the chart and metrics need
    stmt = select(ActivityLog).where(
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

    # Generate summary using actual today's logs
    ai_summary = generate_fake_summary(today_logs)

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
async def get_dashboard(db: Session = Depends(get_db)):
    """
    Get dashboard data including today's metrics and weekly chart.
    Uses data persisted from the extension.
    """
    return get_real_dashboard_data(db)
