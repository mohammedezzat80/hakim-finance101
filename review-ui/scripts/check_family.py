"""Regression fixture — the Family tab: per-person truth, honestly attributed.
Run inside the container:  docker exec hakim-review-ui python3 /app/scripts/check_family.py

Asserts: each person's this-month spend equals the sum of THEIR tagged withdrawals (no invented
attribution); a person's "pocket" is spendable balances only — never their card/loan debt (a recurring
disease: a Mastercard owned by Sarah must not drag her pocket negative); the spend trend carries one point
per complete-or-current month; and the maturity label is derived from the real ledger.
"""
import sys
sys.path.insert(0, "/app")
import app  # noqa: E402


def main():
    f = app._family_impl()
    txns = app.all_txns()
    curmo = app._date.today().strftime("%Y-%m")
    checks = []

    for p in f["people"]:
        real = round(sum(t["amount"] for t in txns
                         if p["person"] in (t.get("tags") or [])
                         and (t["date"] or "")[:7] == curmo and t["type"] == "withdrawal"), 2)
        checks.append(("%s spend == tagged withdrawals this month (%.2f)" % (p["person"], p["spend"]),
                       abs(p["spend"] - real) < 0.01))
        checks.append(("%s pocket is spendable-only (>= 0: %.2f)" % (p["person"], p["pocket_total"]),
                       p["pocket_total"] >= -0.01))

    ntrend = len(app._complete_months()) + 1   # complete months + the current in-progress one
    if f["people"]:
        checks.append(("trend has one point per month (<= %d)" % ntrend,
                       all(1 <= len(p["trend"]) <= ntrend for p in f["people"])))

    m = f["maturity"]
    checks.append(("maturity from real ledger (have=%d/%d · %s)" % (m["have"], m["need"], m["ready_label"]),
                   m["have"] == len(app._complete_months()) and (m["met"] or bool(m["ready_date"]))))

    for label, ok in checks:
        print(("  OK " if ok else "  XX ") + label)
    allok = all(ok for _, ok in checks)
    print("PASS: Family is honest — real attribution, pockets exclude debt, trend + maturity sound." if allok
          else "FAIL: Family lost its honesty.")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
