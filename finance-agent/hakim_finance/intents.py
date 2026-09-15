"""Deterministic natural-language understanding for PERSONAL finance questions.

Architecture rule (one system per domain):
  * Firefly is the PERSONAL ledger only. Finance answers about personal money.
  * Questions about MENTCO (Operations/ERPNext), trading (HISSAR), or the factory
    (name TBD) are DEFERRED to the owning agent — Finance does not guess from data
    it doesn't own. Cross-domain aggregation is a later agent's job (Wealth/WAZIR).

Philosophy:
  * Intent + parameters (period, category) parsed with rules first.
  * All money figures are COMPUTED IN PYTHON from Firefly. The model only
    rephrases computed facts.
  * If a question can't be mapped confidently, FLAG and ask — never guess.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from .config import config
from .firefly import FireflyClient
from .rules import categorize as rules_categorize

# --- canonical personal categories (mirror scripts/setup_books.py) ----------
EXPENSE_CATEGORIES = [
    "Groceries & supermarket", "Eating out & delivery", "Personal care",
    "Clothing & accessories", "Electronics & gadgets", "Entertainment & outings",
    "Sports & fitness", "Subscriptions & digital", "Utilities & telecom",
    "Home & maintenance", "Household staff", "Car", "Transport & taxis",
    "Medical & pharmacy", "School & education", "Government & documents", "Travel",
    "Gifts & occasions", "Hajj & Umrah (حج وعمرة)", "Zakat & charity (زكاة وصدقة)",
    "Insurance", "Bank & fees", "Capital contribution: Factory", "To review",
]
INCOME_CATEGORIES = [
    "Business income", "Salary & allowances", "Rental income", "Interest income",
    "Gifts received", "Reimbursements", "Other income",
]

# synonym -> canonical category. Checked longest-first as substrings.
CATEGORY_SYNONYMS: list[tuple[str, str]] = [
    # expense
    ("groceries", "Groceries & supermarket"), ("grocery", "Groceries & supermarket"),
    ("supermarket", "Groceries & supermarket"),
    ("eating out", "Eating out & delivery"), ("dining", "Eating out & delivery"),
    ("restaurant", "Eating out & delivery"), ("delivery", "Eating out & delivery"),
    ("personal care", "Personal care"), ("haircut", "Personal care"),
    ("hairdresser", "Personal care"), ("shisha", "Personal care"),
    ("clothing", "Clothing & accessories"), ("clothes", "Clothing & accessories"),
    ("shoes", "Clothing & accessories"), ("perfume", "Clothing & accessories"),
    ("watch", "Clothing & accessories"),
    ("electronics", "Electronics & gadgets"), ("gadget", "Electronics & gadgets"),
    ("entertainment", "Entertainment & outings"), ("cinema", "Entertainment & outings"),
    ("outing", "Entertainment & outings"), ("toys", "Entertainment & outings"),
    ("sports", "Sports & fitness"), ("gym", "Sports & fitness"), ("fitness", "Sports & fitness"),
    ("subscriptions", "Subscriptions & digital"), ("subscription", "Subscriptions & digital"),
    ("netflix", "Subscriptions & digital"), ("streaming", "Subscriptions & digital"),
    ("utilities", "Utilities & telecom"), ("electricity", "Utilities & telecom"),
    ("internet", "Utilities & telecom"), ("water bill", "Utilities & telecom"),
    ("stc", "Utilities & telecom"), ("telecom", "Utilities & telecom"),
    ("home maintenance", "Home & maintenance"), ("maintenance", "Home & maintenance"),
    ("laundry", "Home & maintenance"), ("home", "Home & maintenance"),
    ("household staff", "Household staff"), ("maid", "Household staff"),
    ("driver", "Household staff"),
    ("fuel", "Car"), ("petrol", "Car"), ("parking", "Car"), ("car", "Car"),
    ("transport", "Transport & taxis"), ("taxi", "Transport & taxis"),
    ("uber", "Transport & taxis"), ("careem", "Transport & taxis"),
    ("medical", "Medical & pharmacy"), ("pharmacy", "Medical & pharmacy"),
    ("healthcare", "Medical & pharmacy"), ("hospital", "Medical & pharmacy"),
    ("clinic", "Medical & pharmacy"), ("doctor", "Medical & pharmacy"),
    ("school", "School & education"), ("education", "School & education"),
    ("tuition", "School & education"), ("canteen", "School & education"),
    ("government", "Government & documents"), ("iqama", "Government & documents"),
    ("passport", "Government & documents"), ("visa", "Government & documents"),
    ("documents", "Government & documents"),
    ("travel", "Travel"), ("flight", "Travel"), ("hotel", "Travel"),
    ("gifts", "Gifts & occasions"), ("gift", "Gifts & occasions"),
    ("birthday", "Gifts & occasions"),
    ("hajj", "Hajj & Umrah (حج وعمرة)"), ("umrah", "Hajj & Umrah (حج وعمرة)"),
    ("zakat", "Zakat & charity (زكاة وصدقة)"), ("charity", "Zakat & charity (زكاة وصدقة)"),
    ("donation", "Zakat & charity (زكاة وصدقة)"), ("sadaqah", "Zakat & charity (زكاة وصدقة)"),
    ("insurance", "Insurance"),
    ("bank fee", "Bank & fees"), ("bank charge", "Bank & fees"), ("vat", "Bank & fees"),
    # factory capital contribution (personal outflow -> expense, not an account)
    ("capital contribution: factory", "Capital contribution: Factory"),
    ("capital contribution", "Capital contribution: Factory"),
    ("factory capital", "Capital contribution: Factory"),
    ("capital to factory", "Capital contribution: Factory"),
    ("capital into factory", "Capital contribution: Factory"),
    ("contribute to factory", "Capital contribution: Factory"),
    ("contribution", "Capital contribution: Factory"),
    ("contribute", "Capital contribution: Factory"),
    ("capital", "Capital contribution: Factory"),
    # income (incl. MENTCO salary/drawings)
    ("business income", "Business income"), ("mentco salary", "Business income"),
    ("mentco drawings", "Business income"), ("drawings", "Business income"),
    ("drew", "Business income"), ("draw", "Business income"),
    ("salary", "Salary & allowances"), ("allowance", "Salary & allowances"),
    ("housing allowance", "Salary & allowances"),
    ("rental income", "Rental income"), ("rent income", "Rental income"),
    ("interest", "Interest income"),
    ("gifts received", "Gifts received"),
    ("reimbursement", "Reimbursements"),
    ("other income", "Other income"),
]


@dataclass
class Result:
    intent: str
    text: str                      # deterministic, safe fallback answer
    facts: dict = field(default_factory=dict)
    allow_llm: bool = True         # False => return `text` verbatim (flags, errors)
    flagged: bool = False


# --------------------------------------------------------------------------
# parameter parsing
# --------------------------------------------------------------------------
def _today() -> date:
    return datetime.now().date()


def parse_period(text: str) -> tuple[str, str, str]:
    """Return (start_iso, end_iso, label). Defaults to the current month."""
    t = text.lower()
    today = _today()

    def iso(d: date) -> str:
        return d.isoformat()

    m = re.search(r"last\s+(\d+)\s+month", t)
    if m:
        n = int(m.group(1))
        start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        for _ in range(n - 1):
            start = (start - timedelta(days=1)).replace(day=1)
        return iso(start), iso(today), f"the last {n} months"
    m = re.search(r"(?:last|past)\s+(\d+)\s+day", t)
    if m:
        n = int(m.group(1))
        return iso(today - timedelta(days=n)), iso(today), f"the last {n} days"
    m = re.search(r"(?:last|past)\s+(\d+)\s+week", t)
    if m:
        n = int(m.group(1))
        return iso(today - timedelta(weeks=n)), iso(today), f"the last {n} weeks"

    if "today" in t:
        return iso(today), iso(today), "today"
    if "yesterday" in t:
        y = today - timedelta(days=1)
        return iso(y), iso(y), "yesterday"
    if "this week" in t:
        start = today - timedelta(days=today.weekday())
        return iso(start), iso(today), "this week"
    if "last week" in t:
        start = today - timedelta(days=today.weekday() + 7)
        end = start + timedelta(days=6)
        return iso(start), iso(end), "last week"
    if "last month" in t:
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        start = last_prev.replace(day=1)
        return iso(start), iso(last_prev), "last month"
    if "this month" in t:
        return iso(today.replace(day=1)), iso(today), "this month"
    if "year to date" in t or "ytd" in t or "this year" in t:
        return iso(today.replace(month=1, day=1)), iso(today), "this year to date"
    if "last year" in t:
        start = today.replace(year=today.year - 1, month=1, day=1)
        end = today.replace(year=today.year - 1, month=12, day=31)
        return iso(start), iso(end), "last year"

    months = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
    months.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})
    for name, idx in months.items():
        if re.search(rf"\b{name}\b", t):
            ym = re.search(rf"{name}\w*\s+(\d{{4}})", t)
            year = int(ym.group(1)) if ym else today.year
            last_day = calendar.monthrange(year, idx)[1]
            return iso(date(year, idx, 1)), iso(date(year, idx, last_day)), f"{calendar.month_name[idx]} {year}"

    return iso(today.replace(day=1)), iso(today), "this month"


def match_category(text: str, prefer_income: bool = False) -> tuple[str | None, str | None]:
    """Return (canonical_category, matched_term) or (None, None)."""
    t = text.lower()
    for term, cat in sorted(CATEGORY_SYNONYMS, key=lambda x: -len(x[0])):
        if re.search(rf"\b{re.escape(term)}\b", t):
            return cat, term
    return None, None


# words that mean a trading question is about PERFORMANCE/positions => HISSAR, defer
_TRADING_PERF = ["doing", "perform", "p&l", "pnl", "position", "return", "profit",
                 "gain", "loss", "portfolio", "scan", "stock", "made", "make", "trade "]


def _trading_cash_question(t: str) -> bool:
    """A trading question about CASH movement/balance (personal), not performance."""
    if "trading" not in t and "hissar" not in t:
        return False
    if any(k in t for k in _TRADING_PERF):
        return False
    return any(k in t for k in ["transfer", "fund", "move", "moved", "deposit",
                                "withdraw", "withdrew", "pull", "cash", "balance",
                                "to trading", "from trading", "into trading"])


def _personal_flow_signal(t: str) -> bool:
    """True when a question that mentions an entity is actually about MOHAMED's
    personal side, so Finance answers it instead of deferring:
      * MENTCO salary/drawings      -> personal income  (Business income)
      * factory capital contribution -> personal expense (Capital contribution: Factory)
      * trading cash transfers/balance -> personal (Trading cash (HISSAR) account)
    Trading PERFORMANCE/positions still defers to HISSAR.
    """
    if any(k in t for k in ["my salary", "salary/drawings", "drawings", "salary from",
                            "draw from", "drew from", "did i draw", "i draw",
                            "mentco salary", "mentco drawings"]):
        return True
    if "factory" in t and any(k in t for k in
                              ["capital", "contribut", "inject", "put into", "fund"]):
        return True
    if _trading_cash_question(t):
        return True
    return False


# --------------------------------------------------------------------------
# money helpers (pure computation)
# --------------------------------------------------------------------------
def _fmt(n: float) -> str:
    return f"{config.CURRENCY} {n:,.2f}"


# --------------------------------------------------------------------------
# main entry
# --------------------------------------------------------------------------
async def answer(question: str, ff: FireflyClient) -> Result:
    q = question.strip()
    ql = q.lower()

    # 1) explicit categorisation request (utility — always allowed)
    if re.search(r"categori[sz]e", ql) or ql.startswith("what category"):
        return _handle_categorize(q)

    # 2) domain deferral — not Finance's data to answer from
    deferral = _maybe_defer(ql)
    if deferral:
        return deferral

    # 2b) trading cash transfers (personal side of the HISSAR boundary)
    if _trading_cash_question(ql) and any(k in ql for k in
            ["transfer", "fund", "move", "moved", "deposit", "withdraw", "withdrew",
             "pull", "to trading", "from trading", "into trading"]):
        return await _handle_trading_transfer(q, ff)

    # 3) cash position / balance
    if any(k in ql for k in ["cash position", "how much do i have", "how much money do i have",
                             "net worth", "balance", "balances"]):
        return await _handle_cash_position(q, ff)

    # 4) breakdown / where money went
    if any(k in ql for k in ["breakdown", "where did my money", "where is my money",
                             "top expenses", "biggest expenses", "top spending",
                             "what did i spend on", "spending summary", "spending breakdown"]):
        return await _handle_breakdown(q, ff)

    # 5) income (incl. MENTCO salary/drawings — personal income)
    if any(k in ql for k in ["income", "how much did i earn", "how much did i receive",
                             "how much came in", "money in", "received", "drawings",
                             "draw from", "drew from", "did i draw", "i draw"]):
        return await _handle_income(q, ff)

    # 6) spending (incl. factory capital contribution — a personal outflow/expense)
    if any(k in ql for k in ["spend", "spent", "cost", "how much did i pay", "paid",
                             "expenses on", "how much on", "money out",
                             "capital", "contribut", "contribution", "inject"]):
        return await _handle_spending(q, ff)

    # 7) recent transactions
    if any(k in ql for k in ["recent transaction", "last transaction", "show transaction",
                             "list transaction", "latest transaction", "recent activity"]):
        return await _handle_recent(q, ff)

    # 8) not understood -> flag, offer what we CAN do (never guess)
    return Result(
        intent="clarify",
        allow_llm=False,
        flagged=True,
        text=(
            "I'm not sure what you're asking, so I'd rather check than guess. "
            "I cover your **personal** finances. I can answer things like:\n"
            "• \"What's my cash position?\"\n"
            "• \"How much did I spend on groceries last month?\"\n"
            "• \"Give me a spending breakdown for this month.\"\n"
            "• \"How much did I draw from MENTCO this year?\"\n"
            "• \"Categorise: Nahdi pharmacy 220\"\n"
            "Could you rephrase along those lines?"
        ),
    )


def _maybe_defer(ql: str) -> Result | None:
    """If the question is about another domain's own affairs, defer to its agent."""
    if _personal_flow_signal(ql):
        return None  # personal side of a cross-entity flow — Finance answers this
    for token, owner in config.OTHER_DOMAINS.items():
        if re.search(rf"\b{re.escape(token)}\b", ql):
            return Result(
                intent="defer",
                allow_llm=False,
                text=(
                    f"That's **{owner}**'s domain, not Finance. I only cover your "
                    f"personal money (Firefly). It owns its own data, and a "
                    f"cross-domain view (\"everything, everywhere\") is the Wealth "
                    f"agent's job later. I can, though, tell you about the personal "
                    f"side — e.g. what you drew from MENTCO, capital you put into "
                    f"the factory, or transfers to/from your trading account."
                ),
            )
    return None


# --------------------------------------------------------------------------
# handlers (personal ledger only)
# --------------------------------------------------------------------------
async def _handle_cash_position(q: str, ff: FireflyClient) -> Result:
    """Sum all liquid asset accounts (wallets/banks/safes), grouped by currency.
    Receivables ('Owed to me') are excluded — that's money owed, not cash in hand.
    """
    accounts = await ff.asset_accounts()
    liquid = [a for a in accounts
              if a.get("role") != "ccAsset"            # credit cards aren't liquid cash
              and not any(m in (a.get("name") or "").lower()
                          for m in config.RECEIVABLE_MARKERS)]
    by_cur: dict[str, float] = {}
    for a in liquid:
        cur = a.get("currency") or config.CURRENCY
        by_cur[cur] = by_cur.get(cur, 0.0) + a["balance"]

    parts = [f"{cur} {amt:,.2f}" for cur, amt in sorted(by_cur.items())]
    if len(parts) <= 1:
        text = (f"Your cash position is {parts[0] if parts else _fmt(0)} "
                f"across {len(liquid)} accounts.")
    else:
        text = (f"Your cash position across {len(liquid)} accounts:\n"
                + "\n".join(f"• {p}" for p in parts))
    facts = {"accounts": len(liquid),
             "by_currency": {c: round(v, 2) for c, v in by_cur.items()}}
    # deterministic: never let the model collapse/round the multi-currency figures
    return Result("cash_position", text, facts, allow_llm=False)


async def _handle_spending(q: str, ff: FireflyClient) -> Result:
    start, end, plabel = parse_period(q)
    cat, term = match_category(q)

    if not cat and re.search(r"\bon\b", q.lower()):
        return Result(
            "spending", flagged=True, allow_llm=False,
            text=("I couldn't confidently match that to a known spending category, "
                  "so I won't guess. Known categories include: "
                  + ", ".join(EXPENSE_CATEGORIES) + ". Which one did you mean?"),
        )

    rows = await ff.transactions("withdrawal", start, end)
    if cat:
        rows = [r for r in rows if (r.get("category") or "").lower() == cat.lower()]

    total = sum(abs(r["amount"]) for r in rows)
    catlabel = f" on {cat}" if cat else ""
    text = (f"You spent {_fmt(total)}{catlabel} during {plabel} "
            f"({len(rows)} transaction{'s' if len(rows) != 1 else ''}).")
    facts = {"category": cat or "all categories", "period": plabel,
             "total": round(total, 2), "count": len(rows), "currency": config.CURRENCY}
    return Result("spending", text, facts)


async def _handle_income(q: str, ff: FireflyClient) -> Result:
    start, end, plabel = parse_period(q)
    cat, term = match_category(q, prefer_income=True)

    rows = await ff.transactions("deposit", start, end)
    income_cats = {c.lower() for c in INCOME_CATEGORIES}
    if cat and cat.lower() in income_cats:
        rows = [r for r in rows if (r.get("category") or "").lower() == cat.lower()]

    total = sum(abs(r["amount"]) for r in rows)
    catlabel = f" from {cat}" if cat and cat.lower() in income_cats else ""
    text = (f"You received {_fmt(total)}{catlabel} during {plabel} "
            f"({len(rows)} transaction{'s' if len(rows) != 1 else ''}).")
    facts = {"category": cat or "all income", "period": plabel,
             "total": round(total, 2), "count": len(rows), "currency": config.CURRENCY}
    return Result("income", text, facts)


async def _handle_breakdown(q: str, ff: FireflyClient) -> Result:
    start, end, plabel = parse_period(q)
    rows = await ff.transactions("withdrawal", start, end)

    by_cat: dict[str, float] = {}
    for r in rows:
        c = r.get("category") or "Uncategorised"
        by_cat[c] = by_cat.get(c, 0.0) + abs(r["amount"])
    ranked = sorted(by_cat.items(), key=lambda kv: kv[1], reverse=True)[:10]
    total = sum(by_cat.values())

    if not ranked:
        text = f"No personal spending recorded during {plabel}."
    else:
        lines = "\n".join(f"• {c}: {_fmt(v)}" for c, v in ranked)
        text = f"Your spending breakdown during {plabel}:\n{lines}\nTotal: {_fmt(total)}"
    facts = {"period": plabel, "by_category": {c: round(v, 2) for c, v in ranked},
             "total": round(total, 2), "currency": config.CURRENCY}
    return Result("breakdown", text, facts)


async def _handle_recent(q: str, ff: FireflyClient) -> Result:
    start, end, _ = parse_period("last 3 months")
    m = re.search(r"(\d+)", q)
    n = min(int(m.group(1)), 25) if m else 10

    txns = await ff.transactions("all", start, end)
    txns.sort(key=lambda t: t.get("date", ""), reverse=True)
    top = txns[:n]

    lines = []
    for t in top:
        sign = "-" if t["type"] == "withdrawal" else "+"
        lines.append(f"• {t['date']}  {sign}{_fmt(abs(t['amount']))}  {t.get('description','')} "
                     f"[{t.get('category') or 'uncategorised'}]")
    text = ("Your most recent transactions:\n" + "\n".join(lines)) if lines else \
        "No recent transactions found."
    facts = {"count": len(top), "transactions": top}
    return Result("recent", text, facts, allow_llm=False)


async def _handle_trading_transfer(q: str, ff: FireflyClient) -> Result:
    """Personal cash moved to/from the broker (Trading cash (HISSAR) account).
    These are Firefly TRANSFERS; positions/P&L never enter Firefly (HISSAR's).
    """
    start, end, plabel = parse_period(q)
    acct = config.TRADING_CASH_ACCOUNT
    rows = await ff.transactions("transfer", start, end)
    into = sum(abs(r["amount"]) for r in rows if r.get("destination") == acct)
    out = sum(abs(r["amount"]) for r in rows if r.get("source") == acct)

    t = q.lower()
    if any(k in t for k in ["from trading", "withdraw", "withdrew", "pull"]):
        text = f"You moved {_fmt(out)} out of your trading account during {plabel}."
        facts = {"direction": "out", "total": round(out, 2), "period": plabel}
    elif any(k in t for k in ["to trading", "into trading", "fund", "deposit"]):
        text = f"You moved {_fmt(into)} into your trading account during {plabel}."
        facts = {"direction": "in", "total": round(into, 2), "period": plabel}
    else:
        net = into - out
        text = (f"Trading account cash flows during {plabel}: in {_fmt(into)}, "
                f"out {_fmt(out)}, net {_fmt(net)}.")
        facts = {"in": round(into, 2), "out": round(out, 2), "net": round(net, 2),
                 "period": plabel}
    return Result("trading_transfer", text, facts)


def _handle_categorize(q: str) -> Result:
    m = re.search(r"categori[sz]e[:\s]+(.*)", q, re.IGNORECASE)
    payload = (m.group(1) if m else q).strip().strip('"').strip("'")
    amt = None
    am = re.search(r"(\d+(?:\.\d+)?)", payload)
    if am:
        amt = float(am.group(1))
    result = rules_categorize(payload, amt)

    if result.flagged:
        cands = ", ".join(result.candidates) if result.candidates else "none"
        text = (f"⚠️ I can't confidently categorise \"{payload}\" "
                f"(best confidence {result.confidence:.0%}). I'm flagging it for your review "
                f"rather than guessing. Closest candidates: {cands}.")
        return Result("categorize", text, result.as_dict(), allow_llm=False, flagged=True)

    text = (f"\"{payload}\" → {result.category} "
            f"(confidence {result.confidence:.0%}, matched on \"{result.matched_on}\").")
    return Result("categorize", text, result.as_dict(), allow_llm=False)
