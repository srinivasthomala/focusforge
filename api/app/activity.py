"""Shared helper for choosing which day the dashboard and summary center on."""

from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db_models import ActivityLog


def resolve_dashboard_date(db: Session, user_id: str) -> tuple[date, bool]:
    """Return ``(reference_date, is_today)``.

    Centers the dashboard on **today** when there's activity today; otherwise on
    the user's **most recent active day**, so the view never goes blank after a
    break (or when a demo account has been idle). Falls back to today when the
    user has no logs at all.
    """
    # Logs are stored as UTC, so "today" must be the UTC date too. A naive
    # local now() only matched by accident because the server runs in UTC.
    today = datetime.now(timezone.utc).date()
    latest = db.scalar(
        select(func.max(ActivityLog.occurred_at)).where(ActivityLog.user_id == user_id)
    )
    if latest is None:
        return today, True
    reference = min(today, latest.date())
    return reference, reference == today
