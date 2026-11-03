from datetime import datetime, timedelta, timezone, tzinfo

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.activity import resolve_dashboard_date
from app.ai_summary import FALLBACK_MODEL, aggregate_stats, generate_summary
from app.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.db_models import (
    ActivityLog,
    AIGenerationEvent,
    AISummary,
    activity_log_to_log_entry,
)
from app.models import SummaryRequest, SummaryResponse
from app.timezones import day_range_utc, get_user_timezone

router = APIRouter()


def _client_ip(request: Request) -> str:
    """Client IP for the audit record only; never used for limits.

    Fly's proxy sets Fly-Client-IP itself (clients can't forge it). Requests
    proxied through Vercel will show a Vercel address, which is fine for a log.
    """
    return request.headers.get("fly-client-ip") or (
        request.client.host if request.client else "unknown"
    )


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _reserve_generation(db: Session, user_id: str, client_ip: str) -> AIGenerationEvent:
    """Claim one slot under the global daily cap and the per-user limit, or 429.

    The slot is inserted and committed *before* counting, so concurrent
    requests can't all pass a check-then-act race: each one counts every
    committed reservation, including its own. Under a burst this errs toward
    rejecting, never toward exceeding the cap. The caller releases the slot
    if Claude ends up not being used.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    event = AIGenerationEvent(client_ip=client_ip, user_id=user_id, created_at=now)
    db.add(event)
    db.commit()

    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    daily_count = db.scalar(
        select(func.count())
        .select_from(AIGenerationEvent)
        .where(AIGenerationEvent.created_at >= day_start)
    )
    window_start = now - timedelta(seconds=settings.ai_rate_limit_window_seconds)
    user_count = db.scalar(
        select(func.count())
        .select_from(AIGenerationEvent)
        .where(
            AIGenerationEvent.user_id == user_id,
            AIGenerationEvent.created_at >= window_start,
        )
    )

    detail = None
    if daily_count > settings.ai_daily_generation_limit:
        detail = "Daily AI summary limit reached. Showing the standard summary instead."
    elif user_count > settings.ai_rate_limit_per_user:
        detail = "You're generating summaries too quickly. Please try again later."
    if detail:
        _release(db, event)
        raise HTTPException(status_code=429, detail=detail)
    return event


def _release(db: Session, event: AIGenerationEvent) -> None:
    db.delete(event)
    db.commit()


@router.post("/summary", response_model=SummaryResponse)
def generate_summary_endpoint(
    payload: SummaryRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    tz: tzinfo = Depends(get_user_timezone),
) -> SummaryResponse:
    """Generate (or return a cached) AI summary of the user's focus day.

    Triggered explicitly from the dashboard's "Generate" button — never on load.
    """
    # Summarize the same day the dashboard shows (today, or the most recent
    # active day) so the button and the headline stats stay in sync.
    today, _ = resolve_dashboard_date(db, user_id, tz)

    cached = db.scalars(
        select(AISummary).where(
            AISummary.user_id == user_id,
            AISummary.summary_date == today,
        )
    ).first()

    if cached is not None and not payload.refresh:
        return SummaryResponse(
            summary=cached.summary,
            model=cached.model,
            cached=True,
            generatedAt=_iso(cached.created_at),
        )

    # Pull this user's logs for that local day.
    start, end = day_range_utc(today, today, tz)
    stmt = select(ActivityLog).where(
        ActivityLog.user_id == user_id,
        ActivityLog.occurred_at >= start,
        ActivityLog.occurred_at < end,
    )
    logs = [activity_log_to_log_entry(r) for r in db.scalars(stmt).all()]

    # Only enforce quota when we're actually going to call Claude.
    settings = get_settings()
    will_call_claude = (
        aggregate_stats(logs).entry_count > 0 and bool(settings.anthropic_api_key)
    )
    reservation = (
        _reserve_generation(db, user_id, _client_ip(request)) if will_call_claude else None
    )

    try:
        summary_text, model = generate_summary(logs)
    except Exception:
        if reservation is not None:
            _release(db, reservation)
        raise
    now = datetime.now(timezone.utc)

    # Only genuine Claude calls count against the caps: if we fell back to the
    # deterministic summary, give the slot back.
    if reservation is not None and model == FALLBACK_MODEL:
        _release(db, reservation)

    # Only persist genuine Claude summaries. Deterministic fallbacks are free to
    # recompute and must always reflect live stats, so caching them would let the
    # dashboard drift out of sync with the headline numbers.
    if model != FALLBACK_MODEL:
        if cached is not None:
            cached.summary = summary_text
            cached.model = model
            cached.created_at = now
        else:
            db.add(
                AISummary(
                    user_id=user_id,
                    summary_date=today,
                    summary=summary_text,
                    model=model,
                    created_at=now,
                )
            )

    db.commit()

    return SummaryResponse(
        summary=summary_text,
        model=model,
        cached=False,
        generatedAt=_iso(now),
    )
