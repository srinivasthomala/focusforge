#!/usr/bin/env python3
"""Seed a FocusForge account with a realistic week of activity — for demo
screenshots. Posts backdated logs to the live API using an account's API key
(the same ingest path the extension uses), so no DB access is needed.

Usage:
    python scripts/seed_demo_data.py --api-key ff_xxx [--base-url URL] [--dry-run]

Get an API key from the web app: Settings -> API Keys -> Generate key.
Run against a *fresh* demo account so the data is clean.
"""

from __future__ import annotations

import argparse
import json
import random
import urllib.request
from datetime import datetime, time, timedelta, timezone

DEFAULT_BASE_URL = "https://focusforge-api.fly.dev"
DISTRACTORS = ["youtube.com", "twitter.com", "reddit.com"]

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
            start = datetime.combine(
                day,
                time(hour=9 + idx * 2, minute=random.randint(0, 45)),
                tzinfo=timezone.utc,
            )
            end = start + timedelta(minutes=length)
            # Never place today's activity in the future.
            if is_today and end > now:
                end = now - timedelta(minutes=random.randint(2, 20))
                start = end - timedelta(minutes=length)
                if start < datetime.combine(day, time.min, tzinfo=timezone.utc):
                    continue  # session wouldn't fit before "now"; skip it

            logs.append(_marker(start, "session-start"))
            if random.random() < 0.55:  # an occasional blocked distraction
                when = start + timedelta(minutes=random.randint(1, max(1, length - 1)))
                domain = random.choice(DISTRACTORS)
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
    parser.add_argument("--api-key", help="FocusForge API key (ff_...)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--dry-run", action="store_true", help="Print the plan; don't post.")
    parser.add_argument("--seed", type=int, default=7, help="RNG seed for reproducibility.")
    args = parser.parse_args()

    random.seed(args.seed)
    logs = build_week(datetime.now(timezone.utc))

    print(f"Generated {len(logs)} log entries across the last 7 days:\n")
    summarize(logs)

    if args.dry_run:
        print("\n(dry run: nothing posted)")
        return
    if not args.api_key:
        parser.error("--api-key is required unless --dry-run is set")
    print()
    post_logs(args.base_url, args.api_key, logs)


if __name__ == "__main__":
    main()
