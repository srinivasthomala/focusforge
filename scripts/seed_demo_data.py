#!/usr/bin/env python3
"""Seed a FocusForge account with a realistic week of activity — for demo
screenshots. Posts backdated logs to the live API using an account's API key
(the same ingest path the extension uses), so no DB access is needed.

Usage:
    python scripts/seed_demo_data.py [--base-url URL] [--dry-run]

It asks for the API key with a hidden prompt (or reads FOCUSFORGE_API_KEY),
so the key never appears on screen or in shell history.

Get an API key from the web app: Settings -> API Keys -> Generate key.
Run against a *fresh* demo account so the data is clean.
"""

from __future__ import annotations

import argparse
import getpass
import os
import json
import random
import urllib.request
from datetime import datetime, time, timedelta, timezone

DEFAULT_BASE_URL = "https://focusforge-api.fly.dev"
DISTRACTORS = ["youtube.com", "x.com", "reddit.com", "instagram.com"]
BLOCKLIST = ["youtube.com", "x.com", "reddit.com", "instagram.com", "netflix.com"]

# Target focus minutes per day, oldest -> today. Varied so the weekly chart
# looks alive rather than flat.
DAILY_TARGETS = [95, 140, 65, 175, 120, 50, 135]


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _session_lengths(total: int, n: int) -> list[int]:
    """Split `total` minutes into `n` sessions of at least 15 min each."""
    lengths = []
    remaining = total
    for s in range(n):
        left = n - s
        if left == 1:
            lengths.append(max(15, remaining))
        else:
            hi = remaining - 15 * (left - 1)
            chunk = max(15, min(hi, remaining // left + random.randint(-10, 10)))
            lengths.append(chunk)
            remaining -= chunk
    return lengths


def build_week(now: datetime) -> list[dict]:
    logs: list[dict] = []
    today = now.date()

    for i, target in enumerate(DAILY_TARGETS):
        day = today - timedelta(days=len(DAILY_TARGETS) - 1 - i)
        is_today = day == today
        n = random.randint(2, 4)
        lengths = _session_lengths(target, n)

        # Space sessions through the working day (09:00, 11:30, 14:00, ...).
        for idx, length in enumerate(lengths):
            # Sessions at local working hours (09:00, 11:00, 14:00, 16:00 ...).
            start = datetime.combine(
                day,
                time(hour=(9, 11, 14, 16, 18)[idx], minute=random.randint(0, 40)),
                tzinfo=now.tzinfo,
            )
            end = start + timedelta(minutes=length)
            # Never place today's activity in the future.
            if is_today and end > now:
                end = now - timedelta(minutes=random.randint(2, 20))
                start = end - timedelta(minutes=length)
                if start < datetime.combine(day, time.min, tzinfo=now.tzinfo):
                    continue  # session wouldn't fit before "now"; skip it

            logs.append(_marker(start, "session-start"))
            # Blocked distractions: youtube.com most often, so the coach has
            # a clear "top distraction" to talk about.
            for _ in range(random.choice((0, 1, 1, 2, 3))):
                when = start + timedelta(minutes=random.randint(1, max(1, length - 1)))
                domain = random.choices(DISTRACTORS, weights=(5, 3, 2, 1))[0]
                logs.append({
                    "timestamp": _iso(when),
                    "url": f"https://{domain}/",
                    "domain": domain,
                    "minutesActive": 0,
                    "isFocusSession": True,
                    "isDistractionAttempt": True,
                })
            logs.append({
                "timestamp": _iso(end),
                "url": "session-end",
                "domain": "system",
                "minutesActive": float(length),
                "isFocusSession": True,
                "isDistractionAttempt": False,
            })
    return logs


def _marker(dt: datetime, url: str) -> dict:
    return {
        "timestamp": _iso(dt),
        "url": url,
        "domain": "system",
        "minutesActive": 0,
        "isFocusSession": True,
        "isDistractionAttempt": False,
    }


def summarize(logs: list[dict]) -> None:
    by_day: dict[str, dict] = {}
    for log in logs:
        day = log["timestamp"][:10]
        d = by_day.setdefault(day, {"minutes": 0.0, "sessions": 0, "distractions": 0})
        d["minutes"] += log["minutesActive"] if log["isFocusSession"] else 0
        if log["url"] == "session-start":
            d["sessions"] += 1
        if log["isDistractionAttempt"]:
            d["distractions"] += 1
    print(f"{'date':<12}{'minutes':>9}{'sessions':>10}{'distractions':>14}")
    for day in sorted(by_day):
        d = by_day[day]
        print(f"{day:<12}{int(d['minutes']):>9}{d['sessions']:>10}{d['distractions']:>14}")


def set_blocklist(base_url: str, api_key: str) -> None:
    body = json.dumps({"blocklist": BLOCKLIST, "blockingMode": "focus-only"}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/settings",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="PUT",
    )
    with urllib.request.urlopen(req) as resp:
        resp.read()
    print("Blocked sites set:", ", ".join(BLOCKLIST))


def post_logs(base_url: str, api_key: str, logs: list[dict]) -> None:
    body = json.dumps({"logs": logs}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/logs",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        print("Server response:", resp.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed FocusForge with demo activity.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--dry-run", action="store_true", help="Print the plan; don't post.")
    parser.add_argument("--seed", type=int, default=7, help="RNG seed for reproducibility.")
    args = parser.parse_args()

    random.seed(args.seed)
    logs = build_week(datetime.now().astimezone())  # local time zone

    print(f"Generated {len(logs)} log entries across the last 7 days:\n")
    summarize(logs)

    if args.dry_run:
        print("\n(dry run: nothing posted)")
        return
    api_key = os.environ.get("FOCUSFORGE_API_KEY") or getpass.getpass("\nPaste the demo account's API key (hidden): ")
    api_key = api_key.strip()
    if not api_key.startswith("ff_"):
        raise SystemExit("That isn't a FocusForge key (they start with ff_).")
    print()
    set_blocklist(args.base_url, api_key)
    post_logs(args.base_url, api_key, logs)


if __name__ == "__main__":
    main()
