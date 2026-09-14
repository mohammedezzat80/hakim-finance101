"""Regression fixture — the Forecast tab: the KNOWN curve is arithmetically sound and the split between
known and inferred is honest.
Run inside the container:  docker exec hakim-review-ui python3 /app/scripts/check_forecast.py

The most honesty-sensitive tab: a 90-day curve on 2 months of history. Asserts the known line starts at
today's cash and ends at cash + the sum of every dated obligation (no phantom drift); the lowest point and
the negative-crossing date are truthful; the provisional daily burn is non-negative (a modelled overlay,
never baked into the confident line); and maturity is derived from the real ledger.
"""
import sys
sys.path.insert(0, "/app")
import app  # noqa: E402


def main():
    f = app._forecast_impl()
    s = f["series"]
    checks = []

    checks.append(("known curve starts at today's cash (%.2f)" % f["cash0"],
                   abs(s[0]["bal"] - f["cash0"]) < 0.01 or abs(s[0]["bal"] - (f["cash0"] + sum(
                       e["amount"] for e in f["events"] if e["date"] == f["today"]))) < 0.01))

    evt_sum = sum(e["amount"] for e in f["events"])
    checks.append(("end_known == cash0 + Σ dated events (%.2f)" % f["end_known"],
                   abs(f["end_known"] - round(f["cash0"] + evt_sum, 2)) < 0.01))

    lo = min(p["bal"] for p in s)
    checks.append(("lowest point is the true minimum (%.2f)" % f["lowest"]["bal"],
                   abs(f["lowest"]["bal"] - lo) < 0.01))

    first_neg = next((p["date"] for p in s if p["bal"] < 0), None)
    checks.append(("negative-crossing date is truthful (%s)" % f["neg_date"], f["neg_date"] == first_neg))

    checks.append(("provisional daily burn is non-negative (%.2f)" % f["disc_daily"], f["disc_daily"] >= 0))

    m = f["maturity"]
    checks.append(("maturity from real ledger (have=%d/%d · %s)" % (m["have"], m["need"], m["ready_label"]),
                   m["have"] == len(app._complete_months()) and (m["met"] or bool(m["ready_date"]))))

    for label, ok in checks:
        print(("  OK " if ok else "  XX ") + label)
    allok = all(ok for _, ok in checks)
    print("PASS: Forecast is honest — known curve sound, crunch date truthful, inference labelled." if allok
          else "FAIL: Forecast lost its honesty.")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
