#!/usr/bin/env python3
"""HAKIM · Morning Brief — the whisper layer.

Once a day (07:00 via launchd) HAKIM speaks first: a ~6-line ntfy push with
yesterday's flows, cash/cards, the review queue, and the next bill. Read-only,
one-way, honest (placeholder amounts are never printed as numbers).

Reads a single endpoint (/api/brief) on the review-ui — the same ledger sources
the dashboard uses, no new pipeline. Failure is loud: if anything goes wrong a
fallback "brief failed" push is sent instead of a silent skip.

Config lives at the top; the 07:00 schedule itself is the launchd plist.
Manual test:  make brief      (or:  NTFY_URL=... python3 scripts/morning_brief.py --dry)
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

# ---- config ---------------------------------------------------------------
BRIEF_HOUR = 7                                   # documents the launchd schedule
REVIEW_UI = os.environ.get("REVIEW_UI", "http://localhost:8001")
NTFY_URL = os.environ.get("NTFY_URL", "").strip()   # private ntfy topic; unset ⇒ print only
NTFY_TITLE = "HAKIM · Morning brief"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "logs", "brief.log")
DRY = "--dry" in sys.argv

SAR = "SAR"


def log(line):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(f"{datetime.now(timezone.utc).isoformat()} {line}\n")


def snapshot_queue(n):
    """One daily review-queue-size snapshot so the To-review burn-down trend becomes real
    as history accumulates (Loose-ends brief #5). Idempotent per calendar day."""
    p = os.path.join(ROOT, "data", "queue_history.json")
    try:
        hist = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []
    except Exception:
        hist = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    hist = [h for h in hist if h.get("date") != today]
    hist.append({"date": today, "queue": int(n)})
    hist = hist[-400:]
    json.dump(hist, open(p, "w", encoding="utf-8"))


def push(body, title=NTFY_TITLE, priority="default"):
    if DRY or not NTFY_URL:
        return
    req = urllib.request.Request(NTFY_URL, data=body.encode("utf-8"), method="POST")
    req.add_header("Title", title)
    req.add_header("Priority", priority)
    urllib.request.urlopen(req, timeout=10)


def money(n):
    return f"{n:,.0f}"


def compose(d):
    dt = d["date"]
    y = d["yesterday"]
    lines = [f"☀️ HAKIM · {dt['greg']} · {dt['hijri_ar']}"]
    # yesterday
    if not y["count"]:
        lines.append("Yesterday: quiet — no transactions")
    else:
        parts = []
        if y["out"] > 0:
            parts.append(f"−{SAR} {money(y['out'])} out")
        if y["in"] > 0:
            parts.append(f"+{SAR} {money(y['in'])} in")
        parts.append(f"{y['count']} txn" + ("" if y["count"] == 1 else "s"))
        lines.append("Yesterday: " + " · ".join(parts))
    # cash + cards
    lines.append(f"Cash on hand: {SAR} {money(d['cash'])} · Cards: {SAR} {money(d['cards_debt'])}")
    # queue — silence is the reward when empty
    if d["queue"] > 0:
        lines.append(f"Queue: {d['queue']} to answer")
    # next bill — amount only if it is real (never '1.00' / 'not set')
    nb = d.get("next_bill")
    if nb:
        amt = f" {SAR} {money(nb['amount'])}" if nb.get("amount") is not None else ""
        when = "today" if nb["days"] == 0 else ("tomorrow" if nb["days"] == 1 else f"in {nb['days']} days")
        lines.append(f"Next bill: {nb['name']}{amt} · {when}")
    return "\n".join(lines)


def main():
    try:
        with urllib.request.urlopen(REVIEW_UI + "/api/brief", timeout=15) as r:
            data = json.load(r)
        body = compose(data)
        push(body)
        snapshot_queue(data["queue"])
        log("ok · queue=%s · delivered=%s" % (data["queue"], bool(NTFY_URL and not DRY)))
        print(body)
        if not NTFY_URL and not DRY:
            print("\n[NTFY_URL not set — whisper composed but not delivered. "
                  "Set NTFY_URL in com.hakim.morningbrief.plist to push it.]")
    except Exception as e:
        log(f"FAIL {type(e).__name__}: {e}")
        try:
            push("⚠️ Morning brief failed — check logs/brief.log",
                 title="HAKIM · brief FAILED", priority="high")
        except Exception as e2:
            log(f"FALLBACK-PUSH-FAIL {e2}")
        print(f"morning_brief failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
