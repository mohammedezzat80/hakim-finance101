"""Regression fixture — the Today tab + THE OPENING's honest-maturity law.
Run inside the container:  docker exec hakim-review-ui python3 /app/scripts/check_today.py

The Opening's universal law: a surface computes what its data supports and names — FROM THE REAL LEDGER,
never hardcoded — how much history a stronger claim needs and the date it's met. This asserts:
  • safe-to-spend is honest arithmetic (cash − committed-remaining), not a guessed buffer;
  • maturity is derived from the actual complete-month count, and its ready-date is real;
  • the dashboard's temporary forward view (next7/heads) was RETIRED when Today shipped (removal condition);
  • Today owns the forward view (due + heads) instead.
"""
import sys
sys.path.insert(0, "/app")
import app  # noqa: E402


def main():
    t = app._today_impl()
    checks = []

    expect = round(t["cash"] - t["committed_remaining"], 2)
    checks.append(("safe_to_spend == cash − committed_remaining (%.2f)" % t["safe_to_spend"],
                   abs(t["safe_to_spend"] - expect) < 0.01))

    m = app._maturity(3)
    real_have = len(app._complete_months())
    maturity_ok = (m["have"] == real_have) and (m["met"] or bool(m["ready_date"]))
    checks.append(("maturity from real ledger (have=%d/%d · ready %s)" % (m["have"], m["need"], m["ready_label"]),
                   maturity_ok))

    d = app._dash_impl("")
    checks.append(("dashboard retired next7/heads (removal condition held)",
                   "next7" not in d and "heads" not in d))

    checks.append(("Today owns the forward view (due + heads present)",
                   "due" in t and "heads" in t))

    for label, ok in checks:
        print(("  OK " if ok else "  XX ") + label)
    allok = all(ok for _, ok in checks)
    print("PASS: Today is honest — arithmetic sound, maturity real, forward view lives here." if allok
          else "FAIL: Today lost its honesty.")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
