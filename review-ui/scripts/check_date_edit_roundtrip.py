"""Regression fixture — editing a transaction's date MOVES it, and the change is visible fresh.
Run inside the review-ui container:  docker exec hakim-review-ui python3 /app/scripts/check_date_edit_roundtrip.py

The "osama marble" bug: an edit wrote to Firefly successfully, but the Calendar tab never refreshed —
its data-version fingerprint (newest transaction only) was blind to an edit of an OLD transaction, so
open tabs kept showing stale months. This asserts BOTH halves of the truth:
  (1) the date write takes effect — the txn leaves its old month and appears in the new one (Calendar
      reads the ledger, not a cache), and
  (2) the data-version fingerprint MOVES on the edit, so open tabs get the reload signal.
Self-contained: books a scratch txn, moves it across months, checks both calendars + the version, cleans.
"""
import sys
sys.path.insert(0, "/app")
import app  # noqa: E402

OLD, NEW = "2026-01-15", "2026-03-20"


def _day_has(month, day, tid):
    days = app.calendar_data(month).get("days", {})
    return any(str(t.get("id")) == tid for t in (days.get(day, {}).get("txns") or []))


def main():
    acc = app.ff_all("accounts", type="asset")
    if not acc:
        print("SKIP: need an asset account"); return 0
    aid = acc[0]["id"]
    r = app.ff("POST", "transactions", {"transactions": [{"type": "withdrawal", "date": OLD,
        "amount": "12.34", "description": "ZZ date-edit fixture", "source_id": aid,
        "destination_name": "ZZ test", "tags": ["zztest", "manual"]}]})
    tid = r["data"]["id"]
    try:
        assert _day_has("2026-01", OLD, tid), "scratch txn not in its starting month"
        v1 = app._data_version()
        # the edit under test
        import asyncio

        class _Req:
            async def json(self):
                return {"id": tid, "date": NEW}
        res = asyncio.new_event_loop().run_until_complete(app.txn_edit(_Req()))
        assert res.get("changed"), f"edit reported no change: {res}"
        v2 = app._data_version()

        moved_in = _day_has("2026-03", NEW, tid)
        left_old = not _day_has("2026-01", OLD, tid)
        version_moved = v1 != v2
        print(f"appears in new month (2026-03-20): {moved_in}")
        print(f"gone from old month (2026-01-15): {left_old}")
        print(f"data-version moved ({v1} -> {v2}): {version_moved}")
        if moved_in and left_old and version_moved:
            print("PASS: date edit moves the transaction AND signals open tabs to refresh.")
            return 0
        print("FAIL: a date edit that doesn't take effect (or doesn't signal) is a write that lied.")
        return 1
    finally:
        app.ff("DELETE", f"transactions/{tid}")


if __name__ == "__main__":
    sys.exit(main())
