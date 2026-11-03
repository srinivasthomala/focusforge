"""The agent's tools: JSON schemas Claude sees, and the code that runs them.

Every tool is bound to one authenticated user (``Toolbox(db, user_id, tz)``),
so the model can never read or change another tenant's data, whatever it puts
in a tool call. Dates are the user's local calendar days.

Reads run immediately. The single write tool, ``propose_settings_change``,
does NOT change anything: it records a pending action that the user must
confirm in the UI. That keeps a human in the loop for every write.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timedelta, timezone, tzinfo
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_summary import aggregate_stats
from app.db_models import ActivityLog, AgentPendingAction, activity_log_to_log_entry
from app.routers.settings import load_settings, normalize_domain
from app.timezones import day_range_utc, local_date, local_today

MAX_RANGE_DAYS = 92
MAX_DOMAINS_PER_CHANGE = 20
PENDING_ACTION_TTL = timedelta(minutes=15)

_DATE = {"type": "string", "description": "Local calendar date, YYYY-MM-DD."}

# strict: true makes the API guarantee the input matches the schema, which
# needs additionalProperties: false and every property listed in required.
# Optional values are expressed as nullable types instead.
TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "get_day_stats",
        "description": (
            "Focus stats for one local day: focused minutes, focus sessions "
            "started, distraction attempts blocked, and the top distracting sites."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"date": _DATE},
            "required": ["date"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_daily_breakdown",
        "description": (
            "Per-day focused minutes, sessions and distraction attempts for an "
            f"inclusive date range (max {MAX_RANGE_DAYS} days). Use it for weeks, "
            "trends and comparisons."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"start_date": _DATE, "end_date": _DATE},
            "required": ["start_date", "end_date"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_top_distractions",
        "description": (
            "Sites the user tried to open while blocked, ranked by attempts, for "
            "an inclusive date range."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": _DATE,
                "end_date": _DATE,
                "limit": {
                    "type": ["integer", "null"],
                    "description": "How many sites to return (1-20). null means 5.",
                },
            },
            "required": ["start_date", "end_date", "limit"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_settings",
        "description": "The user's current blocklist, blocking mode and timezone.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "name": "propose_settings_change",
        "description": (
            "Propose a change to the blocklist and/or blocking mode. This does NOT "
            "apply the change: the user gets a Confirm button and must click it. "
            "Only call this when the user asked for a change. blocking_mode "
            '"focus-only" blocks during focus sessions; "always" blocks all the time.'
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "add_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Domains to block, e.g. reddit.com. May be empty.",
                },
                "remove_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Domains to unblock. May be empty.",
                },
                "blocking_mode": {
                    "anyOf": [
                        {"type": "string", "enum": ["focus-only", "always"]},
                        {"type": "null"},
                    ],
                    "description": "New blocking mode, or null to leave it unchanged.",
                },
            },
            "required": ["add_domains", "remove_domains", "blocking_mode"],
            "additionalProperties": False,
        },
    },
]


class ToolError(Exception):
    """A problem the model can fix (bad date, empty change). Sent back to Claude
    as an is_error tool_result so it can correct itself."""


# Server-side validation as well: strict mode is a guarantee from the API, but
# the executor should never trust input it didn't check.
class _Day(BaseModel):
    date: str


class _Range(BaseModel):
    start_date: str
    end_date: str


class _TopDistractions(_Range):
    limit: int | None = Field(default=None)


class _Change(BaseModel):
    add_domains: list[str]
    remove_domains: list[str]
    blocking_mode: Literal["focus-only", "always"] | None


class _Empty(BaseModel):
    pass


class Toolbox:
    def __init__(self, db: Session, user_id: str, tz: tzinfo, run_id: int | None = None):
        self.db = db
        self.user_id = user_id
        self.tz = tz
        self.run_id = run_id
        self.pending_actions: list[AgentPendingAction] = []

    def execute(self, name: str, raw_input: Any) -> tuple[str, bool]:
        """Run one tool call. Returns ``(content, is_error)``; never raises for
        model mistakes, so one bad call can't crash the whole run."""
        handlers = {
            "get_day_stats": (_Day, self._day_stats),
            "get_daily_breakdown": (_Range, self._daily_breakdown),
            "get_top_distractions": (_TopDistractions, self._top_distractions),
            "get_settings": (_Empty, self._settings),
            "propose_settings_change": (_Change, self._propose_change),
        }
        if name not in handlers:
            return f"Unknown tool: {name}", True
        model, handler = handlers[name]
        try:
            args = model.model_validate(raw_input or {})
            return json.dumps(handler(args)), False
        except ValidationError as e:
            return f"Invalid input: {e.errors(include_url=False)}", True
        except ToolError as e:
            return str(e), True

    # -- helpers ---------------------------------------------------------------
    def _parse_date(self, value: str) -> date:
        try:
            d = date.fromisoformat(value)
        except ValueError:
            raise ToolError(f"'{value}' is not a valid YYYY-MM-DD date") from None
        if d > local_today(self.tz):
            raise ToolError(f"{value} is in the future; there is no data yet")
        return d

    def _range(self, start: str, end: str) -> tuple[date, date]:
        first, last = self._parse_date(start), self._parse_date(end)
        if first > last:
            raise ToolError("start_date must be on or before end_date")
        if (last - first).days + 1 > MAX_RANGE_DAYS:
            raise ToolError(f"Date range is limited to {MAX_RANGE_DAYS} days")
        return first, last

    def _logs(self, first: date, last: date):
        start, end = day_range_utc(first, last, self.tz)
        rows = self.db.scalars(
            select(ActivityLog).where(
                ActivityLog.user_id == self.user_id,
                ActivityLog.occurred_at >= start,
                ActivityLog.occurred_at < end,
            )
        ).all()
        return [(local_date(r.occurred_at, self.tz), activity_log_to_log_entry(r)) for r in rows]

    # -- tools -----------------------------------------------------------------
    def _day_stats(self, args: _Day) -> dict:
        d = self._parse_date(args.date)
        stats = aggregate_stats([log for _, log in self._logs(d, d)])
        return {
            "date": d.isoformat(),
            "focus_minutes": stats.total_minutes,
            "focus_sessions": stats.focus_sessions,
            "distraction_attempts": stats.distraction_attempts,
            "top_distractions": stats.top_distractions,
            "has_activity": stats.entry_count > 0,
        }

    def _daily_breakdown(self, args: _Range) -> dict:
        first, last = self._range(args.start_date, args.end_date)
        by_day: dict[date, list] = {}
        for day, log in self._logs(first, last):
            by_day.setdefault(day, []).append(log)
        days = []
        d = first
        while d <= last:
            s = aggregate_stats(by_day.get(d, []))
            days.append(
                {
                    "date": d.isoformat(),
                    "weekday": d.strftime("%A"),
                    "focus_minutes": s.total_minutes,
                    "focus_sessions": s.focus_sessions,
                    "distraction_attempts": s.distraction_attempts,
                }
            )
            d += timedelta(days=1)
        return {
            "days": days,
            "total_focus_minutes": sum(x["focus_minutes"] for x in days),
        }

    def _top_distractions(self, args: _TopDistractions) -> dict:
        first, last = self._range(args.start_date, args.end_date)
        limit = min(max(args.limit or 5, 1), 20)
        counts = Counter(
            log.domain for _, log in self._logs(first, last) if log.isDistractionAttempt
        )
        return {
            "start_date": first.isoformat(),
            "end_date": last.isoformat(),
            "sites": [{"domain": d, "attempts": n} for d, n in counts.most_common(limit)],
        }

    def _settings(self, _: _Empty) -> dict:
        s = load_settings(self.db, self.user_id)
        tz_name = getattr(self.tz, "key", None) or "UTC"
        return {"blocklist": s.blocklist, "blocking_mode": s.blockingMode, "timezone": tz_name}

    def _propose_change(self, args: _Change) -> dict:
        add = [d for d in (normalize_domain(x) for x in args.add_domains) if d]
        remove = [d for d in (normalize_domain(x) for x in args.remove_domains) if d]
        if len(add) + len(remove) > MAX_DOMAINS_PER_CHANGE:
            raise ToolError(f"At most {MAX_DOMAINS_PER_CHANGE} domains per change")
        if set(add) & set(remove):
            raise ToolError("A domain can't be both added and removed")

        current = load_settings(self.db, self.user_id)
        add = [d for d in add if d not in current.blocklist]
        remove = [d for d in remove if d in current.blocklist]
        mode = args.blocking_mode if args.blocking_mode != current.blockingMode else None
        if not add and not remove and mode is None:
            raise ToolError(
                "Nothing would change: those sites and that mode already match the "
                "current settings. Tell the user instead of proposing a change."
            )

        parts = []
        if add:
            parts.append("block " + ", ".join(add))
        if remove:
            parts.append("unblock " + ", ".join(remove))
        if mode:
            parts.append(f'switch blocking mode to "{mode}"')
        summary = "; ".join(parts).capitalize()

        now = datetime.now(timezone.utc)
        action = AgentPendingAction(
            user_id=self.user_id,
            run_id=self.run_id,
            payload=json.dumps({"add": add, "remove": remove, "blocking_mode": mode}),
            summary=summary,
            status="pending",
            created_at=now,
            expires_at=now + PENDING_ACTION_TTL,
        )
        self.db.add(action)
        self.db.commit()
        self.pending_actions.append(action)
        return {
            "status": "awaiting_user_confirmation",
            "action_id": action.id,
            "summary": summary,
            "note": "Not applied yet. Ask the user to press Confirm.",
        }
