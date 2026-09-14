#!/usr/bin/env python3
"""HAKIM · Hawl tracker — the one job that must start NOW.

The hawl is one lunar year of continuously holding wealth at or above the nisab
threshold; zakat becomes due on its hijri anniversary. Whether the streak held
can only be known from a DAILY record of "was I above nisab today?" — it cannot
be reconstructed after the fact. So this job records forward from the first day
it runs and calculates nothing: no zakat is assessed and no fatwa is implied.

It is a thin trigger. All money-math lives in the review-ui (POST /api/hawl/
snapshot), which reads the same account balances the dashboard uses, applies the
nisab from data/zakat.yaml, and appends to data/hawl_trail.json (append-only) +
data/hawl_state.json (derived streak). Idempotent per day — safe to re-run.

Schedule: nightly via launchd (com.hakim.hawl.plist). Manual: make hawl
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

REVIEW_UI = os.environ.get("REVIEW_UI", "http://localhost:8001")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "logs", "hawl.log")
DRY = "--dry" in sys.argv


def log(line):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(f"{datetime.now(timezone.utc).isoformat()} {line}\n")


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    if DRY:
        print(f"[dry] would POST {REVIEW_UI}/api/hawl/snapshot date={today}")
        return 0
    body = json.dumps({"date": today}).encode()
    req = urllib.request.Request(f"{REVIEW_UI}/api/hawl/snapshot", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            st = json.load(r)
    except Exception as e:
        log(f"FAIL {e}")
        print(f"hawl snapshot failed: {e}", file=sys.stderr)
        return 1
    z, n, above = st.get("zakatable"), st.get("nisab"), st.get("above")
    est = " (nisab estimated — set yours in /settings)" if st.get("nisab_estimated") else ""
    start = st.get("hawl_start")
    tail = f"hawl since {start} → due ~{st.get('projected_due')}" if start else "below nisab — clock not running"
    log(f"OK date={today} zakatable={z} nisab={n} above={above} records={st.get('records')} {tail}{est}")
    print(f"hawl: recorded {today} · zakatable={z} nisab={n} above={above} · {tail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
