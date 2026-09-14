"""Regression fixture — "needs review" means ONE thing, on every surface.
Run inside the container:  docker exec hakim-review-ui python3 /app/scripts/check_review_parity.py

The review-count fork (the net-worth one-truth lesson, re-learned): the Categories strip counted every
category-LESS row (transfers, ATM withdrawals, card payments, excluded corrections) as "to review" —
7 phantom items · SAR 14,021 — while the Desk queue counted only genuinely undecided rows
(category == "To review") and honestly showed 0. A door that opened onto an empty room.

Canonical definition (the Desk's, the only one): category == REVIEW_CATEGORY ("To review").
This asserts both surfaces compute from that ONE definition:
  • Desk queue count (merchants + one-by-one)      == canonical all-time count
  • Categories strip count (current month)          == canonical month-scoped count
A category-less transfer must NEVER count as review on either surface.
"""
import sys
from datetime import date
sys.path.insert(0, "/app")
import app  # noqa: E402


def main():
    txns = app.all_txns()
    month = date.today().strftime("%Y-%m")

    canon_all = sum(1 for t in txns if t.get("category") == app.REVIEW_CATEGORY)
    canon_month = sum(1 for t in txns
                      if t.get("category") == app.REVIEW_CATEGORY and (t.get("date") or "")[:7] == month)

    q = app.queue()
    desk = sum(g["count"] for g in q["merchants"]) + len(q["onebyone"])

    d = app.categories_data(month)
    catrev = (d.get("review") or {}).get("count", 0)

    ok_desk = desk == canon_all
    ok_cat = catrev == canon_month
    print(f"canonical (category=='{app.REVIEW_CATEGORY}'):  all={canon_all}  month({month})={canon_month}")
    print(f"Desk queue count       = {desk}    ({'OK' if ok_desk else 'XX'} vs canonical all)")
    print(f"Categories strip count = {catrev}    ({'OK' if ok_cat else 'XX'} vs canonical month)")

    if ok_desk and ok_cat:
        print("PASS: one definition, one computation, both surfaces agree.")
        return 0
    print("FAIL: the review count forked — a surface is counting something other than 'To review'.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
