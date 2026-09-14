#!/usr/bin/env python3
"""HAKIM SMS capture (Brief 04, Part B) — reads Saudi bank SMS from the macOS
Messages database and turns real transactions into Firefly entries.

Runs on the HOST (needs Full Disk Access to ~/Library/Messages/chat.db). chat.db
is opened READ-ONLY (mode=ro), copied to a temp dir if the live file is locked.
We never write to it.

  DRY RUN (default): parse + classify, report per wallet/sender, verify the barq
    balance chain, derive openings — WRITE NOTHING.
      ./.venv-importer/bin/python scripts/sms_capture.py
  LIVE (after Hisham approves): --apply  (writes to Firefly via the same pipeline)

Hard filters (never imported): declines / insufficient-balance, OTP codes, ads &
offers, device-login alerts, service notices, balance-only. Counted and logged.
Unknown template from a bank sender -> surfaced to the Review UI (To review).
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ff import Firefly, load_env  # noqa: E402
import hashlib
import sqlite3 as _sq
import yaml as _yaml

CHAT_DB = os.path.expanduser("~/Library/Messages/chat.db")
APPLE_EPOCH = 978307200  # 2001-01-01 in unix seconds
BACKFILL_START = datetime(2026, 7, 1, tzinfo=timezone.utc)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(ROOT, "logs", "sms.log")
UNKNOWN_LOG = os.path.join(ROOT, "logs", "sms_unknown.log")
SMS_INDEX = os.path.join(ROOT, "data", "sms_index.db")
MERCHANTS_PATH = os.path.join(ROOT, "data", "merchants.yaml")
# known current balances (7 Sep) — wallet openings back-solved from these
WALLET_CURRENT = {"Barq": Decimal("56.14"), "STC Pay": Decimal("25.15"),
                  "D360": Decimal("20.03")}

# sender handle (lowercased) -> institution
SENDER_MAP = {
    "sabb": "SABB", "sab": "SABB",
    "snb-alahli": "SNB", "samba.": "SNB", "900": "SNB", "alawwalbank": "SNB",
    "alahlisms": "SNB",
    "stcpay": "STC", "stc bank": "STC", "stc": "STC",
    "d360 bank": "D360", "barq app": "BARQ",
}
# wallets are SMS-only backfill; SNB/SABB are live-capture + statement-confirm
BACKFILL_INSTITUTIONS = {"STC", "D360", "BARQ"}

# card/account last-4 -> Firefly account name (unknown -> ask in Review UI)
CARD_MAP = {
    "5071": "STC Pay", "5621": "Barq", "1084": "D360",
    "6510": "Hisham SNB Mastercard •6510", "8381": "Hisham SNB Alfursan •8381",
    "5019": "SABB Visa •5019", "5158": "SABB Mastercard •5158",
    "4331": "SABB Alfursan •4331",
}
WALLET_ACCOUNT = {"STC": "STC Pay", "D360": "D360", "BARQ": "Barq"}

# --- hard filters (never import) ------------------------------------------
FILTERS = [
    ("decline", re.compile(r"declined|rejected transaction|insufficient balance|"
                           r"رفض|رصيد غير كاف", re.I)),
    ("otp", re.compile(r"\botp\b|is your otp|verification code|رمز التفعيل|"
                       r"لا تشارك", re.I)),
    ("login", re.compile(r"device login|browser device|login to your account", re.I)),
    ("ad", re.compile(r"dear customer|phishing|new brand|announce|beware|offer|"
                      r"عرض|خصم", re.I)),
    ("notice", re.compile(r"overdue amount|has been activated|beneficiary name|"
                          r"reference:", re.I)),
]


# --------------------------------------------------------------------------
def extract_text(blob) -> str | None:
    """Decode an NSAttributedString typedstream blob -> plain message text."""
    if not blob:
        return None
    i = blob.find(b"NSString")
    if i < 0:
        return None
    j = blob.find(b"+", i)
    if j < 0:
        return None
    k = j + 1
    L = blob[k]
    if L == 0x81:
        n = int.from_bytes(blob[k + 1:k + 3], "little"); st = k + 3
    elif L == 0x82:
        n = int.from_bytes(blob[k + 1:k + 5], "little"); st = k + 5
    else:
        n = L; st = k + 1
    return blob[st:st + n].decode("utf-8", "replace")


def open_chatdb():
    try:
        con = sqlite3.connect(f"file:{CHAT_DB}?mode=ro", uri=True, timeout=5)
        con.execute("select count(*) from message").fetchone()
        return con, None
    except Exception:
        tmp = os.path.join(tempfile.mkdtemp(prefix="hakim-sms-"), "chat.db")
        shutil.copy2(CHAT_DB, tmp)
        for ext in ("-wal", "-shm"):
            if os.path.exists(CHAT_DB + ext):
                shutil.copy2(CHAT_DB + ext, tmp + ext)
        return sqlite3.connect(f"file:{tmp}?mode=ro", uri=True), tmp


def messages_since(con, since: datetime):
    cutoff = (since.timestamp() - APPLE_EPOCH) * 1e9
    q = """select m.ROWID, h.id, m.text, m.attributedBody, m.date
           from message m join handle h on m.handle_id = h.ROWID
           where m.date >= ? and m.is_from_me = 0 order by m.date asc"""
    for rowid, sender, text, ab, mdate in con.execute(q, (cutoff,)):
        inst = SENDER_MAP.get((sender or "").strip().lower())
        if not inst:
            continue
        body = text or extract_text(ab) or ""
        ts = datetime.fromtimestamp(mdate / 1e9 + APPLE_EPOCH, tz=timezone.utc)
        yield {"rowid": rowid, "sender": sender, "inst": inst, "text": body, "ts": ts}


def classify(text: str) -> str:
    for name, rx in FILTERS:
        if rx.search(text):
            return name
    return "txn"


def _amount(text) -> Decimal | None:
    m = re.search(r"(?:amount|مبلغ)\s*:?\s*(?:SAR\s*)?([\d,]+\.?\d*)\s*(?:SAR|SR|ريال)?",
                  text, re.I)
    if m:
        return Decimal(m.group(1).replace(",", ""))
    return None


def _last4(text) -> str | None:
    m = re.search(r"(?:card|via|mada card)\s*[:#]?\s*\*+\s*(\d{4})", text, re.I)
    if not m:
        m = re.search(r"\*+\s*(\d{4})", text)
    return m.group(1) if m else None


def _balance(text) -> Decimal | None:
    m = re.search(r"balance\s*:?\s*([\d,]+\.?\d*)", text, re.I)
    return Decimal(m.group(1).replace(",", "")) if m else None


def parse_txn(msg) -> dict | None:
    """Return a normalized txn dict or None if not parseable as a transaction."""
    t = msg["text"]
    amt = _amount(t)
    if amt is None:
        return None
    low = t.lower()
    IN = ["money added", "adding money", "account funding", "incoming", "top up",
          "top-up", "refund", "credit to your", "أضيف", "اضافة", "واردة"]
    OUT = ["purchase", "pos", "atm withdrawal", "withdrawal", "outgoing", "transfer to",
           "payment", "صادرة", "شراء", "سحب"]
    if any(k in low for k in IN) or any(k in t for k in ["أضيف", "اضافة", "واردة"]):
        direction = "in"
    elif any(k in low for k in OUT) or any(k in t for k in ["صادرة", "شراء", "سحب"]):
        direction = "out"
    else:
        direction = "out"
    merch = None
    mm = re.search(r"(?:at|from|to|At:|From:|مستفيد)\s*:?\s*([^/\n]+)", t)
    if mm:
        merch = mm.group(1).strip()[:60]
    return {"inst": msg["inst"], "ts": msg["ts"], "amount": amt, "direction": direction,
            "last4": _last4(t), "balance": _balance(t), "merchant": merch,
            "account": CARD_MAP.get(_last4(t) or "", WALLET_ACCOUNT.get(msg["inst"])),
            "raw": t}


def log(msg: str):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(f"{datetime.now(timezone.utc).isoformat()}  {msg}\n")


# --------------------------------------------------------------------------
def dry_run():
    con, tmp = open_chatdb()
    print(f"\n{'='*72}\nHAKIM SMS CAPTURE — DRY RUN (no writes)\n"
          f"chat.db: {'live (ro)' if not tmp else 'copied'} | since {BACKFILL_START.date()}\n{'='*72}")

    by_inst_msgs = defaultdict(list)
    for m in messages_since(con, BACKFILL_START):
        by_inst_msgs[m["inst"]].append(m)

    for inst in ["STC", "D360", "BARQ", "SNB", "SABB"]:
        msgs = by_inst_msgs.get(inst, [])
        filt = Counter()
        txns = []
        unknown = 0
        for m in msgs:
            c = classify(m["text"])
            if c != "txn":
                filt[c] += 1
                continue
            p = parse_txn(m)
            if p:
                txns.append(p)
            else:
                unknown += 1
        role = "SMS-only backfill" if inst in BACKFILL_INSTITUTIONS else "live + statement-confirm"
        print(f"\n▸ {inst}  ({role})")
        print(f"    messages since 1 Jul: {len(msgs)}")
        print(f"    filtered: " + (", ".join(f"{k}={v}" for k, v in filt.items()) or "none")
              + f"  | unknown-template: {unknown}")
        print(f"    parseable transactions: {len(txns)}")
        if inst == "BARQ":
            _barq_chain(txns)
        elif inst in ("STC", "D360"):
            print(f"    ⚠️ no running-balance in {inst} SMS — opening CANNOT be chain-derived; "
                  f"keep manual opening or reconcile another way.")

    print(f"\n{'-'*72}\nNEXT: after approval, run with --apply to backfill wallets + enable live.")
    print("Nothing written (dry run).\n")
    if tmp:
        shutil.rmtree(os.path.dirname(tmp), ignore_errors=True)


def _barq_chain(txns):
    """Verify barq running-balance chain and derive the 1 Jul opening."""
    chain = [t for t in txns if t["balance"] is not None]
    chain.sort(key=lambda t: t["ts"])
    if not chain:
        print("    (no balance-stamped barq rows)")
        return
    # balance is AFTER the txn; signed effect: purchase = -amount, top-up = +amount
    def signed(t):
        return t["amount"] if t["direction"] == "in" else -t["amount"]
    opening = chain[0]["balance"] - signed(chain[0])
    breaks = 0
    prev = opening
    for t in chain:
        if prev + signed(t) != t["balance"]:
            breaks += 1
        prev = t["balance"]
    last = chain[-1]["balance"]
    ok = "✅" if breaks == 0 else f"⚠️ {breaks} chain break(s)"
    print(f"    barq chain: {len(chain)} balance-stamped rows | derived 1 Jul opening "
          f"SAR {opening:,.2f} | latest balance SAR {last:,.2f}  {ok}")
    print(f"    (expected latest ≈ 56.14 -> {'MATCH' if abs(last-Decimal('56.14'))<Decimal('0.01') else 'CHECK'})")


# --------------------------------------------------------------------------
# write path (backfill + live)
# --------------------------------------------------------------------------
def _signed(t) -> Decimal:
    return t["amount"] if t["direction"] == "in" else -t["amount"]


def _index():
    os.makedirs(os.path.dirname(SMS_INDEX), exist_ok=True)
    con = _sq.connect(SMS_INDEX)
    con.execute("""CREATE TABLE IF NOT EXISTS seen (rowid INTEGER PRIMARY KEY,
                   firefly_id TEXT, account TEXT, amount TEXT, ts TEXT)""")
    con.execute("CREATE TABLE IF NOT EXISTS state (k TEXT PRIMARY KEY, v TEXT)")
    return con


def _rules():
    if not os.path.exists(MERCHANTS_PATH):
        return []
    y = _yaml.safe_load(open(MERCHANTS_PATH, encoding="utf-8")) or {}
    return [(re.compile(r["pattern"], re.I), r) for r in y.get("rules", [])]


def _categorize(text, rules):
    for rx, r in rules:
        if rx.search(text):
            return r["category"], r.get("tags", [])
    return "To review", []


def barq_breaks_check(txns):
    """Report whether barq chain breaks coincide with 'Money Added' top-ups
    (which carry no Balance stamp). Decision #2."""
    chain = sorted([t for t in txns if t["balance"] is not None], key=lambda t: t["ts"])
    tops = sorted([t for t in txns if t["balance"] is None and t["direction"] == "in"],
                  key=lambda t: t["ts"])
    breaks, explained = [], 0
    prev = chain[0]["balance"] - _signed(chain[0]) if chain else Decimal(0)
    for t in chain:
        if prev + _signed(t) != t["balance"]:
            # a top-up between prev and this row explains the jump?
            span = [x for x in tops if x["ts"] <= t["ts"]]
            gap = t["balance"] - (prev + _signed(t))
            match = any(x["amount"] == gap for x in span)
            breaks.append((t["ts"].date(), gap, "top-up" if match else "UNEXPLAINED"))
            if match:
                explained += 1
        prev = t["balance"]
    return breaks, explained, len(tops)


def _account_ids(ff):
    return {a["attributes"]["name"]: a["id"]
            for tp in ("asset", "liability") for a in ff.get_all("accounts", type=tp)}


def _write_txn(ff, ids, con, msg_rowid, t, rules, extra_tags=None):
    if con.execute("SELECT 1 FROM seen WHERE rowid=?", (msg_rowid,)).fetchone():
        return "dup"
    acct = t["account"]
    if not acct or acct not in ids:
        with open(UNKNOWN_LOG, "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now(timezone.utc).isoformat()}  UNMAPPED {t['inst']} "
                     f"last4={t['last4']} {t['raw'][:120]}\n")
        return "unmapped"
    cat, ctags = _categorize(t["raw"], rules)
    tags = ["sms"] + (ctags or []) + (extra_tags or [])
    common = {"date": t["ts"].date().isoformat(), "amount": f"{t['amount']:.2f}",
              "description": (t["merchant"] or t["inst"])[:120], "category_name": cat,
              "currency_code": "SAR", "external_id": f"sms-{msg_rowid}", "tags": tags}
    if t["direction"] == "in":
        body = {**common, "type": "deposit", "source_name": (t["merchant"] or "Top-up")[:60],
                "destination_id": ids[acct]}
    else:
        body = {**common, "type": "withdrawal", "source_id": ids[acct],
                "destination_name": (t["merchant"] or "Unknown")[:60]}
    r = ff.post("transactions", {"error_if_duplicate_hash": False, "apply_rules": False,
                                 "transactions": [body]})
    fid = r["data"]["id"]
    con.execute("INSERT OR IGNORE INTO seen VALUES (?,?,?,?,?)",
                (msg_rowid, fid, acct, f"{t['amount']:.2f}", t["ts"].isoformat()))
    con.commit()
    return "written"


def backfill_wallets(apply: bool):
    con_db, tmp = open_chatdb()
    ff = Firefly(_apply_env())
    ids = _account_ids(ff)
    idx = _index()
    rules = _rules()
    print(f"\n{'='*72}\nSMS WALLET BACKFILL — {'APPLY' if apply else 'DRY RUN'}\n{'='*72}")
    by_inst = defaultdict(list)
    for m in messages_since(con_db, BACKFILL_START):
        if m["inst"] in ("STC", "D360", "BARQ") and classify(m["text"]) == "txn":
            p = parse_txn(m)
            if p:
                p["rowid"] = m["rowid"]
                by_inst[m["inst"]].append(p)

    for inst in ("BARQ", "STC", "D360"):
        acct = WALLET_ACCOUNT[inst]
        txns = sorted(by_inst.get(inst, []), key=lambda t: t["ts"])
        net = sum((_signed(t) for t in txns), Decimal(0))
        opening = WALLET_CURRENT[acct] - net
        print(f"\n▸ {inst} → {acct}: {len(txns)} txns | net SAR {net:,.2f} | "
              f"back-solved 1 Jul opening SAR {opening:,.2f} (lands on {WALLET_CURRENT[acct]})")
        if inst == "BARQ":
            breaks, expl, ntop = barq_breaks_check(txns)
            print(f"    barq chain: {len(breaks)} break(s), {expl} explained by top-ups "
                  f"({ntop} top-ups total)")
            for d, gap, why in breaks:
                print(f"      break {d}: gap SAR {gap:,.2f} — {why}")
        if opening < 0:
            # negative opening => SMS history too incomplete to reconstruct.
            # Do NOT import fake history; set opening = current, dated today.
            print(f"    ⚠️ back-solved opening NEGATIVE ({opening:,.2f}) → {inst} SMS history "
                  f"incomplete. Skipping history import; opening = {WALLET_CURRENT[acct]} "
                  f"dated 7 Sep (monitoring starts now, live capture forward).")
            if apply:
                ff._req("PUT", f"accounts/{ids[acct]}",
                        {"opening_balance": f"{WALLET_CURRENT[acct]:.2f}",
                         "opening_balance_date": "2026-09-07",
                         "notes": f"SMS history incomplete (back-solve went negative); "
                                  f"opening set to current balance, monitoring from 7 Sep."})
                log(f"backfill {inst}: NEGATIVE opening -> monitoring-now at {WALLET_CURRENT[acct]}")
            continue
        if apply:
            ff._req("PUT", f"accounts/{ids[acct]}",
                    {"opening_balance": f"{opening:.2f}",
                     "opening_balance_date": BACKFILL_START.isoformat(),
                     "notes": f"Opening back-solved from 7 Sep balance {WALLET_CURRENT[acct]} "
                              f"minus net SMS {net}; reconcile monthly (app glance)."})
            w = d = u = 0
            for t in txns:
                r = _write_txn(ff, ids, idx, t["rowid"], t, rules)
                w += r == "written"; d += r == "dup"; u += r == "unmapped"
            log(f"backfill {inst}: opening={opening} written={w} dup={d} unmapped={u}")
            print(f"    applied: {w} written, {d} dup, {u} unmapped")
    if tmp:
        shutil.rmtree(os.path.dirname(tmp), ignore_errors=True)
    if apply:
        print("\n✅ Wallet backfill applied. Verify balances land on 56.14 / 25.15 / 20.03.")


def _apply_env():
    env = load_env()
    if (env.get("FIREFLY_ADMIN_TOKEN") or "").strip():
        env["FIREFLY_PAT"] = env["FIREFLY_ADMIN_TOKEN"]
    return env


def live_once():
    """Incremental capture since last processed rowid (launchd every 2 min).
    Wallets + SNB/SABB KNOWN templates import (tag sms); unknown bank templates
    -> sms_unknown.log (never the Review UI); filters dropped."""
    con_db, tmp = open_chatdb()
    ff = Firefly(_apply_env())
    ids = _account_ids(ff)
    idx = _index()
    rules = _rules()
    last = idx.execute("SELECT v FROM state WHERE k='last_rowid'").fetchone()
    last_rowid = int(last[0]) if last else 0
    written = dropped = unknown = 0
    maxrow = last_rowid
    for m in messages_since(con_db, BACKFILL_START):
        if m["rowid"] <= last_rowid:
            continue
        maxrow = max(maxrow, m["rowid"])
        c = classify(m["text"])
        if c != "txn":
            dropped += 1
            continue
        p = parse_txn(m)
        if not p:                                   # unknown template from a bank sender
            with open(UNKNOWN_LOG, "a", encoding="utf-8") as fh:
                fh.write(f"{datetime.now(timezone.utc).isoformat()}  {m['inst']} "
                         f"{m['text'][:140]}\n")
            unknown += 1
            continue
        p["rowid"] = m["rowid"]
        if _write_txn(ff, ids, idx, m["rowid"], p, rules) == "written":
            written += 1
    idx.execute("INSERT OR REPLACE INTO state VALUES ('last_rowid',?)", (str(maxrow),))
    idx.commit()
    log(f"live: written={written} dropped(filter)={dropped} unknown={unknown} "
        f"last_rowid={maxrow}")
    if tmp:
        shutil.rmtree(os.path.dirname(tmp), ignore_errors=True)
    print(f"live: {written} written, {dropped} filtered, {unknown} unknown->log")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="apply wallet backfill (writes)")
    ap.add_argument("--live", action="store_true", help="incremental capture (launchd)")
    args = ap.parse_args()
    if args.live:
        live_once()
    elif args.apply:
        backfill_wallets(apply=True)
    else:
        dry_run()


if __name__ == "__main__":
    main()
