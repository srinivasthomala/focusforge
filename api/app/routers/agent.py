"""POST /agent/chat: ask the focus agent a question about your own data.

Also the human-in-the-loop half of writes: the agent can only *propose*
settings changes; POST /agent/actions/{id}/confirm applies one.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone, tzinfo
from typing import List, Literal

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.loop import AgentLimits, run_agent
from app.agent.tools import TOOL_DEFINITIONS, Toolbox
from app.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.db_models import AgentPendingAction, AgentRun
from app.routers.settings import load_settings, save_settings
from app.timezones import day_range_utc, get_user_timezone, local_today

router = APIRouter(prefix="/agent", tags=["agent"])
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the FocusForge focus coach inside the user's dashboard. FocusForge is a \
Chrome extension plus dashboard that tracks focus sessions and blocks distracting sites.

You help with exactly two things: answering questions about this user's own focus data, and \
changing their blocking settings when they ask.

How to work:
- Get every number from a tool. Never guess or invent stats, dates or sites. If the data is \
empty, say so plainly.
- Dates are the user's local calendar days in YYYY-MM-DD. The user message tells you today's \
date; work out "yesterday", "this week" or "last Tuesday" from it.
- To change the blocklist or blocking mode, call propose_settings_change. It does not apply \
anything: tell the user to press Confirm to apply it. Never claim a change is done.
- Only propose changes the user asked for. You may suggest one, but propose it only after they agree.
- If a question is outside focus data and blocking settings, say briefly what you can help with.

Style: short, warm and specific, 1 to 4 sentences, plain text without markdown. Use real figures. \
Do not use em dashes."""

PENDING_ACTION_STATUSES = ("pending", "applied", "cancelled")


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: List[ChatTurn] = Field(default_factory=list, max_length=10)


class PendingActionOut(BaseModel):
    id: int
    summary: str
    status: str
    expiresAt: str


class ChatResponse(BaseModel):
    reply: str
    status: str
    runId: int
    pendingActions: List[PendingActionOut]
    remainingToday: int


class QuotaResponse(BaseModel):
    limit: int
    remainingToday: int
    enabled: bool


def get_agent_client() -> anthropic.Anthropic:
    """Overridable in tests. Short timeout: the loop has its own deadline."""
    s = get_settings()
    return anthropic.Anthropic(api_key=s.anthropic_api_key, timeout=20.0, max_retries=2)


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


# Errors don't use quota: a failed call shouldn't cost the user a question.
_COUNTED = ("running", "ok", "limit", "truncated", "refusal")


def _used_today(db: Session, user_id: str, tz: tzinfo) -> int:
    start, _ = day_range_utc(local_today(tz), local_today(tz), tz)
    return db.scalar(
        select(func.count())
        .select_from(AgentRun)
        .where(
            AgentRun.user_id == user_id,
            AgentRun.created_at >= start,
            AgentRun.status.in_(_COUNTED),
        )
    ) or 0


def _reserve_run(db: Session, user_id: str, tz: tzinfo, question: str, model: str) -> AgentRun:
    """Insert the run first, then count (same reserve-then-count pattern as the
    summary quota), so a burst of requests can't overshoot either limit."""
    s = get_settings()
    run = AgentRun(user_id=user_id, status="running", model=model, question=question)
    db.add(run)
    db.commit()

    utc_midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    global_count = db.scalar(
        select(func.count())
        .select_from(AgentRun)
        .where(AgentRun.created_at >= utc_midnight, AgentRun.status.in_(_COUNTED))
    )
    detail = None
    if global_count > s.agent_daily_limit_global:
        detail = "The focus coach is very busy today. Please try again tomorrow."
    elif _used_today(db, user_id, tz) > s.agent_daily_limit_per_user:
        detail = f"You've used all {s.agent_daily_limit_per_user} questions for today. They reset at midnight."
    if detail:
        db.delete(run)
        db.commit()
        raise HTTPException(status_code=429, detail=detail)
    return run


def _build_messages(req: ChatRequest, tz: tzinfo) -> list[dict]:
    today = local_today(tz)
    zone = getattr(tz, "key", None) or "UTC"
    messages: list[dict] = []
    # Prior turns are text only. Keep them only if they alternate correctly,
    # starting with the user, so a malformed client can't break the request.
    expected = "user"
    for turn in req.history:
        if turn.role != expected:
            messages = []
            break
        messages.append({"role": turn.role, "content": turn.text})
        expected = "assistant" if expected == "user" else "user"
    if messages and messages[-1]["role"] != "assistant":
        messages = []
    messages.append(
        {
            "role": "user",
            "content": f"(Today is {today.isoformat()}, a {today.strftime('%A')}, timezone {zone}.)\n\n{req.message}",
        }
    )
    return messages


def _action_out(a: AgentPendingAction) -> PendingActionOut:
    return PendingActionOut(id=a.id, summary=a.summary, status=a.status, expiresAt=_iso(a.expires_at))


@router.get("/quota", response_model=QuotaResponse)
def agent_quota(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    tz: tzinfo = Depends(get_user_timezone),
) -> QuotaResponse:
    s = get_settings()
    used = _used_today(db, user_id, tz)
    return QuotaResponse(
        limit=s.agent_daily_limit_per_user,
        remainingToday=max(0, s.agent_daily_limit_per_user - used),
        enabled=bool(s.anthropic_api_key),
    )


@router.post("/chat", response_model=ChatResponse)
def agent_chat(
    req: ChatRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    tz: tzinfo = Depends(get_user_timezone),
    client: anthropic.Anthropic = Depends(get_agent_client),
) -> ChatResponse:
    s = get_settings()
    if not s.anthropic_api_key:
        raise HTTPException(status_code=503, detail="The focus coach isn't enabled on this server.")

    run = _reserve_run(db, user_id, tz, req.message, s.agent_model)
    toolbox = Toolbox(db, user_id, tz, run_id=run.id)
    started = time.monotonic()
    result = run_agent(
        client,
        model=s.agent_model,
        effort=s.agent_effort,
        system=SYSTEM_PROMPT,
        tools=TOOL_DEFINITIONS,
        messages=_build_messages(req, tz),
        executor=toolbox,
        limits=AgentLimits(
            max_steps=s.agent_max_steps,
            deadline_seconds=s.agent_deadline_seconds,
            max_output_tokens=s.agent_max_output_tokens,
        ),
    )

    run.status = result.status
    run.reply = result.reply
    run.steps = result.steps
    run.input_tokens = result.input_tokens
    run.output_tokens = result.output_tokens
    run.latency_ms = int((time.monotonic() - started) * 1000)
    run.trace = json.dumps(result.trace, default=str)
    db.commit()
    logger.info(
        "agent run %s user=%s status=%s steps=%d tokens=%d/%d ms=%d tools=%s",
        run.id, user_id, run.status, run.steps, run.input_tokens, run.output_tokens,
        run.latency_ms, [t["name"] for t in result.trace if t["type"] == "tool"],
    )

    return ChatResponse(
        reply=result.reply,
        status=result.status,
        runId=run.id,
        pendingActions=[_action_out(a) for a in toolbox.pending_actions],
        remainingToday=max(0, s.agent_daily_limit_per_user - _used_today(db, user_id, tz)),
    )


def _get_action(db: Session, user_id: str, action_id: int) -> AgentPendingAction:
    action = db.get(AgentPendingAction, action_id)
    if action is None or action.user_id != user_id:
        raise HTTPException(status_code=404, detail="No such action")
    return action


def _expired(action: AgentPendingAction) -> bool:
    exp = action.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) > exp


@router.post("/actions/{action_id}/confirm", response_model=PendingActionOut)
def confirm_action(
    action_id: int,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PendingActionOut:
    """Apply a proposed change. Idempotent: confirming twice applies it once."""
    action = _get_action(db, user_id, action_id)
    if action.status == "applied":
        return _action_out(action)
    if action.status == "cancelled":
        raise HTTPException(status_code=409, detail="This change was cancelled.")
    if _expired(action):
        raise HTTPException(status_code=410, detail="This change expired. Ask the coach again.")

    change = json.loads(action.payload)
    current = load_settings(db, user_id)
    remove = set(change["remove"])
    blocklist = [d for d in current.blocklist if d not in remove]
    blocklist += [d for d in change["add"] if d not in blocklist]
    mode = change["blocking_mode"] or current.blockingMode

    action.status = "applied"
    save_settings(db, user_id, blocklist, mode)  # commits both
    return _action_out(action)


@router.post("/actions/{action_id}/cancel", response_model=PendingActionOut)
def cancel_action(
    action_id: int,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PendingActionOut:
    action = _get_action(db, user_id, action_id)
    if action.status == "applied":
        raise HTTPException(status_code=409, detail="This change was already applied.")
    action.status = "cancelled"
    db.commit()
    return _action_out(action)
