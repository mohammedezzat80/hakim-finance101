"""Regression fixture — the Debt coach: real numbers, honest ordering, gated recommendation.
Run inside the container:  docker exec hakim-review-ui python3 /app/scripts/check_debt.py

Asserts: total debt equals the sum of the listed balances; snowball is ordered smallest-balance-first;
avalanche never ranks an interest-free (0%) debt above an interest-bearing one; and the payoff-timeline
recommendation stays GATED whenever there's no validated positive surplus (a plan on a surplus that isn't
there is exactly the guess this system refuses).
"""
import sys
sys.path.insert(0, "/app")
import app  # noqa: E402


def main():
    d = app._debt_impl()
    by = {x["name"]: x for x in d["debts"]}
    checks = []

    checks.append(("total_debt == Σ listed balances (%.2f)" % d["total_debt"],
                   abs(d["total_debt"] - round(sum(x["balance"] for x in d["debts"]), 2)) < 0.01))

    sb = [by[n]["balance"] for n in d["snowball"]]
    checks.append(("snowball is smallest-balance-first", sb == sorted(sb)))

    # avalanche: no zero-interest debt ranked above an interest-bearing one
    av = [by[n] for n in d["avalanche"]]
    last_nonzero = max((i for i, x in enumerate(av) if not x["zero"]), default=-1)
    first_zero = next((i for i, x in enumerate(av) if x["zero"]), len(av))
    checks.append(("avalanche keeps 0%% debts last", first_zero > last_nonzero))

    checks.append(("minimums total == Σ mins (%.2f)" % d["min_total"],
                   abs(d["min_total"] - round(sum(x["min"] or 0 for x in d["debts"]), 2)) < 0.01))

    gated_ok = d["surplus_validated"] == (d["avg_net"] > 0 and d["maturity"]["met"])
    checks.append(("payoff plan gated unless surplus is validated (avg_net %.0f · validated=%s)"
                   % (d["avg_net"], d["surplus_validated"]), gated_ok))

    m = d["maturity"]
    checks.append(("maturity from real ledger (have=%d/%d)" % (m["have"], m["need"]),
                   m["have"] == len(app._complete_months())))

    for label, ok in checks:
        print(("  OK " if ok else "  XX ") + label)
    allok = all(ok for _, ok in checks)
    print("PASS: Debt coach is honest — real totals, sound ordering, recommendation gated." if allok
          else "FAIL: Debt coach lost its honesty.")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
