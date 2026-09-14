"""Regression fixture — two-sided transfer visibility (the Money Pro law).
Run inside the review-ui container:  docker exec hakim-review-ui python3 /app/scripts/check_transfer_visibility.py
Asserts a transfer between two owned accounts shows in BOTH accounts' views, with opposite
direction-aware signs ("⇄ to X −amt" / "⇄ from X +amt"), then cleans up. Part of the self-check
ritual so one-sided-filtering can't quietly return in a refactor.
"""
import sys
sys.path.insert(0, "/app")
import app  # noqa: E402


def main():
    assets = [x for x in app._balance_accounts() if x["type"] == "asset" and x["role"] != "ccAsset"]
    if len(assets) < 2:
        print("SKIP: need two asset accounts"); return 0
    a, b = assets[0], assets[1]
    c = app.ff("POST", "transactions", {"error_if_duplicate_hash": False, "transactions": [
        {"type": "transfer", "date": "2026-09-10", "amount": "123.00",
         "description": "ZZ regression transfer", "source_id": a["id"], "destination_id": b["id"]}]})
    tid = c["data"]["id"]
    try:
        ra = [r for r in app.account_series(a["name"])["recent"] if r["id"] == tid]
        rb = [r for r in app.account_series(b["name"])["recent"] if r["id"] == tid]
        ok = bool(ra) and bool(rb) and ra[0]["signed"] < 0 and rb[0]["signed"] > 0 \
            and "⇄ to" in ra[0]["name"] and "⇄ from" in rb[0]["name"]
        print(f"{a['name']}: {[(r['name'], r['signed']) for r in ra]}")
        print(f"{b['name']}: {[(r['name'], r['signed']) for r in rb]}")
        print("PASS: two-sided transfer visible in both accounts" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        app.ff("DELETE", f"transactions/{tid}")


if __name__ == "__main__":
    sys.exit(main())
