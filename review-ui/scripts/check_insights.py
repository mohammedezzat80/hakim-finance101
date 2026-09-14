"""Regression fixture — the Insights tab: only supported patterns surface, and it reuses (never rebuilds).
Run inside the container:  docker exec hakim-review-ui python3 /app/scripts/check_insights.py

Asserts: every surfaced "early read" carries a sample label (no unsourced claim); the 3-month patterns
(trend / anomaly) stay in "coming into focus" — NOT surfaced as facts — while maturity is unmet; the
weekday observation only appears once >= 6 weeks exist; and the deeper views LINK to the Reports Sankey and
Subscriptions rather than duplicating them (the audit rule: Insights must reuse the flow-Sankey in Reports).
"""
import sys
sys.path.insert(0, "/app")
import app  # noqa: E402


def main():
    d = app._insights_impl()
    checks = []

    checks.append(("every early read carries a sample label",
                   all(x.get("sample") for x in d["now"])))

    now_kinds = {x["kind"] for x in d["now"]}
    pend_kinds = {p["kind"] for p in d["pending"]}
    if not d["maturity"]["met"]:
        checks.append(("3-month patterns (trend/anomaly) stay pending, not surfaced",
                       {"trend", "anomaly"} <= pend_kinds and not ({"trend", "anomaly"} & now_kinds)))

    checks.append(("weekday observation gated on >= 6 weeks (weeks=%d)" % d["weeks"],
                   ("weekday" in now_kinds) == (d["weeks"] >= 6)))

    checks.append(("links reuse Reports Sankey + Subscriptions (no rebuild)",
                   d["links"]["sankey"].startswith("/reports") and d["links"]["subs"] == "/subscriptions"))

    m = d["maturity"]
    checks.append(("maturity from real ledger (have=%d/%d · %s)" % (m["have"], m["need"], m["ready_label"]),
                   m["have"] == len(app._complete_months())))

    for label, ok in checks:
        print(("  OK " if ok else "  XX ") + label)
    allok = all(ok for _, ok in checks)
    print("PASS: Insights is honest — only supported patterns, samples shown, reuses not rebuilds." if allok
          else "FAIL: Insights lost its honesty.")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
