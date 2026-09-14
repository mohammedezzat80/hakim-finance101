"""Regression fixture — the Subscriptions tab: honest detection, honest total.
Run inside the container:  docker exec hakim-review-ui python3 /app/scripts/check_subscriptions.py

Asserts: the monthly total is exactly declared + detected (no double-count); every DETECTED-undeclared
charge is subscription-like (stable amount, subscription-sized, ~one/month, not a transfer/fee/ATM — the
noise that "recurs in 2 months" otherwise catches); the unpriced count matches declared bills with no
amount (so the "honest but incomplete" banner is truthful); and maturity is derived from the real ledger.
"""
import sys
import re
sys.path.insert(0, "/app")
import app  # noqa: E402


def main():
    s = app._subs_impl()
    checks = []

    checks.append(("monthly_total == declared + detected (%.2f)" % s["monthly_total"],
                   abs(s["monthly_total"] - (s["declared_monthly"] + s["undeclared_monthly"])) < 0.01))

    EXCL = re.compile(r"تحويل|حوال|transfer|tawarr|financing|fee|رسوم|atm|withdraw|salary|راتب|"
                      r"installment|pos purchase", re.I)
    clean = all(u["stable"] and u["monthly"] <= 3000 and not EXCL.search(u["name"] or "")
                for u in s["undeclared"])
    checks.append(("every detected-undeclared charge is subscription-like (%d found)" % len(s["undeclared"]),
                   clean))

    real_unpriced = sum(1 for d in s["declared"] if not d["known"])
    checks.append(("unpriced count matches declared without amount (%d)" % s["unpriced"],
                   s["unpriced"] == real_unpriced))

    m = s["maturity"]
    checks.append(("maturity from real ledger (have=%d/%d · %s)" % (m["have"], m["need"], m["ready_label"]),
                   m["have"] == len(app._complete_months()) and (m["met"] or bool(m["ready_date"]))))

    for label, ok in checks:
        print(("  OK " if ok else "  XX ") + label)
    allok = all(ok for _, ok in checks)
    print("PASS: Subscriptions is honest — total = declared+detected, detection clean, banner truthful."
          if allok else "FAIL: Subscriptions lost its honesty.")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
