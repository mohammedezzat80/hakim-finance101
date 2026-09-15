#!/usr/bin/env python3
"""HAKIM Statement Importer (Brief 03) — reads bank/card files from inbox/ and
imports them into Firefly III.

  DRY RUN (default): parse everything, print a report, WRITE NOTHING.
  APPLY:  python scripts/import_statements.py --apply   (after Mohamed approves)

Run with the importer venv:
  ./.venv-importer/bin/python scripts/import_statements.py

Hard rules (see Brief 03): Decimal only (never float); deterministic external_id
dedupe; BACKFILL_START cutoff; GET+POST only (never PUT/DELETE transactions);
never invent — unknown account/row is flagged, not guessed.
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import os
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

import xlrd
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ff import Firefly, load_env  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX = os.path.join(ROOT, "inbox")
DATA = os.path.join(ROOT, "data")
DB_PATH = os.path.join(DATA, "import_index.db")
LOG_PATH = os.path.join(ROOT, "logs", "importer.log")
MERCHANTS_PATH = os.path.join(DATA, "merchants.yaml")

BACKFILL_START = date(2026, 7, 1)
LLM_THRESHOLD = Decimal("0.8")

# --- account resolution (never invent; unknown -> flag/ask) ----------------
SNB_ACCOUNT_MAP = {"11100067564602": "Mohamed SNB main",
                   "13388180000100": "Sarah SNB main"}   # Sarah's SNB current (PDF), confirmed by Mohamed
CARD_LAST4_MAP = {
    "4331": "SABB Alfursan •4331",
    "5158": "SABB Mastercard •5158",   # renamed from •1437 (see report)
    "5019": "SABB Visa •5019",
}
SABB_ACCOUNT_DEFAULT = "SABB main"     # only one active SABB current account
# SNB credit-card .xls carry no card number; Mohamed assigned files explicitly
# (both cards are closed at the bank — payments/fees-only files are expected).
SNB_CARD_FILE_MAP = {
    "transactiontable-2.xls": "Mohamed SNB Mastercard •6510",
    "transactiontable-3.xls": "Mohamed SNB Alfursan •8381",
}

PAYMENT_TYPES = {"DIRECT DEBIT PAYMENT", "CREDIT CARD PAYMENT"}  # money INTO a card

# Current card debts as of 7 Sep 2026 (Mohamed). Opening(1 Jul) is back-solved:
#   opening_balance = -(current_debt) - net_effect_of_imported_txns
# so the card shows the real current debt after import; derivation noted per account.
CARD_CURRENT_DEBT = {
    "SABB Visa •5019": Decimal("15418.45"),
    "SABB Mastercard •5158": Decimal("30209.90"),
    "SABB Alfursan •4331": Decimal("31505.27"),
    "Mohamed SNB Mastercard •6510": Decimal("47168.38"),
    "Mohamed SNB Alfursan •8381": Decimal("6345.87"),
}
# Accounts with a known opening balance but no statement file: (amount, as_of_date).
MANUAL_OPENINGS = {
    "SABB Travel": (Decimal("6.00"), BACKFILL_START),   # dormant (•2153)
    "STC Pay": (Decimal("25.15"), date(2026, 9, 7)),    # digital wallets: monitoring
    "D360": (Decimal("20.03"), date(2026, 9, 7)),        # starts today, no history
    "Barq": (Decimal("56.14"), date(2026, 9, 7)),
}


# --------------------------------------------------------------------------
@dataclass
class Row:
    source_file: str
    fmt: str
    account: str | None
    txn_date: date
    amount: Decimal              # signed: negative = out/charge, positive = in/payment
    raw_desc: str                # in-memory only (may contain card #) — never stored
    desc: str                    # cleaned for storage (card numbers stripped)
    ttype: str
    balance: Decimal | None = None
    needs_assignment: bool = False
    unparseable: bool = False
    note: str = ""
    category: str | None = None
    category_source: str = ""
    external_id: str = ""
    is_transfer: bool = False
    transfer_to: str | None = None


# --- helpers ---------------------------------------------------------------
_NUM = re.compile(r"[^0-9.\-]")
_CARD16 = re.compile(r"\d{16}")
_PUA = re.compile(r"[-]")   # private-use glyphs (SAR symbol etc.)


def dec(raw) -> Decimal:
    if isinstance(raw, (int, float)):
        return Decimal(str(raw))
    s = _PUA.sub("", str(raw))
    s = s.replace("SAR", "").replace(",", "").strip()
    s = _NUM.sub("", s)
    if s in ("", "-", "."):
        raise InvalidOperation(f"empty amount from {raw!r}")
    return Decimal(s)


def clean_desc(raw: str) -> str:
    """Storage-safe description: strip 16-digit card numbers, collapse whitespace."""
    s = _CARD16.sub("", raw or "")
    return re.sub(r"\s+", " ", s).strip()


def norm_for_hash(desc: str) -> str:
    s = _CARD16.sub("", (desc or "").lower())
    return re.sub(r"\s+", " ", s).strip()


def compose_desc(ttype: str, ref: str) -> str:
    """Stored description: the transaction TYPE (col C) leads, the reference (col D)
    follows — 'SADAD Payment — 093-2347…'.  external_id is derived from the reference
    alone (make_external_id uses r.desc), so composing here never affects idempotency."""
    t = (ttype or "").strip()
    ref = (ref or "").strip()
    if t and ref and norm_for_hash(t) not in norm_for_hash(ref):
        return f"{t} — {ref}"[:600]   # generous: keep the whole cell incl. trailing counterparty name
    return (t or ref)[:600]


def type_tag(ttype: str) -> str | None:
    t = (ttype or "").strip()
    return f"txn-type:{t}" if t else None


def process_tags(ttype: str) -> list[str]:
    """Feed the transaction type into processing: FX candidates from international
    card use; the txn-type tag itself. (Transfer-confidence uses ttype in matching;
    SADAD→bill-category suggestion lives in the desk.)"""
    out = []
    tt = type_tag(ttype)
    if tt:
        out.append(tt)
    low = (ttype or "").lower()
    if "international" in low or "pos purchase international" in low:
        out.append("fx-candidate")
    return out


def make_external_id(account: str, d: date, amount: Decimal, desc: str, occ: int = 0) -> str:
    # `occ` distinguishes genuine same-day / same-amount / same-merchant duplicates
    # (e.g. 3 identical airline installments). Assigned by stable parse order, so
    # re-importing the same/overlapping file reproduces the same ids (idempotent).
    key = f"{account}|{d.isoformat()}|{amount:.2f}|{norm_for_hash(desc)}|{occ}"
    return "hakim-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


def parse_csv_date(s: str) -> date:
    return datetime.strptime(s.strip(), "%d %b %Y").date()


# --- file classification ---------------------------------------------------
def classify(path: str) -> str:
    low = path.lower()
    if low.endswith(".pdf"):
        import subprocess
        head = subprocess.run(["pdftotext", "-layout", "-l", "1", path, "-"],
                              capture_output=True, text=True).stdout
        if "Transactions History" in head or "Current Account" in head:
            return "P"      # SNB text-PDF statement
        return "?"          # scanned/unknown PDF — flag, don't guess (OCR path would go here)
    if low.endswith(".xls"):
        wb = xlrd.open_workbook(path)
        sh = wb.sheet_by_index(0)
        head = " ".join(
            str(sh.cell_value(r, c))
            for r in range(min(5, sh.nrows)) for c in range(sh.ncols)
        )
        if "Credit Card Transactions" in head:
            return "B"      # SNB credit card
        if "Current Account" in head or "Statement of Account" in head:
            return "A"      # SNB current account
        return "?"
    if low.endswith(".csv"):
        with open(path, encoding="utf-8-sig") as fh:
            first = fh.readline()
        cols = [c.strip() for c in first.split(",")]
        if cols and cols[0].lower().startswith("transaction date"):
            return "D"      # SABB credit card
        if len(cols) >= 3 and cols[0].lower() == "date" and "amount" in cols[2].lower():
            return "C"      # SABB current account
    return "?"


def _find_header_row(sh, label="Date"):
    for r in range(min(8, sh.nrows)):
        for c in range(sh.ncols):
            if str(sh.cell_value(r, c)).strip() == label:
                return r
    return None


def _header_cols(sh, hrow) -> dict:
    cols = {}
    for c in range(sh.ncols):
        v = str(sh.cell_value(hrow, c)).strip()
        if v:
            cols[v] = c
    return cols


def _col(cols: dict, *names) -> int | None:
    for n in names:
        for k, v in cols.items():
            if k.lower().startswith(n.lower()):
                return v
    return None


# --- parsers ---------------------------------------------------------------
def parse_snb_account(path: str) -> list[Row]:
    wb = xlrd.open_workbook(path)
    sh = wb.sheet_by_index(0)
    blob = " ".join(str(sh.cell_value(r, c)) for r in range(min(5, sh.nrows))
                    for c in range(sh.ncols))
    m = re.search(r"Current Account\s+(\d+)", blob)
    acct = SNB_ACCOUNT_MAP.get(m.group(1)) if m else None
    needs = acct is None
    hrow = _find_header_row(sh)
    cols = _header_cols(sh, hrow)
    dcol = _col(cols, "Date")
    tcol = _col(cols, "Transaction type", "Transaction")
    ccol = _col(cols, "Description")
    acol = _col(cols, "Amount")
    bcol = _col(cols, "Balance")
    rows = []
    for r in range(hrow + 1, sh.nrows):
        dv = sh.cell_value(r, dcol)
        if dv in ("", None):
            continue
        try:
            d = xlrd.xldate.xldate_as_datetime(float(dv), wb.datemode).date()
            amt = dec(sh.cell_value(r, acol))
            bal = dec(sh.cell_value(r, bcol)) if bcol is not None else None
        except Exception as e:
            rows.append(Row(path, "A", acct, date(1970, 1, 1), Decimal(0), str(dv),
                            "", "", unparseable=True, note=f"parse error: {e}"))
            continue
        raw = str(sh.cell_value(r, ccol)) if ccol is not None else ""
        ttype = str(sh.cell_value(r, tcol)).strip() if tcol is not None else ""
        rows.append(Row(path, "A", acct, d, amt, raw, clean_desc(raw), ttype,
                        balance=bal, needs_assignment=needs))
    return rows


def parse_snb_card(path: str) -> list[Row]:
    wb = xlrd.open_workbook(path)
    sh = wb.sheet_by_index(0)
    base = os.path.basename(path).lower()
    acct = SNB_CARD_FILE_MAP.get(base)
    needs = acct is None
    hrow = _find_header_row(sh)
    cols = _header_cols(sh, hrow)
    dcol = _col(cols, "Date")
    tcol = _col(cols, "Transaction Type", "Transaction")
    ccol = _col(cols, "Description")
    acol = _col(cols, "Amount")
    rows = []
    for r in range(hrow + 1, sh.nrows):
        dv = sh.cell_value(r, dcol)
        if dv in ("", None):
            continue
        ttype = str(sh.cell_value(r, tcol)).strip()
        try:
            d = xlrd.xldate.xldate_as_datetime(float(dv), wb.datemode).date()
            mag = dec(sh.cell_value(r, acol))
        except Exception as e:
            rows.append(Row(path, "B", acct, date(1970, 1, 1), Decimal(0), ttype, "",
                            ttype, unparseable=True, note=f"parse error: {e}"))
            continue
        up = ttype.upper()
        if up in PAYMENT_TYPES:
            amt = mag                      # payment into card (reduces debt)
        elif up.startswith("DEBIT"):
            amt = -mag                     # charge/fee
        else:
            rows.append(Row(path, "B", acct, d, mag, ttype, clean_desc(ttype), ttype,
                            unparseable=True, note=f"unknown card txn type: {ttype!r}"))
            continue
        raw = str(sh.cell_value(r, ccol)) if ccol is not None else ttype
        rows.append(Row(path, "B", acct, d, amt, raw, clean_desc(raw), ttype,
                        needs_assignment=needs))
    return rows


def parse_sabb_account(path: str) -> list[Row]:
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh, skipinitialspace=True)
        header = [h.strip() for h in next(reader)]
        idx = {h.lower(): i for i, h in enumerate(header)}
        di = idx.get("date")
        ci = idx.get("description")
        ai = next((i for h, i in idx.items() if h.startswith("amount")), None)
        bi = next((i for h, i in idx.items() if h.startswith("balance")), None)
        for rec in reader:
            if not rec or len(rec) <= max(di, ci, ai):
                continue
            try:
                d = parse_csv_date(rec[di])
                amt = dec(rec[ai])
                bal = dec(rec[bi]) if bi is not None and rec[bi].strip() else None
            except Exception as e:
                rows.append(Row(path, "C", SABB_ACCOUNT_DEFAULT, date(1970, 1, 1),
                                Decimal(0), " ".join(rec), "", "", unparseable=True,
                                note=f"parse error: {e}"))
                continue
            raw = rec[ci]
            rows.append(Row(path, "C", SABB_ACCOUNT_DEFAULT, d, amt, raw,
                            clean_desc(raw), "", balance=bal))
    return rows


def parse_sabb_card(path: str) -> list[Row]:
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh, skipinitialspace=True)
        header = [h.strip() for h in next(reader)]
        idx = {h.lower(): i for i, h in enumerate(header)}
        di = idx.get("transaction date")
        ci = idx.get("description")
        ai = next((i for h, i in idx.items() if h.startswith("amount(sar")), None)
        for rec in reader:
            if not rec or len(rec) <= max(di, ci, ai):
                continue
            raw = rec[ci]
            m = _CARD16.match(raw.strip())
            last4 = m.group(0)[-4:] if m else None
            acct = CARD_LAST4_MAP.get(last4) if last4 else None
            needs = acct is None
            try:
                d = parse_csv_date(rec[di])
                amt = dec(rec[ai])
            except Exception as e:
                rows.append(Row(path, "D", acct, date(1970, 1, 1), Decimal(0), raw,
                                "", "", unparseable=True, note=f"parse error: {e}"))
                continue
            rows.append(Row(path, "D", acct, d, amt, raw, clean_desc(raw), "",
                            needs_assignment=needs,
                            note=("unknown card " + (last4 or "?")) if needs else ""))
    return rows


def parse_snb_pdf(path: str) -> list[Row]:
    """SNB 'Transactions History' PDF (text-based). Same normalized Row shape as the XLS parser so the
    rest of the pipeline (dedup, twin-match, rules, opening-balance reconciliation) is untouched — PDF
    is just another mouth. A transaction spans several layout lines; the DATE line carries the signed
    amount + running balance, the merchant name sits on the line above, and 'VAT CHRG/Charges' tails
    below (dropped as noise). Arabic passes through clean_desc unharmed."""
    import subprocess
    txt = subprocess.run(["pdftotext", "-layout", path, "-"],
                         capture_output=True, text=True).stdout
    header = txt[:2500]
    # the SNB account number is the 12–16 digit run in the header (e.g. 13388180000100); dates never
    # form a 12+ digit run, so this is unambiguous. Map it → account name (never guess if unknown).
    am = re.search(r"\b(\d{12,16})\b", header)
    acct = SNB_ACCOUNT_MAP.get(am.group(1)) if am else None
    needs = acct is None
    lines = txt.split("\n")
    dre = re.compile(r"^\s*(\d{2}/\d{2}/\d{4})\s+(.*?)\s+(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$")
    dls = [i for i, ln in enumerate(lines) if dre.match(ln)]
    rows = []
    for k, i in enumerate(dls):
        m = dre.match(lines[i])
        dd, mm, yy = m.group(1).split("/")
        try:
            d = date(int(yy), int(mm), int(dd))
        except Exception as e:
            rows.append(Row(path, "P", acct, date(1970, 1, 1), Decimal(0), lines[i], "", "",
                            unparseable=True, note=f"date parse: {e}"))
            continue
        amt = dec(m.group(3))
        bal = dec(m.group(4))
        mid = m.group(2)
        prev = lines[i - 1].strip() if i > 0 else ""            # the merchant/primary line above
        if dre.match(prev) or prev.startswith(("VAT CHRG", "Charges")):
            prev = ""
        raw = (prev + " " + mid).strip()
        ttype = raw.split("CITY:")[0].strip()[:60] or "transaction"   # leading descriptor as the type
        rows.append(Row(path, "P", acct, d, amt, raw, clean_desc(raw), ttype,
                        balance=bal, needs_assignment=needs))
    return rows


PARSERS = {"A": parse_snb_account, "B": parse_snb_card,
           "C": parse_sabb_account, "D": parse_sabb_card, "P": parse_snb_pdf}


# --- categorisation (rules first) ------------------------------------------
def load_rules():
    with open(MERCHANTS_PATH, encoding="utf-8") as fh:
        y = yaml.safe_load(fh) or {}
    return [(re.compile(r["pattern"], re.I), r) for r in y.get("rules", [])]


def categorize(row: Row, rules):
    for rx, r in rules:
        if rx.search(row.desc) or rx.search(row.raw_desc):
            row.category = r["category"]
            row.category_source = "rule"
            return
    row.category = "To review"
    row.category_source = "none"


# --- Part A: cross-run transfer matching (new rows <-> existing ledger) -----
_XFER_ISH = re.compile(r"تحويل|transfer|ac to ac|\bips\b|ipsp|sadad|card:", re.I)


def ledger_transferables(ff):
    """Existing ledger withdrawals/deposits eligible to fuse into a transfer:
    not already transfers, not manually converted/confirmed."""
    out = []
    for ttype in ("withdrawal", "deposit"):
        for g in ff.get_all("transactions", type=ttype):
            for s in g["attributes"]["transactions"]:
                tags = s.get("tags") or []
                if "confirmed" in tags:
                    continue
                acct = s.get("source_name") if ttype == "withdrawal" else s.get("destination_name")
                amt = abs(Decimal(str(s["amount"])))
                out.append({"id": g["id"], "type": ttype, "account": acct,
                            "amount": (-amt if ttype == "withdrawal" else amt),
                            "date": (s.get("date") or "")[:10],
                            "desc": s.get("description") or "",
                            "external_id": s.get("external_id"), "tags": tags})
    return out


def proposed_foreign(ff):
    """Manual 🟡 foreign entries awaiting bank confirmation (trust:proposed + foreign_amount)."""
    out = []
    for tp in ("withdrawal", "deposit"):
        for g in ff.get_all("transactions", type=tp):
            s = g["attributes"]["transactions"][0]
            if "trust:proposed" in (s.get("tags") or []) and s.get("foreign_amount"):
                acct = s.get("source_name") if tp == "withdrawal" else s.get("destination_name")
                out.append({"id": g["id"], "jid": s["transaction_journal_id"], "account": acct,
                            "amount": abs(float(s["amount"])), "foreign": abs(float(s["foreign_amount"])),
                            "date": (s.get("date") or "")[:10], "tags": s.get("tags") or [],
                            "settled": False})
    return out


def try_settle(ff, pf_list, r):
    """If bank row r matches a 🟡 foreign entry (same account; amount within 5% OR the
    foreign amount matches; date ±3d), update it to the bank's TRUE figure, keep
    note/receipt/tags, mark trust:imported-confirmed. Returns True if settled."""
    for pf in pf_list:
        if pf["settled"] or pf["account"] != r.account:
            continue
        amt = Decimal(str(pf["amount"]))
        fa = Decimal(str(pf["foreign"]))
        ba = abs(r.amount)
        if not (abs(amt - ba) <= Decimal("0.05") * amt or abs(fa - ba) < Decimal("0.01")):
            continue
        try:
            if abs((date.fromisoformat(pf["date"]) - r.txn_date).days) > 3:
                continue
        except Exception:
            continue
        newtags = [t for t in pf["tags"] if t != "trust:proposed"] + ["trust:imported-confirmed"]
        ff._req("PUT", f"transactions/{pf['id']}", {"transactions": [{
            "transaction_journal_id": pf["jid"], "amount": f"{abs(r.amount):.2f}", "tags": newtags}]})
        pf["settled"] = True
        log(f"SETTLE foreign txn {pf['id']}: {amt} -> {abs(r.amount):.2f} (bank-confirmed, was proposed)")
        return True
    return False


def propose_cross_run(new_rows, ledger):
    """Pair a NEW row with an EXISTING ledger row: equal |amount|, OPPOSITE
    direction, dates within 3 days, DIFFERENT internal accounts. Proposals only —
    Mohamed approves before any fusion (agents draft, Mohamed decides)."""
    props, used = [], set()
    for r in new_rows:
        for lg in ledger:
            if id(lg) in used or lg["account"] == r.account:
                continue
            if r.external_id and lg.get("external_id") == r.external_id:
                continue                                    # same txn (re-run self-match)
            if abs(r.amount) != abs(lg["amount"]):
                continue
            if (r.amount < 0) == (lg["amount"] < 0):        # need opposite directions
                continue
            try:
                ld = date.fromisoformat(lg["date"])
            except Exception:
                continue
            if abs((r.txn_date - ld).days) > 3:
                continue
            props.append((r, lg))
            used.add(id(lg))
            break
    return props


# --- transfer matching -----------------------------------------------------
# descriptions that mean the money left to an EXTERNAL party (never internal)
_EXTERNAL = re.compile(
    r"الاهل والاصدقاء|family and friends|personal transfer to|ben ?id|benf|"
    r"مؤسسة|شركة|est\b|company", re.I)


def _in_last4(account: str | None) -> str:
    return account.split("•")[-1].strip()[-4:] if account and "•" in account else ""


def _dest_last4s(desc: str) -> set:
    """Last-4 card identifiers referenced in a description — full 16-digit numbers
    AND masked forms like '******6510', '***6510', '532448******6510'."""
    out = {m[-4:] for m in _CARD16.findall(desc)}
    out |= set(re.findall(r"[*xX•·]{2,}\s*(\d{4})", desc))
    out |= set(re.findall(r"\d{4,}\*+(\d{4})", desc))
    return out


def match_transfers(rows: list[Row]):
    """Return (confirmed, candidates).

    confirmed: outflow explicitly names the destination card's 16-digit number
      (or its last-4) — high confidence, safe to auto-write as ONE transfer.
    candidates: equal/opposite within 3 days, different internal accounts, one side
      a card payment, NOT an external transfer — reported for Mohamed to confirm,
      NOT auto-written (we don't guess which card a generic 'Transfer to Master
      Card' means).
    """
    live = [r for r in rows if not r.unparseable and r.account]
    outs = [r for r in live if r.amount < 0]
    ins = [r for r in live if r.amount > 0]
    confirmed, candidates, used = [], [], set()

    def find(o, strong: bool):
        o_cards = _dest_last4s(o.raw_desc)
        for i in ins:
            if id(i) in used or i is o or i.account == o.account:
                continue
            if o.amount != -i.amount or abs((o.txn_date - i.txn_date).days) > 3:
                continue
            in4 = _in_last4(i.account)
            if strong:
                if in4 and in4 in o_cards:
                    return i
            else:
                if _EXTERNAL.search(o.raw_desc):
                    continue
                pay = i.ttype.upper() in PAYMENT_TYPES or "payment" in i.raw_desc.lower()
                names_card = re.search(r"credit|master ?card|visa|to card", o.raw_desc, re.I)
                if pay or names_card:
                    return i
        return None

    for o in outs:                                   # strong pass first
        if id(o) in used:
            continue
        i = find(o, strong=True)
        if i:
            confirmed.append((o, i)); used.add(id(o)); used.add(id(i))
    for o in outs:                                   # weak pass -> candidates
        if id(o) in used:
            continue
        i = find(o, strong=False)
        if i:
            candidates.append((o, i)); used.add(id(o)); used.add(id(i))
    return confirmed, candidates


# --- dedupe index ----------------------------------------------------------
def db_conn():
    os.makedirs(DATA, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS imported (
        external_id TEXT PRIMARY KEY, account TEXT, txn_date TEXT,
        amount TEXT, description TEXT, firefly_id TEXT, run_id TEXT)""")
    return con


def already_imported(con, ext_id: str) -> bool:
    return con.execute("SELECT 1 FROM imported WHERE external_id=?", (ext_id,)).fetchone() is not None


# --- opening balance derivation --------------------------------------------
def opening_balance(rows: list[Row]):
    """Derive opening balance at BACKFILL_START from the running-balance column.

    The Balance column is balance-AFTER-txn and files are newest-first, so we work
    in FILE ORDER (not date-sorted — same-date rows must keep their true sequence).
    Returns (opening, derived_close, file_close, ok)."""
    inrange = [r for r in rows if not r.unparseable and r.balance is not None
               and r.txn_date >= BACKFILL_START]
    if not inrange:
        return None
    # ensure newest-first (guard in case a source is oldest-first)
    if inrange[0].txn_date < inrange[-1].txn_date:
        inrange = list(reversed(inrange))
    newest, oldest = inrange[0], inrange[-1]
    opening = oldest.balance - oldest.amount           # balance before the oldest in-range txn
    total = sum((r.amount for r in inrange), Decimal(0))
    derived_close = opening + total
    file_close = newest.balance                        # latest statement balance
    return opening, derived_close, file_close, (derived_close == file_close)


def opening_for_account(acct: str, file_rows_map: dict, inrange_all: list):
    """Opening/close for an account that may span MULTIPLE (overlapping) files.

    Opening comes from the file whose data starts earliest; close from the file
    whose data ends latest; the arithmetic check sums the run's DEDUPED rows for
    the account (so overlap isn't double-counted). Returns (opening, derived_close,
    file_close, ok) or None."""
    files = []
    for rows in file_rows_map.values():
        inr = [r for r in rows if not r.unparseable and r.balance is not None
               and r.account == acct and r.txn_date >= BACKFILL_START]
        if not inr:
            continue
        if inr[0].txn_date < inr[-1].txn_date:         # normalise to newest-first
            inr = list(reversed(inr))
        files.append(inr)
    if not files:
        return None
    earliest = min(files, key=lambda f: f[-1].txn_date)   # earliest start
    latest = max(files, key=lambda f: f[0].txn_date)      # latest end
    opening = earliest[-1].balance - earliest[-1].amount
    file_close = latest[0].balance
    total = sum((r.amount for r in inrange_all if r.account == acct), Decimal(0))
    derived_close = opening + total
    return opening, derived_close, file_close, (derived_close == file_close)


# --- writer (only runs on --apply and only when there are no blockers) -----
def _record(con, ext, acct, d, amount, desc, fid, run_id):
    con.execute("INSERT OR IGNORE INTO imported VALUES (?,?,?,?,?,?,?)",
                (ext, acct, d.isoformat(), f"{amount:.2f}", (desc or "")[:120], fid, run_id))
    con.commit()


def _post_txn(ff, body):
    r = ff.post("transactions", {"error_if_duplicate_hash": False,
                                 "apply_rules": False, "transactions": [body]})
    return r["data"]["id"]


def _apply(con, ff, ids, writable, confirmed, account_openings, run_id):
    written = skipped = settled = 0
    tag = f"import:{run_id}"
    pf_list = proposed_foreign(ff)   # 🟡 manual foreign entries awaiting bank confirmation

    def set_open(acct, bal, note=None, when=BACKFILL_START):
        body = {"opening_balance": f"{bal:.2f}",
                "opening_balance_date": when.isoformat()}
        if note:
            body["notes"] = note
        try:
            ff._req("PUT", f"accounts/{ids[acct]}", body)
        except Exception as e:
            print(f"  opening-balance set failed for {acct}: {e}")

    # bank assets — validated running-balance opening (per account, across files)
    for acct, ob in account_openings.items():
        if ob[3] and acct in ids:
            set_open(acct, ob[0])
    # manual openings (dormant accounts / wallets, no file) — dated as given
    for acct, (bal, when) in MANUAL_OPENINGS.items():
        if acct in ids:
            set_open(acct, bal, when=when)
    # card liabilities — back-solve so post-import balance == real current debt
    for acct, current_debt in CARD_CURRENT_DEBT.items():
        if acct not in ids:
            continue
        ne = sum((r.amount for r in writable if r.account == acct), Decimal(0))
        ne += sum((abs(o.amount) for o, i in confirmed if i.account == acct), Decimal(0))
        ne -= sum((abs(o.amount) for o, i in confirmed if o.account == acct), Decimal(0))
        opening = -current_debt - ne
        set_open(acct, opening,
                 f"Opening debt @ {BACKFILL_START} back-solved from 7 Sep 2026 balance "
                 f"SAR {current_debt:,.2f} minus net of imported transactions "
                 f"(SAR {ne:,.2f}); reconcile at next import.")
    # confirmed transfers -> one Firefly transfer each
    from collections import Counter
    toccur = Counter()
    for o, i in confirmed:
        tkey = (o.account, i.account, o.txn_date, f"{abs(o.amount):.2f}", norm_for_hash(o.desc))
        ext = make_external_id(f"{o.account}>{i.account}", o.txn_date, abs(o.amount), o.desc,
                               toccur[tkey])
        toccur[tkey] += 1
        if already_imported(con, ext):
            skipped += 1
            continue
        fid = _post_txn(ff, {"type": "transfer", "date": o.txn_date.isoformat(),
                             "amount": f"{abs(o.amount):.2f}",
                             "description": compose_desc(o.ttype, o.desc) or "Transfer",
                             "source_id": ids[o.account], "destination_id": ids[i.account],
                             "currency_code": "SAR", "external_id": ext,
                             "tags": [tag] + process_tags(o.ttype)})
        _record(con, ext, o.account, o.txn_date, abs(o.amount), o.desc, fid, run_id)
        written += 1
    # plain transactions
    for r in writable:
        if not r.external_id or already_imported(con, r.external_id):
            skipped += 1
            continue
        if try_settle(ff, pf_list, r):     # bank row confirms a 🟡 manual foreign entry
            settled += 1
            continue
        common = {"date": r.txn_date.isoformat(), "amount": f"{abs(r.amount):.2f}",
                  "description": compose_desc(r.ttype, r.desc) or "Unknown",
                  "category_name": r.category, "currency_code": "SAR",
                  "external_id": r.external_id, "tags": [tag] + process_tags(r.ttype)}
        if r.amount < 0:
            body = {**common, "type": "withdrawal", "source_id": ids[r.account],
                    "destination_name": (r.desc or "Unknown")[:60]}
        else:
            body = {**common, "type": "deposit", "source_name": (r.desc or "Unknown")[:60],
                    "destination_id": ids[r.account]}
        fid = _post_txn(ff, body)
        _record(con, r.external_id, r.account, r.txn_date, abs(r.amount), r.desc, fid, run_id)
        written += 1
    if settled:
        log(f"apply: settled {settled} 🟡 foreign entries to bank-true figures")
    return written, skipped


def _fuse_existing(ff, ids, cross_props, ledger, run_id):
    """Part A fusion: turn each approved (new ↔ existing) proposal into ONE Firefly
    transfer and delete the one-sided leg(s). Same strict before/after logging as
    Review-UI conversions. Preserves an external_id so re-import dedupes."""
    ext_index = {lg["external_id"]: lg["id"] for lg in ledger if lg.get("external_id")}
    seen, fused = set(), 0
    for r, lg in cross_props:
        pk = frozenset([r.external_id or f"r{id(r)}", lg.get("external_id") or lg["id"]])
        if pk in seen:
            continue
        seen.add(pk)
        src, dst = (r.account, lg["account"]) if r.amount < 0 else (lg["account"], r.account)
        if src not in ids or dst not in ids:
            print(f"  skip fuse (unknown account {src}/{dst})")
            continue
        d = min(str(r.txn_date), lg["date"])
        rid = ext_index.get(r.external_id)     # r's own ledger txn (already-imported case)
        before = {"leg_a": {"id": rid, "account": r.account, "amount": str(r.amount),
                            "date": str(r.txn_date), "external_id": r.external_id},
                  "leg_b": {"id": lg["id"], "account": lg["account"],
                            "amount": str(lg["amount"]), "date": lg["date"],
                            "external_id": lg.get("external_id")}}
        new = _post_txn(ff, {"type": "transfer", "date": d, "amount": f"{abs(r.amount):.2f}",
                             "description": "Fused internal transfer (Part A)",
                             "source_id": ids[src], "destination_id": ids[dst],
                             "currency_code": "SAR",
                             "external_id": r.external_id or lg.get("external_id"),
                             "tags": [f"fused:{run_id}"]})
        ff._req("DELETE", f"transactions/{lg['id']}")
        if rid:
            ff._req("DELETE", f"transactions/{rid}")
        log(f"FUSE {src}->{dst} SAR {abs(r.amount):.2f} new={new} before={before}")
        fused += 1
    return fused


def _write_review_queue(writable):
    from collections import defaultdict
    groups = defaultdict(list)
    for r in writable:
        if r.category == "To review":
            groups[(r.desc[:40] or "(blank)")].append(r)
    ordered = sorted(groups.items(), key=lambda kv: -len(kv[1]))
    lines = ["# Review queue — uncategorised transactions", "",
             "Answer inline, e.g. `CRAVIA ARABIA = Five Guys = Eating out & delivery`,",
             "then run scripts/apply_reviews.py (adds a merchants.yaml rule + recategorises).",
             "", f"{len(ordered)} distinct merchants to review:", ""]
    for desc, rs in ordered:
        tot = sum((abs(x.amount) for x in rs), Decimal(0))
        lines.append(f"- **{desc}** ×{len(rs)}  (SAR {tot:,.2f})  [{rs[0].account}]")
    with open(os.path.join(DATA, "review_queue.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


# --- report ----------------------------------------------------------------
def log(msg):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(f"{datetime.now(timezone.utc).isoformat()}  {msg}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write to Firefly (default: dry run)")
    ap.add_argument("--write-candidates", action="store_true",
                    help="treat candidate transfers as confirmed (Mohamed-approved)")
    ap.add_argument("--fuse-existing", action="store_true",
                    help="fuse cross-run proposals into transfers (Part A; needs --apply)")
    args = ap.parse_args()
    mode = "APPLY" if args.apply else "DRY RUN"

    files = sorted(f for f in glob.glob(os.path.join(INBOX, "**", "*"), recursive=True)
                   if f.lower().endswith((".xls", ".csv", ".pdf")))
    rules = load_rules()
    con = db_conn()

    env = load_env()
    if (env.get("FIREFLY_ADMIN_TOKEN") or "").strip():
        env["FIREFLY_PAT"] = env["FIREFLY_ADMIN_TOKEN"]
        token_src = "FIREFLY_ADMIN_TOKEN"
    else:
        token_src = "FIREFLY_PAT (⚠️ FIREFLY_ADMIN_TOKEN empty — using agent token as fallback)"

    print(f"\n{'='*74}\nHAKIM STATEMENT IMPORTER — {mode}\nBackfill start: {BACKFILL_START} | "
          f"files: {len(files)} | token: {token_src}\n{'='*74}")
    from collections import Counter
    all_rows: list[Row] = []
    per_file = []
    file_rows_map = {}
    for path in files:
        fmt = classify(path)
        if fmt not in PARSERS:
            per_file.append((path, fmt, None, 0, 0, 0, 0, Decimal(0)))
            print(f"\n⚠️  {os.path.relpath(path, ROOT)} — UNRECOGNISED format, skipped")
            continue
        rows = PARSERS[fmt](path)
        occ = Counter()                      # PER-FILE: overlapping rows across files
        for r in rows:                       # get the SAME id (dedup); genuine same-file
            if not r.unparseable:            # duplicates get distinct occ -> distinct ids
                categorize(r, rules)
                if r.account and r.txn_date >= BACKFILL_START:
                    base = (r.account, r.txn_date, f"{r.amount:.2f}", norm_for_hash(r.desc))
                    r.external_id = make_external_id(r.account, r.txn_date, r.amount,
                                                     r.desc, occ[base])
                    occ[base] += 1
        all_rows.extend(rows)
        file_rows_map[path] = rows
        acct = rows[0].account if rows else None
        needs = any(r.needs_assignment for r in rows)
        inrange = [r for r in rows if not r.unparseable and r.txn_date >= BACKFILL_START]
        before = sum(1 for r in rows if not r.unparseable and r.txn_date < BACKFILL_START)
        per_file.append((path, fmt, acct if not needs else "⚠️ NEEDS ASSIGNMENT",
                         len(rows), len(inrange), before,
                         sum(1 for r in rows if r.unparseable),
                         sum((r.amount for r in inrange), Decimal(0))))

    # run-level dedup of in-range rows by external_id (handles OVERLAPPING exports)
    seen, inrange_all, overlap = set(), [], 0
    for r in all_rows:
        if r.unparseable or not r.account or r.txn_date < BACKFILL_START:
            continue
        if r.needs_assignment:
            inrange_all.append(r)            # kept for reporting; no external_id
            continue
        if r.external_id in seen:
            overlap += 1
            continue
        seen.add(r.external_id)
        inrange_all.append(r)

    # per-account opening balances (across files, dedup-aware)
    account_openings = {}
    for acct in sorted({r.account for r in inrange_all if r.balance is not None and r.account}):
        ob = opening_for_account(acct, file_rows_map, inrange_all)
        if ob:
            account_openings[acct] = ob

    # transfer matching on deduped rows
    confirmed, candidates = match_transfers(inrange_all)
    if args.write_candidates and candidates:
        confirmed = confirmed + candidates
        candidates = []
    confirmed_ids = set()
    for o, i in confirmed:
        confirmed_ids.add(id(o)); confirmed_ids.add(id(i))
    candidate_ids = set()
    for o, i in candidates:
        candidate_ids.add(id(o)); candidate_ids.add(id(i))

    # --- print per-file report ---
    fmt_names = {"A": "SNB current acct", "B": "SNB credit card",
                 "C": "SABB current acct", "D": "SABB credit card"}
    for (path, fmt, acct, total, nin, before, bad, s) in per_file:
        print(f"\n▸ {os.path.relpath(path, ROOT)}")
        print(f"    format: {fmt} ({fmt_names.get(fmt,'?')}) | account: {acct}")
        print(f"    rows: {total} total | {nin} in-range (≥{BACKFILL_START}) | "
              f"{before} before cutoff | {bad} unparseable")
        print(f"    sum of in-range amounts: SAR {s:,.2f}")

    print(f"\n{'-'*74}\nOPENING BALANCES (banks, derived across all files):")
    for acct, ob in account_openings.items():
        opening, dclose, fclose, ok = ob
        flag = "✅ matches" if ok else "❌ MISMATCH — will not import"
        print(f"  {acct}: opening SAR {opening:,.2f} → derived close {dclose:,.2f} "
              f"vs statement {fclose:,.2f} {flag}")

    # --- transfers ---
    print(f"\n{'-'*74}\nCONFIRMED INTERNAL TRANSFERS (card-number anchored): {len(confirmed)}")
    for o, i in confirmed:
        print(f"  • {o.txn_date}  SAR {abs(o.amount):,.2f}  {o.account} → {i.account}"
              f"   [{o.desc[:40]}]")
    print(f"\nCANDIDATE TRANSFERS — need Mohamed to confirm (NOT auto-written): {len(candidates)}")
    for o, i in candidates:
        print(f"  ? {o.txn_date}  SAR {abs(o.amount):,.2f}  {o.account} → {i.account}"
              f"   [{o.desc[:45]}]")

    # --- dedupe / write preview ---
    writable = [r for r in inrange_all if r.account and not r.needs_assignment
                and id(r) not in confirmed_ids and id(r) not in candidate_ids]
    dupes = sum(1 for r in writable if r.external_id and already_imported(con, r.external_id))
    print(f"\n{'-'*74}\nWRITE PREVIEW")
    print(f"  plain transactions to write: {len(writable)}")
    print(f"  transfers to write: {len(confirmed)} | candidate transfers held: {len(candidates)}")
    print(f"  overlap duplicates removed within this run: {overlap}")
    print(f"  already in dedupe index (would skip): {dupes}")
    to_review = sum(1 for r in writable if r.category == 'To review')
    print(f"  auto-categorised by rules: {len(writable)-to_review} | To review: {to_review}")

    # --- live check: do the target Firefly accounts exist? ---
    used_accounts = {r.account for r in inrange_all if r.account and not r.needs_assignment}
    used_accounts |= set(MANUAL_OPENINGS)
    missing_accounts = []
    try:
        ff = Firefly(env)
        existing = set()
        for t in ("asset", "liability"):
            for a in ff.get_all("accounts", type=t):
                existing.add(a["attributes"]["name"])
        missing_accounts = sorted(u for u in used_accounts if u not in existing)
    except Exception as e:
        ff = None
        print(f"\n(account existence check skipped: {e})")

    # --- Part A: cross-run transfer proposals (new rows ↔ existing ledger) ---
    cross_props, ledger = [], []
    if ff is not None:
        transferish = [r for r in writable
                       if _XFER_ISH.search(r.raw_desc or "") or _XFER_ISH.search(r.desc or "")]
        if transferish:
            try:
                ledger = ledger_transferables(ff)
                cross_props = propose_cross_run(transferish, ledger)
            except Exception as e:
                print(f"\n(cross-run match skipped: {e})")
    print(f"\n{'-'*74}\nCROSS-RUN TRANSFER PROPOSALS (new ↔ existing ledger): {len(cross_props)}")
    for r, lg in cross_props:
        print(f"  ? {r.txn_date}  SAR {abs(r.amount):,.2f}  {r.account} ↔ existing "
              f"{lg['account']}  [{lg['desc'][:34]}]")
    if cross_props and not args.fuse_existing:
        print("  (review; pass --fuse-existing to fuse each into one transfer)")

    # --- blockers ---
    blockers = []
    for m in missing_accounts:
        blockers.append(f"Firefly account missing: '{m}' — create/rename before apply "
                        f"(e.g. rename 'SABB Mastercard •1437' → 'SABB Mastercard •5158')")
    for (path, fmt, acct, *_rest) in per_file:
        if acct == "⚠️ NEEDS ASSIGNMENT":
            blockers.append(f"Assign account for {os.path.relpath(path, ROOT)} "
                            f"({fmt_names.get(fmt)})")
    for acct, ob in account_openings.items():
        if not ob[3]:
            blockers.append(f"Balance mismatch for {acct} — resolve before import")
    if candidates:
        blockers.append(f"{len(candidates)} candidate transfer(s) need confirm/routing "
                        f"(which card each 'Transfer to …' targets)")
    print(f"\n{'-'*74}\nBLOCKERS / NEEDS MOHAMED ({len(blockers)}):")
    for b in blockers:
        print(f"  ⛔ {b}")
    if not blockers:
        print("  (none)")

    # --- APPLY (guarded: refuses while any blocker exists) ---
    applied_msg = "No data written (dry run)."
    if args.apply:
        if blockers:
            print(f"\n⛔ APPLY REFUSED — resolve the {len(blockers)} blocker(s) above first. "
                  f"Nothing written.")
            applied_msg = "APPLY refused (blockers present)."
        else:
            ff = Firefly(env)
            ids = {a["attributes"]["name"]: a["id"]
                   for t in ("asset", "liability") for a in ff.get_all("accounts", type=t)}
            run_id = "run-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            w, s = _apply(con, ff, ids, writable, confirmed, account_openings, run_id)
            _write_review_queue(writable)
            applied_msg = f"APPLY complete: {w} written, {s} skipped (dup). run={run_id}"
            print(f"\n✅ {applied_msg}  Review queue: data/review_queue.md")
            if args.fuse_existing and cross_props:
                fused = _fuse_existing(ff, ids, cross_props, ledger, run_id)
                print(f"✅ Part A: fused {fused} cross-run transfer(s) into single transfers.")
                applied_msg += f" | fused {fused}"

    log(f"{mode}: files={len(files)} writable={len(writable)} confirmed_transfers={len(confirmed)} "
        f"candidates={len(candidates)} overlap={overlap} blockers={len(blockers)} | {applied_msg}")
    print(f"\n{'='*74}\n{mode} complete. {applied_msg}\n{'='*74}\n")


if __name__ == "__main__":
    main()
