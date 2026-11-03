from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
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


class AISummary(Base):
    """Cached AI summary, one row per (user, day). Keeps repeat views free."""

    __tablename__ = "ai_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    summary_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "summary_date", name="uq_ai_summary_user_date"),
    )


class AIGenerationEvent(Base):
    """One row per *real* Claude call. Powers the daily cap + per-IP rate limit."""

    __tablename__ = "ai_generation_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_ip: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class ApiKey(Base):
    """A per-user FocusForge API key. The extension (and any device client)
    authenticates with this instead of an interactive Supabase login. Only the
    SHA-256 hash is stored; the raw key is shown to the user exactly once."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    key_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)  # for display
    label: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class UserSettings(Base):
    """Per-user preferences that sync between the web dashboard and the
    extension: the site blocklist and when blocking applies. One row per user."""

    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    blocklist: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON array
    blocking_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="focus-only"
    )
    # IANA zone (e.g. "Asia/Kolkata") from the user's browser; NULL means UTC.
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )



class AgentRun(Base):
    """One row per agent question: the quota counter and the audit trace.

    Inserted with status "running" *before* calling Claude so concurrent
    requests can't race past the per-user and global daily limits.
    """

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    steps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trace: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class AgentPendingAction(Base):
    """A settings change the agent proposed. Nothing is applied until the user
    confirms it in the UI (human-in-the-loop for every write)."""

    __tablename__ = "agent_pending_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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
