"""Regression fixture — Wealth: allocation + currency exposure sum to assets; net worth is canonical.
Run inside the container:  docker exec hakim-review-ui python3 /app/scripts/check_wealth.py
"""
import sys
sys.path.insert(0, "/app")
import app  # noqa: E402


def main():
    w = app._wealth_impl()
    checks = []
    alloc = round(sum(x["amount"] for x in w["allocation"]), 2)
    checks.append(("allocation sums to assets (%.2f)" % w["assets"], abs(alloc - w["assets"]) < 0.5))
    cur = round(sum(x["amount"] for x in w["currency_exposure"]), 2)
    checks.append(("currency exposure sums to assets", abs(cur - w["assets"]) < 0.5))
    invested = round(sum(x["amount"] for x in w["allocation"]
                         if x["cls"] not in ("Cash", "Bank", "Digital wallets")), 2)
    checks.append(("invested == Σ non-cash classes (%.2f)" % w["invested"], abs(invested - w["invested"]) < 0.01))
    checks.append(("net worth is canonical _networth", abs(w["net_worth"] - app._networth()["net"]) < 0.01))
    for label, ok in checks:
        print(("  OK " if ok else "  XX ") + label)
    allok = all(ok for _, ok in checks)
    print("PASS: Wealth is honest — allocation & currency reconcile to assets, net worth canonical." if allok
          else "FAIL")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
