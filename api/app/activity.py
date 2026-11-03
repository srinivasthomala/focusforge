"""Shared helper for choosing which day the dashboard and summary center on."""

from datetime import date, tzinfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db_models import ActivityLog
from app.timezones import local_date, local_today


def resolve_dashboard_date(db: Session, user_id: str, tz: tzinfo) -> tuple[date, bool]:
    """Return ``(reference_date, is_today)`` as dates in the user's timezone.

    Centers the dashboard on **today** when there's activity today; otherwise on
    the user's **most recent active day**, so the view never goes blank after a
    break (or when a demo account has been idle). Falls back to today when the
    user has no logs at all.
    """
    today = local_today(tz)
    latest = db.scalar(
        select(func.max(ActivityLog.occurred_at)).where(ActivityLog.user_id == user_id)
    )
    if latest is None:
        return today, True
    reference = min(today, local_date(latest, tz))
    return reference, reference == today
