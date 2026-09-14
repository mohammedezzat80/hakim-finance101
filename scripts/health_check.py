#!/usr/bin/env python3
"""HAKIM weekly health line — the answer to "did everything actually run?".

Runs on the HOST (launchd, Sundays). Checks every service is up AND that the
background jobs (SMS capture, nightly backup, weekly restore drill) last succeeded
recently. Emits ONE honest line — "✓ all systems ran this week" or
"⚠️ SMS capture last succeeded Tue 14:22" — to logs/health.log + data/health.json,
and (if NTFY_URL is set) pushes it as a notification. Silent death is the only real
enemy of a system like this; this makes silence loud.

  python3 scripts/health_check.py
"""
import json
import os
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS = os.path.join(ROOT, "logs")
# job logs live in TWO places now: launchd-redirected logs (backup, restore-drill) were moved
# OUT of ~/Documents to ~/Library/Logs/hakim to escape the TCC trap; FDA-python jobs (sms,
# brief) still write into ~/Documents/logs. Search both, newest wins.
LOG_DIRS = [os.path.expanduser("~/Library/Logs/hakim"), LOGS]
NTFY_URL = os.environ.get("NTFY_URL", "").strip()   # optional push endpoint


def _find_log(fn):
    cands = [os.path.join(d, fn) for d in LOG_DIRS]
    cands = [p for p in cands if os.path.exists(p)]
    return max(cands, key=os.path.getmtime) if cands else None

SERVICES = [
    ("Firefly III", "http://localhost:8080/", (200, 302)),
    ("Review Desk", "http://localhost:8001/health", (200,)),
    ("Finance agent", "http://localhost:8000/health", (200,)),
    ("Open WebUI", "http://localhost:3000/health", (200,)),
    ("Homepage", "http://localhost:3001/", (200,)),
    ("Uptime Kuma", "http://localhost:3002/", (200,)),
]

# (name, logfile, success-marker, max-age-hours)
JOBS = [
    ("SMS capture", "sms.log", "live:", 12),
    ("Nightly backup", "backup.log", "backup complete", 30),
    ("Restore drill", "restore_drill.log", "PASSED", 24 * 8 + 12),
    ("Morning brief", "brief.log", "ok ·", 30),
    ("Hawl tracker", "hawl.log", "OK ", 30),
]


def check_service(url, ok_codes):
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=6) as r:
            return r.status in ok_codes
    except urllib.error.HTTPError as e:
        return e.code in ok_codes
    except Exception:
        return False


def check_job(logfile, marker, max_age_h):
    p = _find_log(logfile)
    if not p:
        return False, None, "never run"
    age_h = (datetime.now().timestamp() - os.path.getmtime(p)) / 3600
    last = datetime.fromtimestamp(os.path.getmtime(p))
    try:
        tail = "".join(open(p, encoding="utf-8", errors="ignore").readlines()[-25:])
    except Exception:
        tail = ""
    ok = (marker in tail) and (age_h <= max_age_h)
    reason = "ok" if ok else (f"last ok {last:%a %H:%M}" if marker in tail else "last run failed")
    return ok, last, reason


def main():
    svc = [(n, check_service(u, c)) for n, u, c in SERVICES]
    jobs = [(n, *check_job(f, m, a)) for n, f, m, a in JOBS]

    down = [n for n, ok in svc if not ok]
    stale = [(n, r) for n, ok, _, r in jobs if not ok]

    # The 7 agents: 5 log-checked jobs + this health run itself (it's executing → ran) + the
    # event-driven backup-trigger (healthy when the backup is). Name any that didn't run, loudly.
    agent_down = [n for n, ok, _, _ in jobs if not ok]
    if not down and not agent_down:
        line = ("✓ HAKIM: all 7 agents ran this week — nightly-backup, backup-trigger, "
                "restore-drill, health, morning-brief, sms-capture, hawl-tracker all green. Services up.")
    else:
        bits = []
        if down:
            bits.append("services DOWN: " + ", ".join(down))
        if agent_down:
            bits.append("AGENTS NOT RUNNING: " + ", ".join(agent_down))
        for n, r in [(n, r) for n, ok, _, r in jobs if not ok]:
            bits.append(f"{n} — {r}")
        line = "⚠️ HAKIM: " + " · ".join(bits)
    # Dead-man's switch, stated in the message itself: absence of this line is the alarm.
    line += ("  🛡️ You get this every Sunday — if it stops arriving, the health agent itself "
             "is down; check /settings → Agents.")

    report = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "line": line,
        "services": {n: ok for n, ok in svc},
        "jobs": {n: {"ok": ok, "last": (last.isoformat() if last else None), "note": r}
                 for n, ok, last, r in jobs},
    }
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "health.log"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(report, ensure_ascii=False) + "\n")
    with open(os.path.join(ROOT, "data", "health.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    if NTFY_URL:
        try:
            urllib.request.urlopen(urllib.request.Request(
                NTFY_URL, data=line.encode("utf-8"), method="POST"), timeout=8)
        except Exception as e:
            print("ntfy push failed:", e)

    print(line)
    for n, ok in svc:
        print(f"  {'✓' if ok else '✗'} {n}")
    for n, ok, last, r in jobs:
        print(f"  {'✓' if ok else '⚠️'} {n}: {r}")


if __name__ == "__main__":
    main()
