"""Regression fixture — a YAML config write is reflected by the very NEXT cached read.
Run inside the container:  docker exec hakim-review-ui python3 /app/scripts/check_config_cache.py

The stale-config class (fixed twice the hard way): a config write — card registry, then budget targets —
that didn't bump the ledger data-version, so the `_vcache` layer served the OLD value and the write looked
like it "didn't take". `_config_sig()` now folds every YAML store's mtime into the vcache key, so ANY
config write invalidates cached views immediately. This asserts the generalized guarantee via budget
targets: set a target through the real endpoint → the next cached /api/categories read shows it → restore.
Protects every YAML-backed store (targets · envelopes · tree · meta · merchants · registry · schedules).
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


def _tm(name):
    for c in app.categories_data("").get("cats", []):   # vcached read
        if c["name"] == name:
            return c.get("target_monthly")
    return None


def main():
    cats = [c["name"] for c in app.categories_data("").get("cats", []) if c.get("kind") == "exp"]
    if not cats:
        print("SKIP: no expense category to test"); return 0
    name = cats[0]
    saved = app._cat_targets().get(name)                 # preserve to restore
    try:
        asyncio.new_event_loop().run_until_complete(
            app.category_target(_Req({"name": name, "amount": "4321", "period": "monthly"})))
        after = _tm(name)                                # the NEXT cached read MUST reflect it
        ok = abs((after or 0) - 4321.0) < 0.01
        print(f"config write → next cached read: '{name}' target_monthly = {after}  ({'OK' if ok else 'XX'})")
        if ok:
            print("PASS: a YAML-config write is reflected immediately (no stale vcache).")
            return 0
        print("FAIL: cached view served a stale config after the write (the stale-config class).")
        return 1
    finally:
        t = app._cat_targets()
        if saved is None:
            t.pop(name, None)
        else:
            t[name] = saved
        app._yaml_save("category_targets.yaml", t)


if __name__ == "__main__":
    sys.exit(main())
