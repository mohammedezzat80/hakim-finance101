"""Regression fixture — a balance correction moves the balance but is INVISIBLE to flow analytics.
Run inside the review-ui container:  docker exec hakim-review-ui python3 /app/scripts/check_corrections.py

The deepest line in the system: the ledger records what HAPPENED (spending/income); a correction records
what we LEARNED (the account's true balance). Only the first is Mohamed's life. Corrections
(balance-correct + cash-count + opening-debt) must move the account balance while being excluded from
every flow view — else a reconciliation nudge reads as a spending catastrophe (Sep 12 once showed
−30,089 "spent" that was really Sarah's opening card debt + balance corrections). This asserts a
correction: (1) moves the account balance by its amount, (2) leaves the month's flow OUT untouched.
Self-contained: nudges a scratch account down, checks both, deletes the correction.
"""
import sys
import asyncio
sys.path.insert(0, "/app")
import app  # noqa: E402


class _Req:
    def __init__(self, body):
        self._b = body

    async def json(self):
        return self._b


def _month_out(ym):
    return round(sum(t["amount"] for t in app.all_txns()
                     if t["type"] == "withdrawal" and (t.get("date") or "")[:7] == ym), 2)


def main():
    acc = app.ff_all("accounts", type="asset")
    if not acc:
        print("SKIP: need an asset account"); return 0
    aid = acc[0]["id"]
    ym = app._date.today().strftime("%Y-%m")

    def bal():
        return next((a["balance"] for a in app.accounts() if a["id"] == aid), None)

    bal0, out0 = bal(), _month_out(ym)
    # nudge the balance DOWN 123.45 → a withdrawal-shaped correction (the dangerous case)
    res = asyncio.new_event_loop().run_until_complete(
        app.balance_correct(_Req({"account_id": aid, "true_balance": round(bal0 - 123.45, 2),
                                  "note": "fixture"})))
    try:
        bal1, out1 = bal(), _month_out(ym)
        moved = abs((bal0 - bal1) - 123.45) < 0.02
        flow_untouched = abs(out1 - out0) < 0.02
        print(f"balance moved by correction: {bal0} -> {bal1}  ({'OK' if moved else 'XX'})")
        print(f"month OUT (flow) untouched : {out0} -> {out1}  ({'OK' if flow_untouched else 'XX'})")
        if moved and flow_untouched:
            print("PASS: correction moves balance, invisible to flow analytics.")
            return 0
        print("FAIL: a correction leaked into flow analytics (or didn't move the balance).")
        return 1
    finally:
        # delete the scratch correction (the ⚖ excluded withdrawal we just made on this account today)
        today = app._date.today().isoformat()
        for t in app.all_txns(include_excluded=True):
            if (t.get("date") == today and "correction" in (t.get("tags") or [])
                    and str(t.get("source_id")) == aid and abs(t["amount"] - 123.45) < 0.02):
                app.ff("DELETE", f"transactions/{t['id']}")
                break


if __name__ == "__main__":
    sys.exit(main())
