from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

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

router = APIRouter()


def _client_ip(request: Request) -> str:
    """Best-effort client IP, honoring a proxy's X-Forwarded-For first hop."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _enforce_guards(db: Session, client_ip: str) -> None:
    """Raise 429 if the global daily cap or per-IP rate limit is exceeded.

    Only called when a request is actually about to hit Claude, so deterministic
    (empty-day / no-key) responses never consume quota.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)

    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    daily_count = db.scalar(
        select(func.count())
        .select_from(AIGenerationEvent)
        .where(AIGenerationEvent.created_at >= day_start)
    )
    if daily_count >= settings.ai_daily_generation_limit:
        raise HTTPException(
            status_code=429,
            detail="Daily AI summary limit reached. Showing the standard summary instead.",
        )

    window_start = now - timedelta(seconds=settings.ai_rate_limit_window_seconds)
    ip_count = db.scalar(
        select(func.count())
        .select_from(AIGenerationEvent)
        .where(
            AIGenerationEvent.client_ip == client_ip,
            AIGenerationEvent.created_at >= window_start,
        )
    )
    if ip_count >= settings.ai_rate_limit_per_ip:
        raise HTTPException(
            status_code=429,
            detail="You're generating summaries too quickly. Please try again later.",
        )


@router.post("/summary", response_model=SummaryResponse)
async def generate_summary_endpoint(
    payload: SummaryRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SummaryResponse:
    """Generate (or return a cached) AI summary of the user's focus day.

    Triggered explicitly from the dashboard's "Generate" button — never on load.
    """
    today = datetime.now().date()

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

    # Pull today's logs for this user.
    stmt = select(ActivityLog).where(
        ActivityLog.user_id == user_id,
        cast(ActivityLog.occurred_at, Date) == today,
    )
    logs = [activity_log_to_log_entry(r) for r in db.scalars(stmt).all()]

    # Only enforce quota when we're actually going to call Claude.
    settings = get_settings()
    will_call_claude = (
        aggregate_stats(logs).entry_count > 0 and bool(settings.anthropic_api_key)
    )
    if will_call_claude:
        _enforce_guards(db, _client_ip(request))

    summary_text, model = generate_summary(logs)
    now = datetime.now(timezone.utc)

    # Record only genuine Claude calls against the caps.
    if model != FALLBACK_MODEL:
        db.add(
            AIGenerationEvent(
                client_ip=_client_ip(request),
                user_id=user_id,
                created_at=now,
            )
        )

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
