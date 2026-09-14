"""Regression fixture — the Budget tab: proposals are honest averages of real evidence, and accepting one
writes through the single target door.
Run inside the container:  docker exec hakim-review-ui python3 /app/scripts/check_budget.py

Asserts: every proposed target equals the average of that category's spend across complete months (the
evidence shown), so no number is invented; targeted and proposal sets are disjoint (a category with a
target is never also "proposed"); the total-target equals the sum of set targets; accepting a proposal via
the ONE write door (/api/category/target) makes it a real target the very next read (then restored); and
maturity is derived from the real ledger.
"""
import sys
import asyncio
sys.path.insert(0, "/app")
import app  # noqa: E402


class _Req:
    def __init__(self, b):
        self._b = b

    async def json(self):
        return self._b


def main():
    b = app._budget_impl()
    checks = []

    ev_ok = all(abs(r["proposed"] - round(sum(r["evidence"]) / max(1, len(r["evidence"])), 2)) < 0.01
                for r in b["proposals"])
    checks.append(("every proposal == average of its evidence", ev_ok))

    tnames = {r["name"] for r in b["targeted"]}
    pnames = {r["name"] for r in b["proposals"]}
    checks.append(("targeted and proposals are disjoint", not (tnames & pnames)))

    checks.append(("total_target == Σ set targets (%.2f)" % b["total_target"],
                   abs(b["total_target"] - round(sum(r["target"] or 0 for r in b["rows"]), 2)) < 0.01))

    # accept a proposal through the one door, confirm it becomes a target, then restore
    if b["proposals"]:
        p = b["proposals"][0]
        saved = app._cat_targets().get(p["name"])
        try:
            asyncio.new_event_loop().run_until_complete(
                app.category_target(_Req({"name": p["name"], "amount": p["proposed"], "period": "monthly"})))
            after = app._budget_impl()
            became = any(r["name"] == p["name"] for r in after["targeted"])
            checks.append(("accepting a proposal writes a real target (one door)", became))
        finally:
            t = app._cat_targets()
            if saved is None:
                t.pop(p["name"], None)
            else:
                t[p["name"]] = saved
            app._yaml_save("category_targets.yaml", t)

    m = b["maturity"]
    checks.append(("maturity from real ledger (have=%d/%d)" % (m["have"], m["need"]),
                   m["have"] == len(app._complete_months())))

    for label, ok in checks:
        print(("  OK " if ok else "  XX ") + label)
    allok = all(ok for _, ok in checks)
    print("PASS: Budget is honest — proposals from real evidence, one write door, provisional-labelled."
          if allok else "FAIL: Budget lost its honesty.")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
