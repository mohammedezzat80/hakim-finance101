#!/usr/bin/env python3
"""Backfill transaction descriptions + txn-type tags from the source files.

The importer used to store only column D (the reference) — e.g. `093-2347793255
11100067564602` — dropping column C (the transaction type: "SADAD Payment",
"POS Purchase International", "Incoming internal transfer" ...). This re-derives the
composed description ("SADAD Payment — 093-2347…") for the ~280 already-imported
transactions, straight from the same source files, so the weekly sweep is recognition
instead of decryption.

SAFE BY CONSTRUCTION:
  • Matches existing Firefly txns by external_id (reconstructed with the importer's own
    per-file occurrence index + run-level dedup + transfer keys — identical to import).
  • Upgrades a description ONLY when it still equals the raw imported reference, so a
    human edit (or a transfer-conversion rename) is never clobbered.
  • Adds txn-type / fx-candidate tags ONLY to un-answered items; on ANSWERED items
    (verified, categorised, noted, or person-tagged) it touches nothing but the
    description, and even that only if untouched.
  • Only SNB account/card rows carry a type column; SABB rows have none and are skipped.
  • Dry-run by default. `--apply` writes. Every change logged before/after.
"""
import argparse
import glob
import os
import sys
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_statements as imp  # noqa: E402
from _ff import Firefly, load_env  # noqa: E402

LOG = os.path.join(imp.ROOT, "logs", "backfill.log")

# tags that are system/importer bookkeeping — their presence does NOT mean "answered"
_SYS_PREFIXES = ("import:", "txn-type:", "trust:imported", "sms", "fused:")
_SYS_EXACT = {"fx-candidate", "sms"}


def reconstruct() -> dict:
    """Replay the importer's parse + id-assignment to recover, per external_id, the
    (ttype, reference) exactly as the original import produced it."""
    files = sorted(f for f in glob.glob(os.path.join(imp.INBOX, "**", "*"), recursive=True)
                   if f.lower().endswith((".xls", ".csv")))
    rules = imp.load_rules()
    all_rows = []
    for path in files:
        fmt = imp.classify(path)
        if fmt not in imp.PARSERS:
            continue
        rows = imp.PARSERS[fmt](path)
        occ = Counter()
        for r in rows:
            if not r.unparseable:
                imp.categorize(r, rules)
                if r.account and r.txn_date >= imp.BACKFILL_START:
                    base = (r.account, r.txn_date, f"{r.amount:.2f}", imp.norm_for_hash(r.desc))
                    r.external_id = imp.make_external_id(r.account, r.txn_date, r.amount,
                                                         r.desc, occ[base])
                    occ[base] += 1
        all_rows.extend(rows)
    # run-level dedup of overlapping exports (identical to import)
    seen, inrange = set(), []
    for r in all_rows:
        if (r.unparseable or not r.account or r.txn_date < imp.BACKFILL_START
                or r.needs_assignment):
            continue
        if r.external_id in seen:
            continue
        seen.add(r.external_id)
        inrange.append(r)
    confirmed, _cand = imp.match_transfers(inrange)
    confirmed_ids = set()
    for o, i in confirmed:
        confirmed_ids.add(id(o))
        confirmed_ids.add(id(i))
    src = {}
    for r in inrange:
        if id(r) in confirmed_ids or not r.external_id:
            continue
        src[r.external_id] = {"ttype": r.ttype, "ref": r.desc, "kind": "plain"}
    toccur = Counter()
    for o, i in confirmed:
        tkey = (o.account, i.account, o.txn_date, f"{abs(o.amount):.2f}", imp.norm_for_hash(o.desc))
        ext = imp.make_external_id(f"{o.account}>{i.account}", o.txn_date, abs(o.amount),
                                   o.desc, toccur[tkey])
        toccur[tkey] += 1
        src[ext] = {"ttype": o.ttype, "ref": o.desc, "kind": "transfer"}
    return src


def is_answered(split: dict) -> bool:
    tags = split.get("tags") or []
    for t in tags:
        if t == "trust:verified" or t.startswith("trust:verified"):
            return True
    cat = split.get("category_name")
    if cat and cat != "To review":
        return True
    if (split.get("notes") or "").strip():
        return True
    for t in tags:  # any non-system tag => Mohamed labelled it (person/context)
        if t in _SYS_EXACT or t.startswith(_SYS_PREFIXES):
            continue
        return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write to Firefly (default: dry run)")
    args = ap.parse_args()
    mode = "APPLY" if args.apply else "DRY RUN"

    src = reconstruct()
    env = load_env()
    if (env.get("FIREFLY_ADMIN_TOKEN") or "").strip():
        env["FIREFLY_PAT"] = env["FIREFLY_ADMIN_TOKEN"]
    ff = Firefly(env)

    idx = {}
    for tp in ("withdrawal", "deposit", "transfer"):
        for g in ff.get_all("transactions", type=tp):
            for s in g["attributes"]["transactions"]:
                eid = s.get("external_id")
                if eid:
                    idx[eid] = (g["id"], s)

    print(f"\n{'='*74}\nHAKIM DESCRIPTION BACKFILL — {mode}\n"
          f"source rows with a type: {sum(1 for v in src.values() if (v['ttype'] or '').strip())}"
          f" | ledger txns indexed: {len(idx)}\n{'='*74}")

    plan, skipped_edit, no_type, no_match = [], 0, 0, 0
    for eid, info in src.items():
        ttype = (info["ttype"] or "").strip()
        if not ttype:
            no_type += 1   # no type prefix/tag, but still repair a truncated description (SABB)
        hit = idx.get(eid)
        if not hit:
            no_match += 1
            continue
        gid, s = hit
        cur = (s.get("description") or "").strip()
        new = imp.compose_desc(ttype, info["ref"])
        if cur == new:
            continue  # already upgraded (idempotent rerun)
        answered = is_answered(s)
        tx = {"transaction_journal_id": s["transaction_journal_id"]}
        did = []
        ref_clean = (info["ref"] or "").strip()
        # upgradeable if the stored text is the raw reference OR a truncated PREFIX of it
        # (the original importer capped descriptions at 120 chars, losing trailing names).
        # A genuine human edit is not a prefix of the bank reference, so it's still protected.
        upgradeable = (cur == ref_clean or cur == imp.clean_desc(info["ref"])
                       or (len(cur) >= 20 and ref_clean.startswith(cur)))
        if upgradeable:
            tx["description"] = new
            did.append("desc")
        elif cur != new:
            skipped_edit += 1  # genuinely human-edited description — leave it be
        if not answered:
            existing = s.get("tags") or []
            want = existing + [t for t in imp.process_tags(ttype) if t not in existing]
            if want != existing:
                tx["tags"] = want
                did.append("tags")
        if not did:
            continue
        plan.append((eid, gid, cur, new, did, answered, tx))

    for eid, gid, cur, new, did, answered, tx in plan:
        flag = " [answered: desc-only]" if answered else ""
        print(f"  {'✎' if 'desc' in did else ' '} #{gid} {'+tag' if 'tags' in did else '    '}"
              f"{flag}\n      was: {cur[:70]}\n      now: {new[:70]}")

    print(f"\n{'-'*74}\nWould change: {len(plan)}  "
          f"(desc {sum(1 for p in plan if 'desc' in p[4])}, "
          f"tags {sum(1 for p in plan if 'tags' in p[4])})")
    print(f"Skipped — human-edited description: {skipped_edit} | "
          f"no-type rows (desc-repair only): {no_type} | external_id not in ledger: {no_match}")

    if not args.apply:
        print("\nDRY RUN — nothing written. Re-run with --apply to update.\n")
        return

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    done = 0
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(f"\n=== backfill_descriptions {stamp} — {len(plan)} planned ===\n")
        for eid, gid, cur, new, did, answered, tx in plan:
            try:
                ff._req("PUT", f"transactions/{gid}", {"transactions": [tx]})
                done += 1
                fh.write(f"OK #{gid} {'/'.join(did)}{' answered' if answered else ''} | "
                         f"was={cur!r} now={new!r} tags={tx.get('tags')}\n")
            except Exception as e:
                fh.write(f"FAIL #{gid} {e}\n")
                print(f"  FAIL #{gid}: {e}")
    print(f"\nApplied {done}/{len(plan)} updates. Logged → {os.path.relpath(LOG, imp.ROOT)}\n")


if __name__ == "__main__":
    main()
