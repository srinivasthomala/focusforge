from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, Text, Boolean, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models import LogEntry


def parse_log_timestamp(s: str) -> datetime:
    t = s.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    return datetime.fromisoformat(t)


def _format_log_timestamp(dt: datetime) -> str:
    if dt.tzinfo is not None:
        s = dt.astimezone(timezone.utc).isoformat()
        return s.replace("+00:00", "Z")
    return f"{dt.isoformat()}Z"


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    minutes_active: Mapped[float] = mapped_column(Float, nullable=False)
    is_focus_session: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_distraction_attempt: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


def log_entry_to_orm(e: LogEntry) -> ActivityLog:
    return ActivityLog(
        user_id=e.userId,
        occurred_at=parse_log_timestamp(e.timestamp),
        url=e.url,
        domain=e.domain,
        minutes_active=e.minutesActive,
        is_focus_session=e.isFocusSession,
        is_distraction_attempt=e.isDistractionAttempt,
    )


def activity_log_to_log_entry(r: ActivityLog) -> LogEntry:
    return LogEntry(
        userId=r.user_id,
        timestamp=_format_log_timestamp(r.occurred_at),
        url=r.url,
        domain=r.domain,
        minutesActive=r.minutes_active,
        isFocusSession=r.is_focus_session,
        isDistractionAttempt=r.is_distraction_attempt,
    )
