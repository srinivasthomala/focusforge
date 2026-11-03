"""Agent tests with a scripted fake Claude client: no network, no cost.

They pin down the loop's mechanics (tool dispatch, error results, every stop
reason, limits), tenant isolation in the tools, the quota, and the
confirm-before-write flow.
"""
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import anthropic
import httpx
import pytest

import app.routers.agent as agent_router
from app.agent.loop import AgentLimits, run_agent
from app.agent.tools import TOOL_DEFINITIONS, Toolbox
from app.config import Settings
from app.db_models import ActivityLog, AgentPendingAction, AgentRun, UserSettings
from app.main import app
from app.routers.settings import load_settings
from app.timezones import parse_zone

UTC = timezone.utc
IST = parse_zone("Asia/Kolkata")


# -- fakes ---------------------------------------------------------------------
def text(t):
    return SimpleNamespace(type="text", text=t)


def tool_use(name, input, id="tu_1"):
    return SimpleNamespace(type="tool_use", id=id, name=name, input=input)


def reply(stop_reason, *content, inp=100, out=50):
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=list(content),
        usage=SimpleNamespace(input_tokens=inp, output_tokens=out),
    )


class FakeClient:
    """Returns scripted responses in order and records every request."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []
        self.messages = self

    def create(self, **kwargs):
        # Snapshot the message list: the loop keeps appending to it.
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


class RecordingExecutor:
    def __init__(self, results=None):
        self.calls = []
        self.results = results or {}

    def execute(self, name, raw_input):
        self.calls.append((name, raw_input))
        return self.results.get(name, ('{"ok": true}', False))


def run(client, executor=None, limits=None, clock=None):
    kwargs = {"clock": clock} if clock else {}
    return run_agent(
        client,
        model="claude-haiku-5-5",
        system="sys",
        tools=TOOL_DEFINITIONS,
        messages=[{"role": "user", "content": "How was today?"}],
        executor=executor or RecordingExecutor(),
        limits=limits or AgentLimits(),
        **kwargs,
    )


# -- loop ----------------------------------------------------------------------
def test_tool_call_then_answer():
    client = FakeClient(
        reply("tool_use", tool_use("get_day_stats", {"date": "2026-07-04"})),
        reply("end_turn", text("You focused 30 minutes.")),
    )
    ex = RecordingExecutor()
    r = run(client, ex)
    assert (r.status, r.reply, r.steps) == ("ok", "You focused 30 minutes.", 2)
    assert ex.calls == [("get_day_stats", {"date": "2026-07-04"})]
    # The tool result went back in one user message, matched by tool_use_id.
    sent = client.requests[1]["messages"][-1]
    assert sent["role"] == "user"
    assert sent["content"][0]["tool_use_id"] == "tu_1"
    assert (r.input_tokens, r.output_tokens) == (200, 100)
    assert [t["type"] for t in r.trace] == ["model", "tool", "model"]


def test_parallel_tool_calls_return_together():
    client = FakeClient(
        reply(
            "tool_use",
            tool_use("get_settings", {}, id="a"),
            tool_use("get_day_stats", {"date": "2026-07-04"}, id="b"),
        ),
        reply("end_turn", text("ok")),
    )
    run(client)
    results = client.requests[1]["messages"][-1]["content"]
    assert [x["tool_use_id"] for x in results] == ["a", "b"]


def test_tool_error_is_sent_back_and_the_run_continues():
    client = FakeClient(
        reply("tool_use", tool_use("get_day_stats", {"date": "bad"})),
        reply("end_turn", text("Sorry, which day?")),
    )
    ex = RecordingExecutor({"get_day_stats": ("'bad' is not a valid date", True)})
    r = run(client, ex)
    assert r.status == "ok"
    result = client.requests[1]["messages"][-1]["content"][0]
    assert result["is_error"] is True
    assert r.trace[1]["ok"] is False


def test_step_limit():
    looping = [reply("tool_use", tool_use("get_settings", {})) for _ in range(3)]
    r = run(FakeClient(*looping), limits=AgentLimits(max_steps=3))
    assert r.status == "limit" and r.steps == 3


def test_deadline():
    ticks = iter([0, 0, 1, 1, 100, 100, 100])
    client = FakeClient(*[reply("tool_use", tool_use("get_settings", {})) for _ in range(5)])
    r = run(client, limits=AgentLimits(deadline_seconds=10), clock=lambda: next(ticks))
    assert r.status == "limit" and len(client.requests) == 1


def test_output_token_budget_caps_max_tokens_and_stops():
    client = FakeClient(
        reply("tool_use", tool_use("get_settings", {}), out=900),
        reply("end_turn", text("x")),
    )
    r = run(client, limits=AgentLimits(max_output_tokens=1000, max_tokens_per_call=4000))
    assert client.requests[0]["max_tokens"] == 1000
    assert client.requests[1]["max_tokens"] == 100
    assert r.status == "ok"
    r = run(
        FakeClient(reply("tool_use", tool_use("get_settings", {}), out=1000)),
        limits=AgentLimits(max_output_tokens=1000),
    )
    assert r.status == "limit"


def test_max_tokens_is_reported_as_truncated():
    r = run(FakeClient(reply("max_tokens", text("You focused for"))))
    assert r.status == "truncated" and r.reply.startswith("You focused for")


def test_refusal():
    assert run(FakeClient(reply("refusal"))).status == "refusal"


def test_api_errors_degrade_gracefully():
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    r = run(FakeClient(anthropic.APIConnectionError(request=req)))
    assert r.status == "error" and "try again" in r.reply


def test_effort_and_tools_are_sent():
    client = FakeClient(reply("end_turn", text("hi")))
    run(client)
    assert client.requests[0]["output_config"] == {"effort": "medium"}
    assert {t["name"] for t in client.requests[0]["tools"]} >= {"get_day_stats", "propose_settings_change"}
    assert all(t["strict"] for t in client.requests[0]["tools"])


# -- tools ---------------------------------------------------------------------
def add_log(db, user, when, minutes=0.0, url="session-end", domain="x", focus=True, distraction=False):
    db.add(
        ActivityLog(
            user_id=user, occurred_at=when, url=url, domain=domain,
            minutes_active=minutes, is_focus_session=focus, is_distraction_attempt=distraction,
        )
    )
    db.commit()


def test_day_stats_are_scoped_to_the_user_and_their_local_day(db_session):
    # 20:00 UTC Jul 4 is Jul 5 in India.
    add_log(db_session, "me", datetime(2026, 7, 4, 20, tzinfo=UTC), minutes=40)
    add_log(db_session, "me", datetime(2026, 7, 4, 20, tzinfo=UTC), url="youtube.com",
            domain="youtube.com", distraction=True)
    add_log(db_session, "someone-else", datetime(2026, 7, 4, 20, tzinfo=UTC), minutes=999)
    tb = Toolbox(db_session, "me", IST)
    import json

    out, err = tb.execute("get_day_stats", {"date": "2026-07-05"})
    data = json.loads(out)
    assert not err
    assert data["focus_minutes"] == 40
    assert data["distraction_attempts"] == 1
    assert data["top_distractions"] == ["youtube.com"]
    assert json.loads(tb.execute("get_day_stats", {"date": "2026-07-04"})[0])["has_activity"] is False


def test_breakdown_and_bad_ranges(db_session):
    import json

    tb = Toolbox(db_session, "me", UTC)
    out, err = tb.execute("get_daily_breakdown", {"start_date": "2026-07-01", "end_date": "2026-07-07"})
    assert not err and len(json.loads(out)["days"]) == 7
    assert tb.execute("get_daily_breakdown", {"start_date": "2026-07-07", "end_date": "2026-07-01"})[1]
    assert tb.execute("get_daily_breakdown", {"start_date": "2025-01-01", "end_date": "2026-07-01"})[1]
    future = (date.today() + timedelta(days=5)).isoformat()
    assert tb.execute("get_day_stats", {"date": future})[1]
    assert tb.execute("get_day_stats", {"wrong": 1})[1]
    assert tb.execute("drop_tables", {})[1]


def test_propose_change_does_not_apply_it(db_session):
    import json

    tb = Toolbox(db_session, "me", UTC)
    out, err = tb.execute(
        "propose_settings_change",
        {"add_domains": ["https://www.News.YCombinator.com/item?id=1"], "remove_domains": [], "blocking_mode": None},
    )
    assert not err
    assert json.loads(out)["status"] == "awaiting_user_confirmation"
    assert "news.ycombinator.com" not in load_settings(db_session, "me").blocklist  # untouched
    action = db_session.query(AgentPendingAction).one()
    assert json.loads(action.payload)["add"] == ["news.ycombinator.com"]


def test_noop_change_is_rejected(db_session):
    tb = Toolbox(db_session, "me", UTC)
    # The blocklist starts empty: unblocking a site that isn't blocked, with the
    # mode unchanged, would change nothing.
    _, err = tb.execute(
        "propose_settings_change",
        {"add_domains": [], "remove_domains": ["youtube.com"], "blocking_mode": "focus-only"},
    )
    assert err and db_session.query(AgentPendingAction).count() == 0


# -- router: quota + confirm flow ----------------------------------------------
@pytest.fixture
def agent_env(monkeypatch):
    """Turn the agent on with a fake client; returns a setter for the script."""
    s = Settings(anthropic_api_key="test-key", agent_daily_limit_per_user=2)
    monkeypatch.setattr(agent_router, "get_settings", lambda: s)
    holder = {}

    def script(*responses):
        holder["client"] = FakeClient(*responses)
        app.dependency_overrides[agent_router.get_agent_client] = lambda: holder["client"]
        return holder["client"]

    return script


def test_chat_end_to_end(client, agent_env):
    fake = agent_env(
        reply("tool_use", tool_use("get_settings", {})),
        reply("end_turn", text("You block youtube.com.")),
    )
    r = client.post("/agent/chat", json={"message": "What do I block?"}, headers={"X-Timezone": "Asia/Kolkata"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["reply"] == "You block youtube.com." and body["status"] == "ok"
    assert body["remainingToday"] == 1
    first = fake.requests[0]["messages"][0]["content"]
    assert "timezone Asia/Kolkata" in first and "What do I block?" in first
    assert fake.requests[0]["model"] == "claude-haiku-5-5"


def test_daily_quota(client, agent_env, db_session):
    for _ in range(2):
        agent_env(reply("end_turn", text("hi")))
        assert client.post("/agent/chat", json={"message": "hi"}).status_code == 200
    agent_env(reply("end_turn", text("hi")))
    r = client.post("/agent/chat", json={"message": "hi"})
    assert r.status_code == 429
    assert db_session.query(AgentRun).count() == 2  # the rejected one released its slot
    assert client.get("/agent/quota").json()["remainingToday"] == 0


def test_failed_runs_do_not_use_quota(client, agent_env):
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    agent_env(anthropic.APIConnectionError(request=req))
    body = client.post("/agent/chat", json={"message": "hi"}).json()
    assert body["status"] == "error" and body["remainingToday"] == 2


def test_disabled_without_api_key(client, monkeypatch):
    monkeypatch.setattr(agent_router, "get_settings", lambda: Settings(anthropic_api_key=""))
    assert client.post("/agent/chat", json={"message": "hi"}).status_code == 503


def _propose(client, agent_env):
    agent_env(
        reply("tool_use", tool_use(
            "propose_settings_change",
            {"add_domains": ["news.ycombinator.com"], "remove_domains": [], "blocking_mode": "always"},
        )),
        reply("end_turn", text("Press Confirm to block reddit.com.")),
    )
    body = client.post("/agent/chat", json={"message": "block reddit always"}).json()
    assert len(body["pendingActions"]) == 1
    return body["pendingActions"][0]["id"]


def test_confirm_applies_once(client, agent_env, db_session):
    action_id = _propose(client, agent_env)
    assert "news.ycombinator.com" not in client.get("/settings").json()["blocklist"]

    r = client.post(f"/agent/actions/{action_id}/confirm")
    assert r.status_code == 200 and r.json()["status"] == "applied"
    s = client.get("/settings").json()
    assert s["blockingMode"] == "always"
    assert s["blocklist"].count("news.ycombinator.com") == 1

    # Confirming again is a no-op, not a second change.
    assert client.post(f"/agent/actions/{action_id}/confirm").status_code == 200
    assert client.get("/settings").json()["blocklist"].count("news.ycombinator.com") == 1


def test_cancel_then_confirm_is_refused(client, agent_env):
    action_id = _propose(client, agent_env)
    assert client.post(f"/agent/actions/{action_id}/cancel").status_code == 200
    assert client.post(f"/agent/actions/{action_id}/confirm").status_code == 409
    assert "news.ycombinator.com" not in client.get("/settings").json()["blocklist"]


def test_expired_actions_cannot_be_confirmed(client, agent_env, db_session):
    action_id = _propose(client, agent_env)
    action = db_session.get(AgentPendingAction, action_id)
    action.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()
    assert client.post(f"/agent/actions/{action_id}/confirm").status_code == 410


def test_cannot_confirm_another_users_action(client, agent_env, db_session):
    db_session.add(
        AgentPendingAction(
            user_id="victim", payload='{"add": [], "remove": ["youtube.com"], "blocking_mode": null}',
            summary="Unblock youtube.com", status="pending",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
    )
    db_session.commit()
    other = db_session.query(AgentPendingAction).filter_by(user_id="victim").one()
    assert client.post(f"/agent/actions/{other.id}/confirm").status_code == 404
