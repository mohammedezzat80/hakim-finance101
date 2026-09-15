"""Regression fixture — pages stay fast as the ledger grows. (Perf ceiling guard.)
Run inside the review-ui container:  docker exec hakim-review-ui python3 /app/scripts/check_perf.py

The reading layer (all_txns) fetches + normalizes the whole ledger; uncached it cost ~550ms EVERY call,
and a dashboard hits it several times → seconds (felt the night Sarah's 424 txns landed). It is now cached
on the data-version fingerprint. This asserts the warm path stays under budget so slowness gets caught by
the ritual before Mohamed feels it — and flags the NEXT ceiling as the ledger keeps growing.
"""
import sys
import time
sys.path.insert(0, "/app")
import app  # noqa: E402

BUDGET = {"all_txns (warm)": 0.15, "dashboard": 0.1, "Desk queue": 0.1, "accounts": 0.15}


def _t(fn):
    t = time.time()
    fn()
    return time.time() - t


def main():
    n = len(app.all_txns())            # warm the cache
    app.dash("")            # prime the version-keyed view caches
    app.queue()
    checks = [
        ("all_txns (warm)", lambda: app.all_txns()),
        ("dashboard", lambda: app.dash("")),         # version-cached → flat at any ledger size
        ("Desk queue", lambda: app.queue()),
        ("accounts", lambda: app.accounts()),
    ]
    bad = []
    print(f"ledger size: {n} transactions")
    for name, fn in checks:
        dur = min(_t(fn) for _ in range(3))   # best of 3 (warm)
        ok = dur <= BUDGET[name]
        print(f"  {'OK ' if ok else 'XX '}{name}: {dur*1000:.0f}ms  (budget {BUDGET[name]*1000:.0f}ms)")
        if not ok:
            bad.append(name)
    # anticipate the next ceiling: the cache makes reads O(1) between writes, but each cache MISS still
    # re-fetches + re-normalizes the whole ledger. At ~0.8ms/txn that's ~0.5s at 688 and would approach
    # ~8s at 10k — the miss cost (not the hit) is the next ceiling. Before then: incremental/paged fetch
    # or a persistent normalized store keyed by journal id. Noted in STATE.md.
    if bad:
        print("FAIL: a warm page exceeded its budget — the reading layer needs attention.")
        return 1
    print("PASS: warm pages within budget.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
