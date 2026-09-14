#!/usr/bin/env python3
"""Delete ALL transactions from Firefly III — leaves the v2 structure
(accounts, categories, tags, bills) intact.

Use to clear test/entry mistakes without rebuilding the structure. Requires a
valid token (FIREFLY_ADMIN_TOKEN or FIREFLY_PAT). Refuses unless CONFIRM=1.

  CONFIRM=1 python3 scripts/reset_ledger.py
"""
import os

from _ff import Firefly, load_env


def main():
    if os.environ.get("CONFIRM") != "1":
        raise SystemExit("This deletes ALL transactions. Re-run with CONFIRM=1 to proceed.")

    env = load_env()
    admin = (env.get("FIREFLY_ADMIN_TOKEN") or "").strip()
    if admin:
        env["FIREFLY_PAT"] = admin
    ff = Firefly(env)

    txns = ff.get_all("transactions")
    print(f"Deleting {len(txns)} transaction(s) ...")
    for t in txns:
        ff._req("DELETE", f"transactions/{t['id']}")
    remaining = ff.get("transactions", limit=1).get("meta", {}).get("pagination", {}).get("total", 0)
    print(f"Done. Transactions remaining: {remaining}")
    print("(Structure — accounts, categories, tags, bills — left intact.)")


if __name__ == "__main__":
    main()
