#!/usr/bin/env python3
"""BRIEF 02 — build the Firefly III personal-finance structure (v2 spec).

Idempotent: check-before-create on every object (match by name). Structure only —
NO opening balances, NO transactions, NO fake data. Hisham enters true balances
from his bank apps afterwards.

Token: uses FIREFLY_ADMIN_TOKEN if set, else falls back to FIREFLY_PAT.
Run log appended to logs/setup_structure.log.

  python3 scripts/build_structure.py
"""
import os
from datetime import datetime, timezone

from _ff import Firefly, load_env

LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "logs", "setup_structure.log")
_run = []


def logline(msg: str):
    print(msg)
    _run.append(f"{datetime.now(timezone.utc).isoformat()}  {msg}")


def flush_log():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write("\n".join(_run) + "\n")


# ---- data (from HAKIM_Finance_Structure_v2.md) ----------------------------
# (name, currency, role)
ASSET_ACCOUNTS = [
    # cash & safes
    ("Hisham Wallet", "SAR", "defaultAsset"), ("Sarah's wallet", "SAR", "defaultAsset"),
    ("Safe", "SAR", "defaultAsset"), ("Safe Dollar", "USD", "defaultAsset"),
    ("Adam safe", "SAR", "savingAsset"), ("Aser safe", "SAR", "savingAsset"),
    ("Egyptian pound safe", "EGP", "defaultAsset"), ("UAE Dirham", "AED", "defaultAsset"),
    # banks — Saudi
    ("Hisham SNB main", "SAR", "defaultAsset"), ("Hisham SNB saving", "SAR", "savingAsset"),
    ("Sarah SNB main", "SAR", "defaultAsset"), ("Sarah SNB shopping", "SAR", "defaultAsset"),
    ("Sarah SNB saving", "SAR", "savingAsset"), ("SABB main", "SAR", "defaultAsset"),
    ("SABB Hisham shopping", "SAR", "defaultAsset"), ("SABB School", "SAR", "defaultAsset"),
    ("SABB Travel", "SAR", "defaultAsset"),
    # banks — Egypt
    ("Bank Misr USD", "USD", "defaultAsset"), ("Bank Misr EGP", "EGP", "defaultAsset"),
    # digital wallets
    ("STC Pay", "SAR", "defaultAsset"), ("D360", "SAR", "defaultAsset"),
    ("Barq", "SAR", "defaultAsset"),
    # trading cash held at the broker — YOUR money (positions/P&L stay in HISSAR)
    ("Trading cash (HISSAR)", "SAR", "defaultAsset"),
    # receivable (asset)
    ("Owed to me (مستحقات)", "SAR", "defaultAsset"),
]

# credit cards as ccAsset accounts (Firefly v6.6.6 API rejects transfers TO a
# liability, so card payments must transfer into an asset; ccAsset shows spending
# as a negative balance = debt growth). "I owe" stays a real liability.
CARD_ACCOUNTS = [
    "SABB Alfursan •4331", "SABB Mastercard •5158", "SABB Visa •5019",
    "Hisham SNB Alfursan •8381", "Hisham SNB Mastercard •6510",
    "Sarah SNB Mastercard •437x",
]
LIABILITY_ACCOUNTS = ["I owe (عليّ)"]

CATEGORIES = [
    # expense
    "Groceries & supermarket", "Eating out & delivery", "Personal care",
    "Clothing & accessories", "Electronics & gadgets", "Entertainment & outings",
    "Sports & fitness", "Subscriptions & digital", "Utilities & telecom",
    "Home & maintenance", "Household staff", "Car", "Transport & taxis",
    "Medical & pharmacy", "School & education", "Government & documents", "Travel",
    "Gifts & occasions", "Hajj & Umrah (حج وعمرة)", "Zakat & charity (زكاة وصدقة)",
    "Insurance", "Bank & fees", "To review",
    # cross-entity outflow (factory capital leaves your book -> its own books)
    "Capital contribution: Factory",
    # income
    "Business income", "Salary & allowances", "Rental income", "Interest income",
    "Gifts received", "Reimbursements", "Other income",
]

TAGS = [
    "Hisham", "Sarah", "Aser", "Adam", "Family", "Maid", "Driver",
    "online", "luxury", "home-project", "work",
    "allowance:housing", "allowance:tickets",
]

# (name, repeat_freq, first_date)  — placeholder amounts min=max=1, Hisham edits
BILLS_MONTHLY = ["Netflix", "Shahid", "OSN", "Prime Video", "Starzplay", "Apple TV+",
                 "Microsoft", "VPN", "STC Hisham", "STC Sarah", "STC Aser",
                 "Electricity", "Water", "Internet", "Gas", "Maid salary"]
BILLS_YEARLY = ["School installments (Aser)", "School installments (Adam)",
                "Car insurance", "Iqama renewal Maid"]


def main():
    env = load_env()
    admin = (env.get("FIREFLY_ADMIN_TOKEN") or "").strip()
    if admin:
        env["FIREFLY_PAT"] = admin
        logline("Using FIREFLY_ADMIN_TOKEN for setup.")
    else:
        logline("FIREFLY_ADMIN_TOKEN empty — falling back to FIREFLY_PAT "
                "(recommend a dedicated admin token you can revoke after setup).")
    ff = Firefly(env)

    about = ff.get("about")
    logline(f"Connected to Firefly {about['data']['version']} (API {about['data']['api_version']}).")

    # 1) currencies (create AED if the instance doesn't ship it)
    currency_defs = {"AED": {"code": "AED", "name": "UAE Dirham", "symbol": "د.إ",
                             "decimal_places": 2}}
    for code in ["SAR", "EGP", "USD", "AED"]:
        try:
            ff.post(f"currencies/{code}/enable", {})
            logline(f"currency enabled: {code}")
        except Exception as e:
            if "404" in str(e) and code in currency_defs:
                try:
                    ff.post("currencies", {**currency_defs[code], "enabled": True})
                    logline(f"currency created+enabled: {code}")
                except Exception as e2:
                    logline(f"currency create {code} FAILED: {e2}")
            else:
                logline(f"currency enable {code} skipped/failed: {e}")
    try:
        ff._req("PUT", "currencies/SAR", {"default": True, "enabled": True})
        logline("default currency: SAR")
    except Exception as e:
        logline(f"set default SAR failed: {e}")

    # helpers -------------------------------------------------------------
    existing_accounts = {a["attributes"]["name"] for a in ff.get_all("accounts")}

    def make_account(name, body):
        if name in existing_accounts:
            logline(f"account exists, skip: {name}")
            return
        try:
            ff.post("accounts", body)
            existing_accounts.add(name)
            logline(f"account created: {name}")
        except Exception as e:
            logline(f"account FAILED: {name} -> {e}")

    # 2) asset accounts
    for name, cur, role in ASSET_ACCOUNTS:
        make_account(name, {"name": name, "type": "asset", "account_role": role,
                            "currency_code": cur})

    # 3a) credit cards as ccAsset (see CARD_ACCOUNTS note)
    for name in CARD_ACCOUNTS:
        make_account(name, {"name": name, "type": "asset", "account_role": "ccAsset",
                            "currency_code": "SAR", "credit_card_type": "monthlyFull",
                            "monthly_payment_date": "2026-01-01"})

    # 3b) real liabilities (money owed to people)
    for name in LIABILITY_ACCOUNTS:
        make_account(name, {"name": name, "type": "liability", "liability_type": "debt",
                            "liability_direction": "debit", "currency_code": "SAR"})

    # 4) categories
    existing_cats = {c["attributes"]["name"] for c in ff.get_all("categories")}
    for name in CATEGORIES:
        if name in existing_cats:
            logline(f"category exists, skip: {name}")
            continue
        try:
            ff.post("categories", {"name": name})
            logline(f"category created: {name}")
        except Exception as e:
            logline(f"category FAILED: {name} -> {e}")

    # 5) tags
    existing_tags = {t["attributes"]["tag"] for t in ff.get_all("tags")}
    for tag in TAGS:
        if tag in existing_tags:
            logline(f"tag exists, skip: {tag}")
            continue
        try:
            ff.post("tags", {"tag": tag})
            logline(f"tag created: {tag}")
        except Exception as e:
            logline(f"tag FAILED: {tag} -> {e}")

    # 6) bills — skeleton, placeholder amounts (min=max=1)
    existing_bills = {b["attributes"]["name"] for b in ff.get_all("bills")}

    def make_bill(name, freq, date):
        if name in existing_bills:
            logline(f"bill exists, skip: {name}")
            return
        try:
            ff.post("bills", {"name": name, "amount_min": "1", "amount_max": "1",
                              "date": date, "repeat_freq": freq, "skip": 0,
                              "active": True, "currency_code": "SAR"})
            existing_bills.add(name)
            logline(f"bill created: {name} ({freq})")
        except Exception as e:
            logline(f"bill FAILED: {name} -> {e}")

    for name in BILLS_MONTHLY:
        make_bill(name, "monthly", "2026-09-01")
    for name in BILLS_YEARLY:
        make_bill(name, "yearly", "2027-01-01")

    # 6b) prune fake-data residue + stale categories — ONLY on an empty ledger,
    #     so this is safe and idempotent and never touches real data later.
    ntx = ff.get("transactions", limit=1).get("meta", {}).get("pagination", {}).get("total", 0)
    if ntx == 0:
        # remove superseded v1 placeholder accounts
        legacy = {"Personal"}
        for a in ff.get_all("accounts"):
            if a["attributes"]["name"] in legacy:
                try:
                    ff._req("DELETE", f"accounts/{a['id']}")
                    logline(f"removed legacy account: {a['attributes']['name']}")
                except Exception as e:
                    logline(f"remove legacy account failed: {a['attributes']['name']} -> {e}")
        pruned_acc = 0
        for a in ff.get_all("accounts"):
            if a["attributes"]["type"] in ("expense", "revenue"):
                try:
                    ff._req("DELETE", f"accounts/{a['id']}")
                    pruned_acc += 1
                except Exception as e:
                    logline(f"prune account failed: {a['attributes']['name']} -> {e}")
        desired = set(CATEGORIES)
        pruned_cat = 0
        for c in ff.get_all("categories"):
            if c["attributes"]["name"] not in desired:
                try:
                    ff._req("DELETE", f"categories/{c['id']}")
                    pruned_cat += 1
                except Exception as e:
                    logline(f"prune category failed: {c['attributes']['name']} -> {e}")
        logline(f"pruned (ledger empty): {pruned_acc} orphan expense/revenue accounts, "
                f"{pruned_cat} stale categories")
    else:
        logline(f"ledger has {ntx} transactions — skipping prune (safety)")

    # 7) verify
    accts = ff.get_all("accounts")
    by_type: dict[str, int] = {}
    by_cur: dict[str, int] = {}
    for a in accts:
        at = a["attributes"]
        by_type[at["type"]] = by_type.get(at["type"], 0) + 1
        by_cur[at.get("currency_code") or "?"] = by_cur.get(at.get("currency_code") or "?", 0) + 1
    ncat = len(ff.get_all("categories"))
    ntag = len(ff.get_all("tags"))
    nbill = len(ff.get_all("bills"))
    ntx = ff.get("transactions", limit=1).get("meta", {}).get("pagination", {}).get("total", 0)

    logline("---- SUMMARY ----")
    logline(f"accounts by type: {by_type}")
    logline(f"accounts by currency: {by_cur}")
    logline(f"categories: {ncat} | tags: {ntag} | bills: {nbill}")
    logline(f"transactions: {ntx} (must be 0)")


if __name__ == "__main__":
    try:
        main()
    finally:
        flush_log()
