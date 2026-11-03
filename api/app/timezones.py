"""Per-user timezones, so "today" means the user's local day, not the UTC day.

Logs are stored in UTC. Every day-based view (today's metrics, the 7-day chart,
the AI summary's day) converts a local calendar day into a UTC [start, end)
range and filters on that.

The web app sends the browser's IANA zone in an ``X-Timezone`` header on every
request. We persist it on the user's settings row whenever it changes, so code
that runs without a browser (e.g. the agent) still knows the user's zone.
"""
from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.db_models import UserSettings
from app.models import DEFAULT_BLOCKLIST

UTC = timezone.utc


def parse_zone(name: str | None) -> ZoneInfo | None:
    """An IANA zone like 'Asia/Kolkata', or None if missing/invalid."""
    if not name or len(name) > 64:
        return None
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def resolve_user_timezone(db: Session, user_id: str, header: str | None) -> tzinfo:
    """Header zone if valid (saved when it changed), else the stored zone, else UTC."""
    row = db.get(UserSettings, user_id)
    zone = parse_zone(header)
    if zone is not None:
        if row is None:
            db.add(
                UserSettings(
                    user_id=user_id,
                    blocklist=json.dumps(DEFAULT_BLOCKLIST),
                    blocking_mode="focus-only",
                    timezone=header,
                )
            )
            db.commit()
        elif row.timezone != header:
            row.timezone = header
            db.commit()
        return zone
    stored = parse_zone(row.timezone) if row is not None else None
    return stored or UTC


def get_user_timezone(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_timezone: str | None = Header(default=None),
) -> tzinfo:
    """FastAPI dependency: the caller's timezone."""
    return resolve_user_timezone(db, user_id, x_timezone)


def local_today(tz: tzinfo) -> date:
    return datetime.now(tz).date()


def local_date(dt: datetime, tz: tzinfo) -> date:
    """The user's calendar date for a stored timestamp (naive = UTC)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(tz).date()


def day_range_utc(first: date, last: date, tz: tzinfo) -> tuple[datetime, datetime]:
    """UTC [start, end) covering local days ``first`` through ``last`` inclusive.

    Built from local midnights, so a 23- or 25-hour DST day is handled.
    """
    start = datetime.combine(first, time.min, tzinfo=tz).astimezone(UTC)
    end = datetime.combine(last + timedelta(days=1), time.min, tzinfo=tz).astimezone(UTC)
    return start, end
