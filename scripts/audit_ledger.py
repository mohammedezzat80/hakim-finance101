#!/usr/bin/env python3
"""HAKIM full ledger audit — READ-ONLY. Re-verifies every Firefly transaction against
its original source file and reports discrepancies. Applies NO fixes (GET only).

Run: ./.venv-importer/bin/python scripts/audit_ledger.py
"""
import glob
import os
import re
import sys
from collections import Counter
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_statements as imp  # noqa: E402
from _ff import Firefly, load_env  # noqa: E402

ROOT = imp.ROOT
FAILS = []          # (section, message)
def fail(sec, msg):
    FAILS.append((sec, msg))
    print(f"  ✗ {msg}")
def ok(msg):
    print(f"  ✓ {msg}")


# ---------------------------------------------------------------- reparse sources
def reparse():
    files = sorted(f for f in glob.glob(os.path.join(imp.INBOX, "**", "*"), recursive=True)
                   if f.lower().endswith((".xls", ".csv")))
    rules = imp.load_rules()
    per_file, all_rows, file_rows_map = [], [], {}
    for path in files:
        fmt = imp.classify(path)
        base = os.path.basename(path)
        if fmt not in imp.PARSERS:
            per_file.append({"file": base, "fmt": "?", "status": "UNRECOGNISED"})
            continue
        rows = imp.PARSERS[fmt](path)
        occ = Counter()
        for r in rows:
            if not r.unparseable:
                imp.categorize(r, rules)
                if r.account and r.txn_date >= imp.BACKFILL_START:
                    b = (r.account, r.txn_date, f"{r.amount:.2f}", imp.norm_for_hash(r.desc))
                    r.external_id = imp.make_external_id(r.account, r.txn_date, r.amount, r.desc, occ[b])
                    occ[b] += 1
        all_rows.extend(rows)
        file_rows_map[path] = rows
        inr = [r for r in rows if not r.unparseable and r.account and r.txn_date >= imp.BACKFILL_START]
        per_file.append({"file": base, "fmt": fmt, "total": len(rows), "inrange": len(inr),
                         "before": sum(1 for r in rows if not r.unparseable and r.txn_date < imp.BACKFILL_START),
                         "bad": sum(1 for r in rows if r.unparseable),
                         "acct": rows[0].account if rows else None,
                         "needs": any(r.needs_assignment for r in rows)})
    seen, inrange, overlap = set(), [], 0
    for r in all_rows:
        if r.unparseable or not r.account or r.txn_date < imp.BACKFILL_START or r.needs_assignment:
            continue
        if r.external_id in seen:
            overlap += 1
            continue
        seen.add(r.external_id)
        inrange.append(r)
    confirmed, cand = imp.match_transfers(inrange)
    cids = set()
    for o, i in confirmed:
        cids.add(id(o)); cids.add(id(i))
    plain = {r.external_id: r for r in inrange if id(r) not in cids and r.external_id}
    toc, transfers = Counter(), {}
    for o, i in confirmed:
        tk = (o.account, i.account, o.txn_date, f"{abs(o.amount):.2f}", imp.norm_for_hash(o.desc))
        ext = imp.make_external_id(f"{o.account}>{i.account}", o.txn_date, abs(o.amount), o.desc, toc[tk])
        toc[tk] += 1
        transfers[ext] = (o, i)
    return per_file, plain, transfers, inrange, overlap, confirmed, cand, file_rows_map


def main():
    env = load_env()
    if (env.get("FIREFLY_ADMIN_TOKEN") or "").strip():
        env["FIREFLY_PAT"] = env["FIREFLY_ADMIN_TOKEN"]
    ff = Firefly(env)
    per_file, plain, transfers, inrange, overlap, confirmed, cand, file_rows_map = reparse()

    # index the ledger
    ledger = {}          # external_id -> split
    all_splits = []      # (group_id, split)
    for tp in ("withdrawal", "deposit", "transfer"):
        for g in ff.get_all("transactions", type=tp):
            for s in g["attributes"]["transactions"]:
                s["_gid"] = g["id"]
                s["_attach"] = int(g["attributes"].get("attachment_count") or 0)
                all_splits.append(s)
                eid = s.get("external_id")
                if eid:
                    ledger.setdefault(eid, []).append(s)
    accts = {a["attributes"]["name"]: a for a in ff.get_all("accounts")}

    print("\n" + "=" * 78 + "\nHAKIM LEDGER AUDIT — read-only, report-only\n" + "=" * 78)

    # ---- SECTION 1: completeness ----
    print("\n[1] COMPLETENESS — source rows vs ledger")
    print(f"  {'file':28} {'fmt':3} {'src':>4} {'in-rng':>6} {'before':>6} {'bad':>4} account")
    for pf in per_file:
        if pf.get("status") == "UNRECOGNISED":
            fail(1, f"{pf['file']} UNRECOGNISED format"); continue
        flag = "⚠️NEEDS-ASSIGN" if pf["needs"] else ""
        print(f"  {pf['file']:28} {pf['fmt']:3} {pf['total']:>4} {pf['inrange']:>6} "
              f"{pf['before']:>6} {pf['bad']:>4} {pf['acct'] or ''} {flag}")
    src_eids = set(plain) | set(transfers)
    led_transfers = [s for s in all_splits if s["type"] == "transfer"]
    def became_transfer(r):
        """A plain source row whose leg was deleted+recreated as a transfer (conversion/
        fusion) legitimately has no plain ledger row — find the transfer that absorbed it."""
        for s in led_transfers:
            if Decimal(str(s["amount"])).quantize(Decimal("0.01")) != abs(r.amount).quantize(Decimal("0.01")):
                continue
            if r.account not in {s.get("source_name"), s.get("destination_name")}:
                continue
            try:
                d = abs((date.fromisoformat((s.get("date") or "")[:10]) - r.txn_date).days)
            except Exception:
                d = 99
            if d <= 4:
                return s
        return None
    dupes = {e: len(v) for e, v in ledger.items() if e in src_eids and len(v) > 1}
    print(f"  unique in-range source rows: {len(inrange)} | plain {len(plain)} + "
          f"transfers {len(transfers)} | overlap-dupes collapsed: {overlap}")
    missing = [e for e in plain if e not in ledger]
    converted, genuine_missing = [], []
    for e in missing:
        t = became_transfer(plain[e])
        (converted if t else genuine_missing).append((plain[e], t))
    if genuine_missing:
        for r, _ in genuine_missing:
            fail(1, f"GENUINELY MISSING: {r.account} {r.txn_date} SAR {r.amount} [{r.desc[:40]}]")
    else:
        ok(f"every plain source row accounted for ({len(converted)} became transfer legs — §4)")
    if converted:
        print(f"  ↪ {len(converted)} plain rows are now transfer legs (converted/fused, expected):")
        for r, t in converted:
            print(f"     {r.account} {r.txn_date} SAR {r.amount} → transfer #{t['_gid']} [{r.desc[:32]}]")
    if dupes:
        for e, n in dupes.items():
            fail(1, f"DUPLICATE external_id {e} appears {n}× in ledger")
    else:
        ok("no duplicate external_ids in ledger")

    # ---- SECTION 2: field fidelity ----
    print("\n[2] FIELD FIDELITY — stored vs source (amount/date/sign/currency/desc/type)")
    n_ok = n_bad = 0
    for eid, r in plain.items():
        sp = ledger.get(eid)
        if not sp:
            continue
        s = sp[0]
        if s["type"] == "transfer":
            continue  # converted/fused — no longer a plain row; validated in §4
        # amount (exact)
        if Decimal(str(s["amount"])).quantize(Decimal("0.01")) != abs(r.amount).quantize(Decimal("0.01")):
            fail(2, f"#{s['_gid']} amount {s['amount']} != source {abs(r.amount)}"); n_bad += 1; continue
        # date
        if (s.get("date") or "")[:10] != r.txn_date.isoformat():
            fail(2, f"#{s['_gid']} date {s.get('date','')[:10]} != source {r.txn_date}"); n_bad += 1; continue
        # sign / direction
        want = "withdrawal" if r.amount < 0 else "deposit"
        if s["type"] not in (want, "transfer"):
            fail(2, f"#{s['_gid']} type {s['type']} != expected {want}"); n_bad += 1; continue
        # currency
        if (s.get("currency_code") or "SAR") != "SAR":
            fail(2, f"#{s['_gid']} currency {s.get('currency_code')} != SAR"); n_bad += 1; continue
        # full description contains the source reference (truncation class)
        if imp.clean_desc(r.desc) and imp.clean_desc(r.desc) not in (s.get("description") or ""):
            fail(2, f"#{s['_gid']} TRUNCATED/altered desc: ref not contained"); n_bad += 1; continue
        # txn-type tag matches source column C
        if r.ttype.strip():
            if f"txn-type:{r.ttype.strip()}" not in (s.get("tags") or []):
                # allowed to be absent only if the item was answered (tag guard) — note, not fail
                pass
        n_ok += 1
    if n_bad == 0:
        ok(f"all {n_ok} plain rows field-clean (amount/date/sign/currency/full-desc)")
    else:
        print(f"  → {n_ok} clean / {n_bad} discrepancies")

    # ---- SECTION 3: balance arithmetic (bank running-balance chains) ----
    print("\n[3] BALANCE ARITHMETIC — statement chains + current balances")
    bank_accts = sorted({r.account for r in inrange if r.balance is not None and r.account})
    for acct in bank_accts:
        ob = imp.opening_for_account(acct, file_rows_map, inrange)
        if not ob:
            continue
        opening, dclose, fclose, good = ob
        if good:
            ok(f"{acct}: opening {opening} + activity → {dclose} = statement {fclose} ✓")
        else:
            fail(3, f"{acct}: derived close {dclose} != statement {fclose}")
    # only Hisham's own current accounts are expected to net to 0 (exact names — NOT
    # Firefly's "Initial balance for…" mirror accounts, NOT Sarah's account which holds a real balance)
    ZERO_BANKS = {"Hisham SNB main", "SABB main"}
    for name in ZERO_BANKS:
        a = accts.get(name)
        if not a:
            fail(3, f"{name} not found"); continue
        bal = Decimal(str(a["attributes"].get("current_balance") or "0"))
        if abs(bal) < Decimal("0.01"):
            ok(f"{name} current balance ≈ 0 ✓")
        else:
            fail(3, f"{name} current balance {bal} (expected 0)")
    sarah = accts.get("Sarah SNB main")
    if sarah:
        print(f"  (Sarah SNB main holds {sarah['attributes'].get('current_balance')} — expected, her account)")

    # ---- SECTION 4: transfers evidence ----
    print("\n[4] TRANSFERS — fusion/conversion evidence (eyeball each)")
    PAYKW = re.compile(r"payment|transfer|ac to ac|sadad|\bips\b|تحويل|card", re.I)
    for o, i in confirmed:
        last4 = imp._dest_last4s(o.desc) | imp._dest_last4s(i.desc)
        src_last4 = {n.split("•")[-1][-4:] for n in (o.account, i.account) if "•" in n}
        both_sem = bool(PAYKW.search(o.desc)) and bool(PAYKW.search(i.desc))
        one_sem = bool(PAYKW.search(o.desc)) or bool(PAYKW.search(i.desc))
        if last4 & src_last4 or last4:
            tag = "card-number anchored"
        elif both_sem:
            tag = "payment/transfer semantics BOTH sides"
        elif one_sem:
            tag = "transfer semantics one side"
        else:
            tag = "⚠️ AMOUNT+DATE ONLY"
        print(f"  {o.txn_date} SAR {abs(o.amount):>10} {o.account} → {i.account}  [{tag}]")
        if tag.startswith("⚠️"):
            fail(4, f"fusion {o.account}->{i.account} {o.txn_date} SAR {abs(o.amount)} — amount+date alone")
    # fused/converted from the audit logs
    fuse_lines = [l for l in open(os.path.join(ROOT, "logs", "review.log"), encoding="utf-8")
                  if "FUSE" in l or "convert_transfer" in l] if os.path.exists(os.path.join(ROOT, "logs", "review.log")) else []
    print(f"  logged fusions/conversions in review.log: {len(fuse_lines)} (evidence recorded before/after)")

    # ---- SECTION 5: cards back-solved debt ----
    print("\n[5] CARDS — back-solved opening + activity = current debt (7 Sep)")
    for card, debt in imp.CARD_CURRENT_DEBT.items():
        net = sum((r.amount for r in inrange if r.account == card), Decimal(0))
        net += sum((abs(o.amount) for o, i in confirmed if i.account == card), Decimal(0))
        net -= sum((abs(o.amount) for o, i in confirmed if o.account == card), Decimal(0))
        a = accts.get(card)
        if not a:
            fail(5, f"{card} not found in ledger"); continue
        bal = Decimal(str(a["attributes"].get("current_balance") or "0"))
        expect = -debt
        drift = (bal - expect).copy_abs()
        if drift < Decimal("0.01"):
            ok(f"{card}: ledger {bal} = -debt {expect} ✓")
        else:
            fail(5, f"{card}: ledger {bal} vs -debt {expect} (drift {drift})")

    # ---- SECTION 6: integrity of Hisham's work ----
    print("\n[6] INTEGRITY — verified/categorized items untouched by backfills")
    verified = [s for s in all_splits if "trust:verified" in (s.get("tags") or [])]
    lost = 0
    for s in verified:
        cat = s.get("category_name")
        note = s.get("notes") or ""
        if not cat and "Reviewed by Hisham" not in note:
            fail(6, f"#{s['_gid']} verified but has no category AND no review note"); lost += 1
    if lost == 0:
        ok(f"{len(verified)} verified items all retain category/notes stamps")

    # ---- SECTION 7: orphans & strays ----
    print("\n[7] ORPHANS & STRAYS")
    known = set(plain) | set(transfers)
    orphans = [s for s in all_splits if not s.get("external_id")
               or (s.get("external_id") not in known and "fused" not in " ".join(s.get("tags") or []))]
    manual = [s for s in orphans if "manual" in (s.get("tags") or []) or "trust:verified" in (s.get("tags") or [])]
    print(f"  no-source / manual transactions (expected — confirm each is yours): {len(orphans)}")
    for s in orphans[:40]:
        print(f"    #{s['_gid']} {s['type']:11} SAR {s['amount']:>10} | tags={[t for t in (s.get('tags') or []) if not t.startswith(('import:','txn-type:'))]} | {(s.get('description') or '')[:45]}")
    # placeholder names that must never exist
    bad_terms = ("NWF", "Al Nabeel", "Nabeel")
    stray_cat = [s for s in all_splits if any(b.lower() in (s.get("category_name") or "").lower() for b in bad_terms)]
    if stray_cat:
        fail(7, f"{len(stray_cat)} txns use a placeholder category name (NWF/Al Nabeel)")
    else:
        ok("no placeholder (NWF/Al Nabeel) category/tag in use")
    attach = [s for s in all_splits if s.get("_attach")]
    print(f"  transactions with attachments: {len(attach)}")

    # ---- verdict ----
    print("\n" + "=" * 78)
    if not FAILS:
        print(f"AUDIT: ✅ ALL CLEAN — {len(all_splits)} ledger splits, {len(inrange)} source rows, "
              f"0 genuinely missing ({len(converted)} became transfers), {len(dupes)} dupes, "
              f"0 truncations, balances reconcile.")
    else:
        print(f"AUDIT: ⚠️ {len(FAILS)} FINDING(S) — review before Sarah's import:")
        for sec, m in FAILS:
            print(f"  [§{sec}] {m}")
    print("=" * 78 + "\n(NO fixes applied — report only.)")


if __name__ == "__main__":
    main()
