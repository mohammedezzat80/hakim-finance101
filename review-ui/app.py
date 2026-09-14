"""HAKIM Entry & Review Desk v2 (Brief 03c).

The permanent truth-desk on :8001 — data entry + review + confirmation ONLY.
NO charts, NO analysis, NO advice (that's the future intelligence layer).

Colour language everywhere: GREEN = money in, RED = money out, BLUE = transfer.
Trust dots: ⚪ imported · 🟡 proposed · 🟢 verified by Hisham.
"""
from __future__ import annotations

import calendar as _calendar
import html
import json
import os
import re
import threading
from datetime import datetime, timedelta, timezone

import httpx
import yaml
from fastapi import FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

FIREFLY_URL = os.environ.get("FIREFLY_URL", "http://firefly:8080").rstrip("/")
TOKEN = (os.environ.get("FIREFLY_ADMIN_TOKEN") or os.environ.get("FIREFLY_PAT") or "").strip()
AGENT_URL = os.environ.get("AGENT_URL", "http://finance-agent:8000").rstrip("/")
AGENT_KEY = os.environ.get("AGENT_API_KEY", "").strip()
DATA = os.environ.get("DATA_DIR", "/app/data")
MERCHANTS_PATH = os.path.join(DATA, "merchants.yaml")
TREE_PATH = os.path.join(DATA, "category_tree.yaml")
RECENTS_PATH = os.path.join(DATA, "recent_cats.json")
FX_PATH = os.path.join(DATA, "fx_rates.yaml")
LOG_PATH = os.environ.get("REVIEW_LOG", "/app/logs/review.log")
REVIEW_CATEGORY = "To review"
OWED = "Owed to me (مستحقات)"

PERSON_TAGS = ["Hisham", "Sarah", "Aser", "Adam", "Family", "Maid", "Driver"]
CONTEXT_TAGS = ["online", "luxury", "work", "home-project"]
TRANSFERISH = re.compile(r"تحويل|transfer|ac to ac|\bips\b|ipsp|sadad|card:", re.I)
ATM_RE = re.compile(r"\batm\b|cash withdraw|سحب نقد|نقدي", re.I)
CARD16 = re.compile(r"\d{16}")
MASKED4 = re.compile(r"[*xX•·]{2,}\s*(\d{4})|\d{4,}\*+(\d{4})")

_lock = threading.RLock()   # reentrant: a thread may re-enter (e.g. audit() inside a locked write) without self-deadlock
app = FastAPI(title="HAKIM Entry & Review Desk")


def _humanize_ff_error(exc):
    """Turn a raw Firefly API error into words the owner can act on (no-raw-errors rule)."""
    try:
        body = exc.response.json()
    except Exception:
        body = {}
    msg = (body.get("message") or "") if isinstance(body, dict) else ""
    errs = body.get("errors") if isinstance(body, dict) else None
    blob = (msg + " " + json.dumps(errs, ensure_ascii=False)).lower() if errs else msg.lower()
    if "valid destination account" in blob or "valid source account" in blob:
        return ("Firefly won’t accept this shape — you can’t move money straight into (or out of) a "
                "debt account with a plain transfer. To reduce a BNPL/loan balance, use the plan’s "
                "“Record payment”, or “Link an existing charge” on the account, which use the correct "
                "paydown shape.")
    if "duplicate" in blob:
        return "Firefly thinks this is a duplicate of an existing transaction — it wasn’t saved again."
    if errs and isinstance(errs, dict):
        first = next(iter(errs.values()), None)
        if isinstance(first, list) and first:
            return f"Firefly couldn’t accept this: {first[0]}"
    if msg:
        return f"Firefly couldn’t accept this: {msg}"
    return "Firefly couldn’t process that request."


@app.exception_handler(httpx.HTTPStatusError)
async def _ff_http_error(request: Request, exc: httpx.HTTPStatusError):
    """Firefly returned a 4xx/5xx that no endpoint caught — surface it in HUMAN words, never the raw
    '422 Unprocessable' that once reached the owner."""
    human = _humanize_ff_error(exc)
    try:
        audit("ff_error", path=str(request.url.path), status=exc.response.status_code,
              human=human)
    except Exception:
        pass
    return JSONResponse(status_code=200, content={"ok": False, "error": human,
                        "firefly_status": exc.response.status_code})


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    """Never swallow a failure: log the traceback + audit it, return clean JSON so the
    frontend can show an error state instead of hanging."""
    import traceback
    traceback.print_exc()
    try:
        audit("error", path=str(request.url.path), error=repr(exc))
    except Exception:
        pass
    return JSONResponse(status_code=500, content={"ok": False, "error": str(exc)})


# ---------------------------------------------------------------- Firefly IO
def ff(method, path, body=None, raw=None, ctype=None):
    url = f"{FIREFLY_URL}/api/v1/{path.lstrip('/')}"
    headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}
    if ctype:
        headers["Content-Type"] = ctype
    with httpx.Client(timeout=60.0) as c:
        if raw is not None:
            r = c.request(method, url, content=raw, headers=headers)
        else:
            headers["Content-Type"] = "application/json"
            r = c.request(method, url, json=body, headers=headers)
        r.raise_for_status()
        # Any WRITE we make moves the data-version fingerprint so open tabs (Calendar, Dashboard)
        # reload — even an EDIT to an OLD transaction, which the newest-transaction fingerprint alone
        # can't see (the osama-marble date-edit that "didn't stick": the write succeeded, but the
        # Calendar tab never re-fetched because its version signal never changed).
        if method.upper() in ("POST", "PUT", "DELETE"):
            _bump_data_epoch()
        return r.json() if r.content else {}


def _bump_data_epoch():
    global _DATA_EPOCH
    _DATA_EPOCH += 1
    _DATA_CACHE["t"] = 0.0        # force a fresh fingerprint on the next poll


def ff_all(path, **params):
    out, page = [], 1
    while True:
        params["page"], params["limit"] = page, 100
        d = ff("GET", path + "?" + "&".join(f"{k}={v}" for k, v in params.items()))
        out.extend(d.get("data", []))
        pg = d.get("meta", {}).get("pagination", {})
        if page >= pg.get("total_pages", 1):
            break
        page += 1
    return out


def audit(event, **fields):
    rec = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with _lock, open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    except Exception as e:
        print("audit fail", e, flush=True)


# ---------------------------------------------------------------- undo store
# Append-only ring of the last N *undoable* writes, each with enough state to
# reverse it. Never silent: every undo is itself audited.
UNDO_PATH = os.path.join(DATA, "undo.json")
_undo = []


def _load_undo():
    global _undo
    try:
        _undo = json.load(open(UNDO_PATH, encoding="utf-8"))
    except Exception:
        _undo = []


def _save_undo():
    try:
        json.dump(_undo, open(UNDO_PATH, "w", encoding="utf-8"),
                  ensure_ascii=False, default=str)
    except Exception as e:
        print("undo save fail", e, flush=True)


def record_undo(kind, label, restore=None, delete_ids=None, recreate=None):
    """kind: 'edit' (restore fields) | 'create' (delete new) | 'convert' (delete new + recreate old)."""
    with _lock:
        eid = "u" + datetime.now(timezone.utc).strftime("%y%m%d%H%M%S%f")
        _undo.append({"id": eid, "ts": datetime.now(timezone.utc).isoformat(),
                      "kind": kind, "label": label, "undone": False,
                      "restore": restore or [], "delete_ids": delete_ids or [],
                      "recreate": recreate})
        del _undo[:-60]
        _save_undo()
    return eid


_load_undo()


@app.get("/api/recent")
def recent():
    return {"items": list(reversed(_undo))[:30]}


@app.post("/api/undo")
async def undo(req: Request):
    p = await req.json()
    e = next((x for x in _undo if x["id"] == p.get("id")), None)
    if not e:
        return {"ok": False, "error": "not found"}
    if e.get("undone"):
        return {"ok": False, "error": "already undone"}
    try:
        if e["kind"] == "edit":
            for r in e["restore"]:
                ff("PUT", f"transactions/{r['id']}",
                   {"transactions": [{"transaction_journal_id": r["jid"], **r["fields"]}]})
        elif e["kind"] == "create":
            for gid in e["delete_ids"]:
                ff("DELETE", f"transactions/{gid}")
        elif e["kind"] == "convert":
            if e.get("recreate"):
                ff("POST", "transactions",
                   {"error_if_duplicate_hash": False, "transactions": [e["recreate"]]})
            for gid in e["delete_ids"]:
                ff("DELETE", f"transactions/{gid}")
    except Exception as ex:
        return {"ok": False, "error": str(ex)}
    with _lock:
        e["undone"] = True
        _save_undo()
    audit("undo", undo_id=e["id"], kind=e["kind"], label=e["label"])
    return {"ok": True, "label": e["label"]}


@app.get("/api/counterparties")
def counterparties():
    """The 'who' book — people you tag and merchants you pay. Counts + net, no charts."""
    txns = all_txns()
    people = {p: {"name": p, "in": 0.0, "out": 0.0, "count": 0} for p in PERSON_TAGS}
    for t in txns:
        for tg in (t.get("tags") or []):
            if tg in people:
                d = people[tg]
                if t["type"] == "deposit":
                    d["in"] += t["amount"]
                elif t["type"] == "withdrawal":
                    d["out"] += t["amount"]
                d["count"] += 1
    ppl = []
    for v in people.values():
        if v["count"]:
            ppl.append({"name": v["name"], "count": v["count"],
                        "in": round(v["in"], 2), "out": round(v["out"], 2),
                        "net": round(v["in"] - v["out"], 2)})
    ppl.sort(key=lambda x: -x["count"])
    merch = {}
    for t in txns:
        if t["type"] != "withdrawal":
            continue
        k = merchant_key(t["desc"])
        d = t["desc"]
        name = (d.split(" — ", 1)[1] if " — " in d else d)[:34]
        m = merch.setdefault(k, {"key": k, "name": name, "total": 0.0, "count": 0})
        m["total"] += t["amount"]
        m["count"] += 1
    top = sorted(merch.values(), key=lambda x: -x["count"])[:30]
    for m in top:
        m["total"] = round(m["total"], 2)
    # transfer counterparties — names extracted from IPS/transfer descriptions
    names = {}
    for t in txns:
        cp = extract_counterparty(t.get("desc") or "")
        if not cp:
            continue
        d = names.setdefault(cp, {"name": cp, "in": 0.0, "out": 0.0, "count": 0})
        if t["type"] == "deposit":
            d["in"] += t["amount"]
        elif t["type"] == "withdrawal":
            d["out"] += t["amount"]
        d["count"] += 1
    people_ext = [{"name": v["name"], "count": v["count"], "in": round(v["in"], 2),
                   "out": round(v["out"], 2), "net": round(v["in"] - v["out"], 2)}
                  for v in names.values()]
    people_ext.sort(key=lambda x: -x["count"])
    return {"people": ppl, "merchants": top, "names": people_ext}


_VCACHE = {}


def _config_sig():
    """Combined mtime of every YAML config store in DATA (targets · envelopes · tree · meta · merchants ·
    card registry/networks · schedules · funds …). Folded into _vcache so a config write invalidates
    cached views IMMEDIATELY. The stale-config class — a YAML write that didn't bump the ledger
    data-version, so the vcache served the old value (card registry once, budget targets again) — is now
    dead for ALL stores at once. YAML only: volatile JSON (hawl_trail, undo) must not thrash the cache."""
    try:
        s = 0.0
        for fn in os.listdir(DATA):
            if fn.endswith((".yaml", ".yml")):
                try:
                    s += os.path.getmtime(os.path.join(DATA, fn))
                except OSError:
                    pass
        return round(s, 3)
    except OSError:
        return 0.0


def _vcache(name, key, compute):
    """Compute-once-per-(data-version × config-version) cache for heavy READ endpoints (the permanent
    speed layer): each view's aggregation runs at most once per version, then every load is served from
    memory — flat at any ledger size (a 10k-txn dashboard rollup would be ~5s recomputed, ~0ms cached).
    The fingerprint invalidates on every ledger write (_DATA_EPOCH / external total·newest·updated_at)
    AND every YAML-config write (_config_sig), so cached views are never stale. Bounded; versions pruned."""
    ver = str(_data_version()) + "|" + str(_config_sig())
    ck = (name, key)
    ent = _VCACHE.get(ck)
    if ent is not None and ent[0] == ver:
        return ent[1]
    if len(_VCACHE) > 200:                     # safety bound
        _VCACHE.clear()
    val = compute()
    _VCACHE[ck] = (ver, val)
    return val


@app.get("/api/dash")
def dash(month: str = ""):
    return _vcache("dash", month, lambda: _dash_impl(month))


def _dash_impl(month: str = ""):
    """Wave-1 Dashboard analytics — READ-ONLY. Cash/net-worth from live account balances,
    plus a chosen month's flows by category / person / merchant / day-of-week."""
    import datetime as _dt
    txns = all_txns()
    fx = fx_rates() or {}
    def sar(amt, cur):
        return float(amt) * (1 if cur == "SAR" else (fx.get(cur) or 1))
    months = sorted({(t["date"] or "")[:7] for t in txns if t.get("date")})
    if month not in months:
        month = months[-1] if months else ""
    m = [t for t in txns if (t["date"] or "")[:7] == month]
    inflow = round(sum(t["amount"] for t in m if t["type"] == "deposit"), 2)
    outflow = round(sum(t["amount"] for t in m if t["type"] == "withdrawal"), 2)
    # monthly cash-flow series (all months with data) + prior-month net for the tile delta
    flow = []
    for mo in months:
        mt = [t for t in txns if (t["date"] or "")[:7] == mo]
        fi = round(sum(t["amount"] for t in mt if t["type"] == "deposit"), 2)
        fo = round(sum(t["amount"] for t in mt if t["type"] == "withdrawal"), 2)
        flow.append({"month": mo, "in": fi, "out": fo, "net": round(fi - fo, 2)})
    prev_net = None
    if month in months:
        i = months.index(month)
        if i > 0:
            prev_net = flow[i - 1]["net"]
    catmap = {}
    for t in m:
        if t["type"] != "withdrawal":
            continue
        main = (t["category"] or "Uncategorized").split(":")[0].strip() or "Uncategorized"
        catmap[main] = catmap.get(main, 0) + t["amount"]
    cats = sorted(({"name": k, "amount": round(v, 2)} for k, v in catmap.items()),
                  key=lambda x: -x["amount"])
    pmap = {p: 0.0 for p in PERSON_TAGS}
    for t in m:
        for tag in (t.get("tags") or []):
            if tag in pmap:
                pmap[tag] += (t["amount"] if t["type"] == "deposit"
                              else -t["amount"] if t["type"] == "withdrawal" else 0)
    people = sorted(({"name": k, "net": round(v, 2)} for k, v in pmap.items() if v),
                    key=lambda x: x["net"])
    mm = {}
    for t in m:
        if t["type"] != "withdrawal":
            continue
        d = t["desc"]
        e = mm.setdefault(merchant_key(d), {"key": merchant_key(d), "name": merchant_display(d),
                                            "total": 0.0, "count": 0})
        e["total"] += t["amount"]
        e["count"] += 1
    merch = sorted(mm.values(), key=lambda x: -x["total"])[:8]
    for x in merch:
        x["total"] = round(x["total"], 2)
    dow = [0.0] * 7
    for t in m:
        if t["type"] != "withdrawal":
            continue
        try:
            dow[_dt.date.fromisoformat(t["date"]).weekday()] += t["amount"]
        except Exception:
            pass
    dow = [round(x, 2) for x in dow]
    # money position — THE canonical net worth / debt (one owner: _networth). Never re-derive it here.
    _nwp = _networth()
    nw, cash, cards = _nwp["net"], _nwp["cash"], -_nwp["cards_debt"]
    per_cur = {}
    for a in ff_all("accounts"):                 # per-currency spendable breakdown only (not the total)
        at = a["attributes"]
        if at.get("type") != "asset":
            continue
        role = at.get("account_role")
        if role != "ccAsset" and "receivable" not in (at.get("name") or "").lower() and at.get("active", True):
            per_cur[at.get("currency_code") or "SAR"] = per_cur.get(at.get("currency_code") or "SAR", 0) + float(at.get("current_balance") or 0)
    days_in = 30
    try:
        y, mm = int(month[:4]), int(month[5:7])
        today = _dt.date.today()
        days_in = today.day if (y, mm) == (today.year, today.month) else __import__("calendar").monthrange(y, mm)[1]
    except Exception:
        pass
    # net worth over time (weekly points) — computed honestly from the ledger flows
    signed = sorted(((t["date"], (t["amount"] if t["type"] == "deposit"
                     else -t["amount"] if t["type"] == "withdrawal" else 0.0))
                    for t in txns if t.get("date")), key=lambda x: x[0])
    nw_series, nw_month_delta, start = [], 0.0, (signed[0][0] if signed else None)
    if start:
        def nw_at(dstr):
            return round(nw - sum(x for dd, x in signed if dd[:10] > dstr), 2)
        d0, today = _dt.date.fromisoformat(start[:10]), _dt.date.today()
        d = d0
        while d < today:
            nw_series.append({"date": d.isoformat(), "value": nw_at(d.isoformat())})
            d += _dt.timedelta(days=7)
        nw_series.append({"date": today.isoformat(), "value": round(nw, 2)})
        nw_month_delta = round(nw - nw_at((month + "-01") if month else today.isoformat()), 2)
    # upcoming bills — shared projection with the Recurring page (computed next-due,
    # honest amounts: None when the bill's amount is still a placeholder)
    upcoming = []
    try:
        for b in bills_view(today)[:5]:
            if b["next_due"]:
                upcoming.append({"name": b["name"], "date": b["next_due"],
                                 "amount": b["amount"], "days": b["days"]})
    except Exception:
        pass
    # data completeness — exact truth, not vague "provisional"
    review_left = sum(1 for t in txns if t["category"] == REVIEW_CATEGORY)
    weeks = round((_dt.date.today() - _dt.date.fromisoformat(start[:10])).days / 7) if start else 0
    squares = [
        {"k": "Sarah's 3 statements imported", "done": False},
        {"k": "Review queue cleared", "done": review_left == 0, "note": f"{review_left} left"},
        {"k": "Cash & safes counted", "done": False},
        {"k": "Wallets reconciled (not monitoring-only)", "done": False},
        {"k": "3–4 normal weeks observed", "done": weeks >= 4, "note": f"{weeks} wk"},
    ]
    comp_done = sum(1 for s in squares if s["done"])
    completeness = {"pct": round(comp_done / len(squares) * 100), "done": comp_done,
                    "total": len(squares), "squares": squares}
    # recent activity (last 5 ledger entries, read-only)
    recent = sorted(txns, key=lambda t: (t.get("created") or t.get("date") or ""), reverse=True)[:5]
    recent = [{"id": t["id"], "name": merchant_display(t["desc"]), "signed": t["signed"],
               "date": t["date"], "account": t["account"], "cat": t["category"]} for t in recent]
    # --- The month's shape (Dashboard charter #2): COMPLETED-PERIOD comparison, never a pace judgment.
    #     in/out/net for this month, with last month + the 3-month typical shown inline, plus the
    #     fixed-vs-flexible split (ONE definition — the category `flex` meta, same as Categories). ---
    this_i = months.index(month) if month in months else -1
    def _sh(f):
        return {"in": f["in"], "out": f["out"], "net": f["net"]}
    last_shape = _sh(flow[this_i - 1]) if this_i >= 1 else None
    prior = flow[max(0, this_i - 3):this_i] if this_i >= 1 else []   # up to 3 COMPLETED months before
    typical = None
    if prior:
        n = len(prior)
        typical = {"in": round(sum(f["in"] for f in prior) / n, 2),
                   "out": round(sum(f["out"] for f in prior) / n, 2),
                   "net": round(sum(f["net"] for f in prior) / n, 2), "n": n}
    cmeta = _cat_meta()
    fx_fixed = fx_flex = fx_untag = 0.0
    for t in m:
        if t["type"] != "withdrawal":
            continue
        main = (t["category"] or "").split(":")[0].strip()
        fl = (cmeta.get(main) or {}).get("flex") or ""
        if fl == "fixed":
            fx_fixed += t["amount"]
        elif fl == "flexible":
            fx_flex += t["amount"]
        else:
            fx_untag += t["amount"]
    shape = {"this": _sh(flow[this_i]) if this_i >= 0 else
             {"in": inflow, "out": outflow, "net": round(inflow - outflow, 2)},
             "last": last_shape, "typical": typical,
             "fixed": round(fx_fixed, 2), "flexible": round(fx_flex, 2), "untagged": round(fx_untag, 2)}
    # --- Household split (Dashboard charter #3): uniquely available since Sarah's import.
    #     Attribution: explicit person tag first (Hisham/Sarah → that person; Family → joint); else the
    #     account's owner IF the account name is unambiguously personal; else honestly "unassigned"
    #     (flag-don't-guess — a joint/ambiguous account is never forced onto a person). ---
    def _own(name):
        nm = (name or "").lower()
        if "hisham" in nm or "هشام" in nm:
            return "Hisham"
        if "sarah" in nm or "سار" in nm:
            return "Sarah"
        return None
    def _who(t):
        tags = t.get("tags") or []
        if "Hisham" in tags:
            return "Hisham"
        if "Sarah" in tags:
            return "Sarah"
        if "Family" in tags:
            return "joint"
        return _own(t.get("account")) or "unassigned"
    hh = {k: {"spend": 0.0, "net": 0.0} for k in ("Hisham", "Sarah", "joint", "unassigned")}
    for t in m:
        who = _who(t)
        if t["type"] == "withdrawal":
            hh[who]["spend"] += t["amount"]
            hh[who]["net"] -= t["amount"]
        elif t["type"] == "deposit":
            hh[who]["net"] += t["amount"]
    household = {k: {"spend": round(v["spend"], 2), "net": round(v["net"], 2)} for k, v in hh.items()}
    return {"month": month, "months": months, "inflow": inflow, "outflow": outflow,
            "net": round(inflow - outflow, 2), "count": len(m), "days_in": days_in,
            "cash": round(cash, 2), "cards_debt": round(-cards, 2), "net_worth": round(nw, 2),
            "debt": _nwp["debt"], "assets": _nwp["assets"], "other_debt": _nwp["other_debt"],
            "cats": cats, "people": people, "merchants": merch, "dow": dow,
            "per_cur": {k: round(v, 2) for k, v in per_cur.items()},
            "nw_series": nw_series, "nw_month_delta": nw_month_delta,
            "upcoming": upcoming, "completeness": completeness, "recent": recent,
            "flow": flow, "prev_net": prev_net, "shape": shape, "household": household}


_PAGES = [("Dashboard", "/dashboard", "◈"), ("Desk", "/", "▤"), ("Calendar", "/calendar", "▦"),
          ("Categories", "/categories", "🏷️"), ("Recurring", "/recurring", "🔁"),
          ("Spending heatmap", "/heatmap", "🔥")]


@app.get("/api/search")
def search(q: str = ""):
    """Global ⌘K search: pages, accounts, categories, and transactions (by merchant/
    description/amount). Read-only; each result carries the surface it routes to."""
    ql = _norm(q.strip())
    out = []
    if not ql:
        return {"results": []}
    for name, url, ic in _PAGES:
        if ql in _norm(name):
            out.append({"type": "page", "icon": ic, "label": name, "sub": "page", "target": url})
    for a in accounts():
        if ql in _norm(a["name"]):
            out.append({"type": "account", "icon": "🏦", "label": a["name"],
                        "sub": f"account · SAR {a['balance']:,.0f}", "target": "/account?account=" + a["name"]})
    cats = sorted({t["category"].split(":")[0].strip() for t in all_txns() if t.get("category")})
    for c in cats:
        if c and ql in _norm(c):
            out.append({"type": "category", "icon": "🏷️", "label": c,
                        "sub": "category", "target": "/?category=" + c})
    # transactions — amount match if numeric, else text match on merchant/desc
    num = None
    try:
        num = float(q.replace(",", "").strip())
    except Exception:
        num = None
    tmatch = []
    for t in all_txns():
        disp = t.get("counterparty") or merchant_display(t.get("desc") or "")
        if num is not None and abs(t["amount"] - num) < 0.01:
            tmatch.append((t, disp))
        elif num is None and ql in _norm((t.get("desc") or "") + " " + disp):
            tmatch.append((t, disp))
    tmatch.sort(key=lambda x: x[0].get("date") or "", reverse=True)
    for t, disp in tmatch[:8]:
        sign = "+" if t["signed"] >= 0 else "−"
        out.append({"type": "txn", "icon": "💳", "label": disp or "(no description)",
                    "sub": f"{t['date']} · {sign}SAR {abs(t['signed']):,.0f}", "target": "/?txn=" + t["id"]})
    return {"results": out[:20]}


def _card_networks():
    """Verified card networks (data/card_networks.yaml). Missing file/key → unknown."""
    try:
        return yaml.safe_load(open(os.path.join(DATA, "card_networks.yaml"), encoding="utf-8")) or {}
    except Exception:
        return {}


def _card_limits():
    """Verified per-card credit limits (data/card_limits.yaml). last-4 → SAR limit.
    Missing ⇒ {} (utilization simply not shown — never guessed)."""
    d = _yaml_load("card_limits.yaml")
    return {str(k): v for k, v in (d.get("limits", {}) if isinstance(d, dict) else {}).items()}


def _positions():
    """Position metadata per account id (data/positions.yaml): as_of · restricted_until ·
    optional contract terms (rate/maturity/payout_freq/units/nav). Manual, honest, as-of stamped."""
    d = _yaml_load("positions.yaml")
    return d.get("positions", {}) if isinstance(d, dict) else {}


def _positions_save(aid, fields):
    with _lock:
        d = _yaml_load("positions.yaml")
        if not isinstance(d, dict):
            d = {}
        pos = d.setdefault("positions", {})
        cur = dict(pos.get(str(aid)) or {})
        cur.update({k: v for k, v in fields.items() if v not in (None, "")})
        pos[str(aid)] = cur
        _yaml_save("positions.yaml", d)


@app.get("/api/rail")
def rail():
    """Live account balances for the sidebar — READ-ONLY. Cash accounts + credit cards."""
    cash, cards = [], []
    hidden = _acct_hidden()
    for a in ff_all("accounts"):
        at = a["attributes"]
        if not at.get("active", True):
            continue
        if a["id"] in hidden:
            continue
        name = at.get("name") or ""
        role = at.get("account_role")
        bal = round(float(at.get("current_balance") or 0), 2)
        cur = at.get("currency_code") or "SAR"
        nl = name.lower()
        if role == "ccAsset":
            bank = "SABB" if "sabb" in nl else "SNB" if "snb" in nl else "CARD"
            # product name only (never the network) — the network is verified, not guessed
            brand = "Alfursan" if "alfursan" in nl else ""
            last4 = name.split("•")[-1].strip() if "•" in name else ""
            net = str(_card_networks().get(last4, "unknown")).lower()
            if net not in ("visa", "mastercard", "mada"):
                net = ""  # unknown → no network mark on the face
            cards.append({"id": a["id"], "name": name, "last4": last4, "bal": bal,
                          "bank": bank, "brand": brand, "network": net})
        elif at.get("type") == "asset" and not any(k in nl for k in ("receivable", "trading", "i owe")):
            cash.append({"id": a["id"], "name": name, "bal": bal, "cur": cur})
    # show meaningful accounts only: non-zero, or a primary bank (kept even at 0)
    cash = [c for c in cash if c["bal"] != 0 or any(p in c["name"].lower() for p in ("snb main", "sabb main"))]
    cards = [c for c in cards if c["bal"] != 0]
    wallet = ("stc", "d360", "barq")
    cash.sort(key=lambda x: (_order_key(x["id"]), any(w in x["name"].lower() for w in wallet), -abs(x["bal"])))
    cards.sort(key=lambda x: (_order_key(x["id"]), -abs(x["bal"])))
    return {"cash": cash, "cards": cards}


@app.get("/api/status")
def status():
    """Instrument-strip feed from REAL signals: the SMS agent's 2-minute heartbeat
    (freshness of the last 'live:' line in logs/sms.log — NOT the weekly health.json),
    and the nightly backup status (data/backup_status.json)."""
    import datetime as _dt
    now = _dt.datetime.now(_dt.timezone.utc)
    log_dir = os.path.dirname(LOG_PATH)
    # --- SMS heartbeat ---
    sms_age = None
    try:
        last = None
        with open(os.path.join(log_dir, "sms.log"), encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if " live:" in line:
                    last = line.split(None, 1)[0]
        if last:
            dtl = _dt.datetime.fromisoformat(last)
            if dtl.tzinfo is None:
                dtl = dtl.replace(tzinfo=_dt.timezone.utc)
            sms_age = max(0, int((now - dtl).total_seconds()))
    except Exception:
        pass
    if sms_age is None:
        sms_state, sms_label = "amber", "SMS ?"
    elif sms_age <= 300:
        sms_state, sms_label = "live", "SMS LIVE"
    elif sms_age <= 600:
        sms_state, sms_label = "idle", f"SMS IDLE · last run {sms_age // 60}m ago"
    else:
        sms_state, sms_label = "amber", f"SMS IDLE · last run {sms_age // 60}m ago"
    # --- nightly backup ---
    bok, bage, have = True, None, False
    try:
        b = json.load(open(os.path.join(DATA, "backup_status.json"), encoding="utf-8"))
        have = True
        bok = bool(b.get("ok"))
        dtb = _dt.datetime.fromisoformat(b["ts"].replace("Z", "+00:00"))
        bage = int((now - dtb).total_seconds())
    except Exception:
        pass
    backup_bad = have and ((not bok) or (bage is not None and bage > 30 * 3600))
    footer = "⚠ BACKUP NEEDS ATTENTION" if backup_bad else "ALL SYSTEMS NOMINAL"
    return {"sms_state": sms_state, "sms_label": sms_label, "sms_age": sms_age,
            "live": sms_state == "live",
            "backup_ok": (bok and not backup_bad), "backup_age": bage,
            "nominal": not backup_bad, "footer": footer}


# ---------------------------------------------------------------- reference data
def tree():
    with open(TREE_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def recents():
    try:
        return json.load(open(RECENTS_PATH, encoding="utf-8"))
    except Exception:
        return []


def fx_rates():
    try:
        return (yaml.safe_load(open(FX_PATH, encoding="utf-8")) or {}).get("rates", {}) or {"SAR": 1.0}
    except Exception:
        return {"SAR": 1.0}


def to_sar(amount, cur):
    r = fx_rates().get(cur, 1.0)
    return round(float(amount) * float(r), 2)


def _networth():
    """THE canonical money position — one computation every surface reads (Dashboard hero + debt tile,
    Accounts hero + rail, morning brief). Two-doors-one-number doctrine: net worth is the headline
    truth; it must never fork.

    Rule (fixed once, here): ALL asset+liability accounts that are ACTIVE, each FX-converted to SAR.
    Hidden accounts ARE counted — hiding is cosmetic (declutter a picker), the money is still yours.
    Archived/closed are excluded — no longer owned. cash = spendable assets (not receivables);
    cards_debt = credit-card balances; other_debt = loans/BNPL/lease/other liabilities; net = assets −
    (cards_debt + other_debt). Callers read the field they need; nobody re-derives it."""
    assets = cash = cards_debt = other_debt = 0.0
    n = 0
    for a in ff_all("accounts", type="asset") + ff_all("accounts", type="liability"):
        at = a["attributes"]
        if not at.get("active", True):            # archived/closed — no longer owned
            continue
        s = to_sar(float(at.get("current_balance") or 0), at.get("currency_code") or "SAR")
        role = at.get("account_role")
        nm = (at.get("name") or "").lower()
        if role == "ccAsset":
            cards_debt += abs(s)
        elif at["type"] in ("liability", "liabilities"):
            other_debt += abs(s)
        else:                                     # asset
            assets += s
            if "receivable" not in nm and not any(x in nm for x in ("owed", "i owe", "مستحقات")):
                cash += s
        n += 1
    assets, cash = round(assets, 2), round(cash, 2)
    cards_debt, other_debt = round(cards_debt, 2), round(other_debt, 2)
    debt = round(cards_debt + other_debt, 2)
    return {"assets": assets, "cash": cash, "cards_debt": cards_debt, "other_debt": other_debt,
            "debt": debt, "net": round(assets - debt, 2), "count": n}


CURRENCIES_PATH = os.path.join(DATA, "currencies.yaml")
_ENABLED = set()


def currency_catalog():
    try:
        return yaml.safe_load(open(CURRENCIES_PATH, encoding="utf-8")) or {}
    except Exception:
        return {"favorites": ["SAR"], "list": {"SAR": ["Saudi Riyal", "﷼"]}}


def ensure_currency(code):
    """Guarantee a currency is enabled in Firefly (create it on demand). No internet."""
    code = (code or "SAR").upper()
    if code in _ENABLED:
        return code
    existing = {c["attributes"]["code"]: c["attributes"]
                for c in ff_all("currencies")}
    if code not in existing:
        cat = currency_catalog().get("list", {}).get(code, [code, code[:1]])
        try:
            ff("POST", "currencies", {"code": code, "name": cat[0], "symbol": cat[1],
                                      "decimal_places": 2, "enabled": True})
        except Exception:
            pass
    elif not existing[code].get("enabled"):
        try:
            ff("POST", f"currencies/{code}/enable", {})
        except Exception:
            pass
    _ENABLED.add(code)
    return code


def save_fx(code, rate):
    with _lock:
        y = {}
        if os.path.exists(FX_PATH):
            y = yaml.safe_load(open(FX_PATH, encoding="utf-8")) or {}
        y.setdefault("rates", {})[code.upper()] = float(rate)
        yaml.safe_dump(y, open(FX_PATH, "w", encoding="utf-8"), allow_unicode=True, sort_keys=False)


def push_recent(cat):
    with _lock:
        r = [cat] + [c for c in recents() if c != cat]
        json.dump(r[:12], open(RECENTS_PATH, "w", encoding="utf-8"), ensure_ascii=False)


def _group(name, role):
    n = name.lower()
    if role == "ccAsset" or "•" in name and any(k in n for k in ["visa", "master", "alfursan"]):
        return "Cards"
    if any(k in n for k in ["wallet", "safe", "safes", "cash"]):
        return "Cash & safes"
    if any(k in n for k in ["stc", "d360", "barq"]):
        return "Digital"
    if "owed" in n or "i owe" in n or "مستحقات" in name or "عليّ" in name:
        return "Receivables & debts"
    return "Banks"


# ---- operator layer: custom order, hide (≠ close), and Other-assets/liabilities kinds ----
def _acct_order():
    d = _yaml_load("account_order.yaml")
    return d.get("order", []) if isinstance(d, dict) else []


def _acct_hidden():
    d = _yaml_load("hidden_accounts.yaml")
    return set(d.get("hidden", [])) if isinstance(d, dict) else set()


def _acct_kinds_map():
    d = _yaml_load("account_kinds.yaml")
    return d.get("kinds", {}) if isinstance(d, dict) else {}


def _order_key(aid):
    o = _acct_order()
    try:
        return o.index(str(aid))
    except ValueError:
        return len(o) + 1


def _group2(aid, name, role, atype):
    """Group name honoring the local Other-assets/Other-liabilities classification (F),
    else the heuristic _group()."""
    k = _acct_kinds_map().get(str(aid))
    if k == "other_asset":
        return "Other assets"
    if k in ("gold", "silver"):
        return "Gold & metals"
    if k in ("certificate", "fund", "etf"):
        return "Investments"
    if k == "hissar":
        return "HISSAR"
    if k == "equity":
        return "Company equity"
    if k in ("loan", "bnpl", "lease"):
        return "Financing"
    if k == "other_liability":
        return "Other liabilities"
    if atype == "liability" and role != "ccAsset" and not any(
            x in (name or "").lower() for x in ("owed", "i owe", "مستحقات", "receivable")):
        return "Other liabilities"
    return _group(name, role)


_ACCT_CACHE = {"ver": None, True: None, False: None}


def accounts(include_liab=True):
    """Active, grouped accounts. Cached on the data-version fingerprint like all_txns — it hits Firefly
    twice + processes every account, and hot paths (suggestions per queue row) called it hundreds of
    times uncached (the 22s /api/queue). Shallow copy so callers never mutate the cache."""
    global _ACCT_CACHE
    ver = _data_version()
    if _ACCT_CACHE["ver"] != ver:
        _ACCT_CACHE = {"ver": ver, True: None, False: None}
    if _ACCT_CACHE[include_liab] is not None:
        return list(_ACCT_CACHE[include_liab])
    hidden = _acct_hidden()
    out = []
    types = ["asset", "liability"] if include_liab else ["asset"]
    for t in types:
        for a in ff_all("accounts", type=t):
            at = a["attributes"]
            if not at.get("active", True):          # closed accounts never in pickers
                continue
            if a["id"] in hidden:                    # hidden ≠ closed: gone from active views
                continue
            out.append({"id": a["id"], "name": at["name"],
                        "balance": round(float(at.get("current_balance") or 0), 2),
                        "currency": at.get("currency_code") or "SAR",
                        "role": at.get("account_role"),
                        "group": _group2(a["id"], at["name"], at.get("account_role"), t)})
    out.sort(key=lambda x: _order_key(x["id"]))
    _ACCT_CACHE[include_liab] = out
    return list(out)


def _acct_by_name():
    return {a["name"]: a for a in accounts()}


# ---------------------------------------------------------------- transactions
def trust_of(tags):
    if "trust:verified" in tags:
        return "verified"
    if "trust:proposed" in tags:
        return "proposed"
    return "imported"


def norm(g, si=0):
    splits = g["attributes"]["transactions"]
    s = splits[si]
    n_splits = len(splits)
    tp = s["type"]
    tags = s.get("tags") or []
    withdrawal = tp == "withdrawal"
    acct = s.get("source_name") if withdrawal or tp == "transfer" else s.get("destination_name")
    if tp == "deposit":
        acct = s.get("destination_name")
    _desc = s.get("description") or ""
    _bcode, _bname, _display = sadad_info(_desc)
    _cp = extract_counterparty(_desc)
    _created = g["attributes"].get("created_at") or ""
    return {
        "counterparty": _cp,
        "created": _created,
        "prov": provenance(tags, acct, (s.get("date") or "")[:10]),
        "id": g["id"], "jid": s["transaction_journal_id"], "type": tp,
        "split": n_splits > 1, "split_i": si, "split_n": n_splits,
        "date": (s.get("date") or "")[:10],
        "amount": round(float(s["amount"]), 2),
        "signed": (-1 if withdrawal else 1) * round(abs(float(s["amount"])), 2),
        "desc": _desc, "display": _display, "biller": _bcode, "biller_name": _bname,
        "notes": s.get("notes") or "",
        "category": s.get("category_name") or "", "tags": tags,
        "trust": trust_of(tags),
        "reconciled": "reconciled" in tags,
        "klass": next((t.split(":", 1)[1] for t in tags if t.startswith("class:")), ""),
        "amortize": next((int(t.split(":")[1]) for t in tags
                          if t.startswith("amortize:") and t.split(":")[1].isdigit()), 0),
        "source": s.get("source_name"), "destination": s.get("destination_name"),
        "source_id": s.get("source_id"), "destination_id": s.get("destination_id"),
        "account": acct, "currency": s.get("currency_code") or "SAR",
        "attachments": int(g["attributes"].get("attachment_count") or 0)
        if "attachment_count" in g["attributes"] else 0,
    }


_TXN_CACHE = {"ver": None, "rows": None}


def all_txns(include_excluded=False):
    """Every transaction, normalized. Excluded transactions (tagged 'excluded' — an imported
    line flagged as an error) are dropped from analytics BY DEFAULT so totals stay honest;
    the Desk passes include_excluded=True to still show them (struck-through, un-excludable).

    Cached in-process keyed on the data-version fingerprint: fetching + normalizing the whole ledger
    cost ~550ms EVERY call (a dashboard hits it several times → seconds), which is fine at 800 rows and
    heavy past 1,200. The fingerprint bumps on every write we make (ff → _DATA_EPOCH) AND catches
    external writes (importer, Firefly UI) via total/newest/updated_at, so the cache is never stale."""
    global _TXN_CACHE
    ver = _data_version()
    if _TXN_CACHE["ver"] != ver or _TXN_CACHE["rows"] is None:
        # expand split groups into one row per line so each line's amount/category/person counts
        # (Firefly stores a split as one group with N journals; reading only [0] would drop lines 2+)
        out = []
        for g in ff_all("transactions"):
            for i in range(len(g["attributes"]["transactions"])):
                out.append(norm(g, i))
        _TXN_CACHE = {"ver": ver, "rows": out}
    rows = _TXN_CACHE["rows"]
    if include_excluded:
        return list(rows)                      # shallow copy — callers must never mutate the cache
    return [t for t in rows if "excluded" not in (t.get("tags") or [])]


def merchant_key(desc):
    s = CARD16.sub("", desc or "")
    s = re.sub(r"\d{2,}", " ", s)
    return re.sub(r"\s+", " ", s).strip().lower()


SADAD_RE = re.compile(r"\b(\d{3})-\d{5,}")


def _merch_yaml():
    try:
        return yaml.safe_load(open(MERCHANTS_PATH, encoding="utf-8")) or {}
    except Exception:
        return {}


def sadad_info(desc):
    """For a SADAD payment, return (biller_code, biller_name|None, display_desc).
    When the biller code is named in merchants.yaml `sadad_names`, the numeric
    reference is swapped for the name — 'SADAD Payment — Electricity/SEC'.
    Filled one biller at a time from the desk, exactly like the merchants map."""
    m = SADAD_RE.search(desc or "")
    if not m:
        return (None, None, desc)
    code = m.group(1)
    name = (_merch_yaml().get("sadad_names") or {}).get(code)
    disp = desc
    if name:
        disp = f"{desc.split(' — ', 1)[0]} — {name}" if " — " in desc else name
    return (code, name, disp)


def _norm(s):
    """Lowercase + Arabic-normalize (alef/ya/ta-marbuta variants, strip tashkeel/tatweel)
    so search matches regardless of case or Arabic orthographic variation."""
    s = (s or "").lower()
    s = (s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
          .replace("ى", "ي").replace("ة", "ه"))
    return re.sub("[ً-ْـ]", "", s)


_CP_NOISE = {"SAUDI", "ARABIA", "BANK", "BENBK", "CITY", "JEDDAH", "RIYADH", "DAMMAM",
             "MAKKAH", "IPS", "IPSP", "SASTCJ", "SAR", "BEN", "DEP", "ID", "CHNL", "PA",
             "REM", "REMBK", "BK", "VAT", "CHRG", "TRANSFERLP", "STC", "SNB", "SABB",
             "THE", "AL", "EST", "CO", "LTD", "KSA", "KING", "KHALID", "RD", "SYSTEM",
             "GENERATED", "NATIONAL", "PERSONAL", "TRANSFER", "TRANSFERS", "INDIVIDUALS",
             "INDIVIDUALSR", "INDIVIDUAL", "TO", "FROM", "FRIENDS", "FRIENDSPERSONAL",
             "FAMILY", "EXPENSES", "EXPENSE", "PAYMENT", "ONLINE", "PURCHASE", "POS",
             "MILY", "FA", "AND", "FOR", "REF", "TRN", "TRANS"}
_CP_TRIGGER = re.compile(r"transfer|تحويل|\bIPS\b|IPSP|SASTCJ|BEN ID|DEP ID", re.I)
# whitespace-bounded ALL-CAPS runs only → a name glued to a code (…O7XRVHESHAM, RAHMANSA177695)
# is NOT captured, because it isn't cleanly delimited. Under-extract rather than mislabel.
_CP_RUN = re.compile(r"(?:^|\s)([A-Z]{2,}(?:\s+[A-Z]{2,}){1,4})(?=\s|$)")


def extract_counterparty(desc):
    """Pull a person/entity name out of an IPS/transfer description — the trailing clean
    ALL-CAPS run, e.g. '…SASTCJ HESHAM ABD EL RAHMAN' -> 'Hesham Abd El Rahman'. STRICT:
    only fires on transfer-like rows and only when the run reads like a real name
    (2–4 alphabetic words, one ≥4 chars). Returns None otherwise — never guesses."""
    if not desc or not _CP_TRIGGER.search(desc):
        return None
    for run in reversed(_CP_RUN.findall(desc)):
        words = [w for w in run.split() if w not in _CP_NOISE]
        if (2 <= len(words) <= 4 and all(w.isalpha() and 2 <= len(w) <= 15 for w in words)
                and any(len(w) >= 4 for w in words)):
            return " ".join(words).title()
    return None


DIGITAL_BANKS = ("STC Pay", "D360", "Barq")   # SMS is the FINAL source — no statements exist
_CONFIRMED_TAGS = {"confirmed", "trust:imported-confirmed", "sms-confirmed"}


def provenance(tags, acct, dt):
    """How the desk KNOWS this transaction: captured-by + confirmation status by account
    class. SNB/SABB SMS items await their statement twin; digital wallets are SMS-final."""
    tags = tags or []
    acct = acct or ""
    if "sms" in tags:
        source, sicon = "SMS", "📲"
    elif any(t.startswith("import:") for t in tags):
        source, sicon = "bank statement", "🏦"
    elif any(t.startswith("fused:") for t in tags):
        source, sicon = "reconciled", "🔗"
    elif "manual" in tags:
        source, sicon = "manual", "✍️"
    else:
        source, sicon = "manual", "✍️"
    is_digital = any(d in acct for d in DIGITAL_BANKS)
    if "sms-missed" in tags:
        status, cicon = "gap flagged — no capture", "⚠️"
    elif source == "SMS" and is_digital:
        status, cicon = "SMS — final source (no statements)", "✔️"
    elif source == "SMS" and (set(tags) & _CONFIRMED_TAGS):
        status, cicon = "confirmed by statement", "✅"
    elif source == "SMS":
        status, cicon = "awaiting statement confirmation", "⏳"
    elif source == "bank statement":
        status, cicon = "from statement", "🏦"
    else:
        status, cicon = "", ""
    # coarse buckets for filtering
    src_key = "sms" if source == "SMS" else ("statement" if source == "bank statement" else "manual")
    st_key = ("awaiting" if status.startswith("awaiting")
              else "confirmed" if ("confirmed" in status or "final" in status or source == "bank statement")
              else "flagged" if cicon == "⚠️" else "")
    return {"source": source, "source_icon": sicon, "captured": dt,
            "status": status, "status_icon": cicon, "src_key": src_key, "st_key": st_key,
            "line": f"{sicon} {source}" + (f" · {cicon} {status}" if status else "")}


def merchant_display(desc):
    """Human-readable merchant/counterparty name — never a raw code string.
    Order: extracted counterparty (person) → SADAD biller name → 'SADAD payment' →
    the reference after the type prefix (if it's not just digits) → the type lead."""
    d = desc or ""
    cp = extract_counterparty(d)
    if cp:
        return cp
    bcode, bname, _ = sadad_info(d)
    if bname:
        return bname
    if bcode or "sadad" in d.lower():
        return "SADAD payment"
    ref = d.split(" — ", 1)[1] if " — " in d else d
    if " — " in d and not re.sub(r"[0-9\s\-:.*#]", "", ref).strip():
        return d.split(" — ", 1)[0][:32]   # reference is all codes → show the type lead
    return ref[:32] or (d[:32] or "—")


def suggestions(row):
    out = []
    d = row["desc"]
    accts = _acct_by_name()
    if row["type"] == "withdrawal" and ATM_RE.search(d):
        if "Hisham Wallet" in accts:
            out.append({"label": "→ Hisham Wallet (cash)", "kind": "transfer",
                        "dir": "to", "account_id": accts["Hisham Wallet"]["id"],
                        "account": "Hisham Wallet"})
    # card/masked reference -> transfer to that account
    l4s = {m[-4:] for m in CARD16.findall(d)} | {a or b for a, b in MASKED4.findall(d)}
    for name, a in accts.items():
        last4 = name.split("•")[-1].strip()[-4:] if "•" in name else ""
        if last4 and last4 in l4s:
            direction = "to" if row["type"] == "withdrawal" else "from"
            out.append({"label": f"{'→' if direction=='to' else '←'} {name}", "kind": "transfer",
                        "dir": direction, "account_id": a["id"], "account": name})
    # SADAD biller -> mapped category (merchants yaml is mtime-cached — re-parsing per row was O(N²))
    for biller, cat in (_merch_cached().get("sadad") or {}).items():
        if biller in d:
            out.append({"label": f"category: {cat}", "kind": "category", "category": cat})
    return out


_MERCH_CACHE = {"mtime": None, "data": {}}


def _merch_cached():
    """The merchants map, cached on the file's mtime — read once, not per suggestions() call."""
    global _MERCH_CACHE
    try:
        mt = os.path.getmtime(MERCHANTS_PATH)
    except OSError:
        return {}
    if _MERCH_CACHE["mtime"] != mt:
        try:
            _MERCH_CACHE = {"mtime": mt, "data": yaml.safe_load(open(MERCHANTS_PATH, encoding="utf-8")) or {}}
        except Exception:
            _MERCH_CACHE = {"mtime": mt, "data": {}}
    return _MERCH_CACHE["data"]


# ---------------------------------------------------------------- HTML shell
def esc(s):
    return html.escape(str(s or ""))


@app.get("/health")
def health():
    try:
        ff("GET", "about")
        ok = True
    except Exception:
        ok = False
    try:
        with httpx.Client(timeout=3) as c:
            a = c.get(f"{AGENT_URL}/health").status_code == 200
    except Exception:
        a = False
    return {"status": "ok" if ok else "degraded", "firefly": ok, "agent": a}


_NOCACHE = {"Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
           "Pragma": "no-cache", "Expires": "0"}

# Build id — changes every rebuild (app.py is re-COPYed, so its mtime moves). An open browser
# tab polls /api/version and, when this changes, offers a reload — so a shipped fix reaches a
# tab that was opened BEFORE the deploy (the exact gap that made the add-category fix "not land").
try:
    _BUILD_ID = str(int(os.path.getmtime(__file__)))
except Exception:
    _BUILD_ID = "0"


@app.get("/api/version")
def api_version():
    return {"build": _BUILD_ID}


# ── Live data-refresh (Wave N) ────────────────────────────────────────────────
# A ledger fingerprint the rail polls; when it changes (new SMS transaction, an edit, a delete)
# open pages surface a "refresh" pill — the reload-pill pattern, now for DATA not just builds.
# Firefly can POST /api/webhook/firefly on every change (near-instant); without it the poll still
# catches changes within its interval. Honest either way.
import time as _time
_DATA_EPOCH = 0            # bumped by the webhook so a configured Firefly gives seconds-latency
_DATA_CACHE = {"t": 0.0, "ver": ""}


def _data_version():
    """Cheap ledger fingerprint: total count + newest journal id + its updated_at. Cached ~8s so
    a room full of open tabs polling can't hammer Firefly."""
    now = _time.time()
    if now - _DATA_CACHE["t"] < 8 and _DATA_CACHE["ver"]:
        return f"{_DATA_EPOCH}:{_DATA_CACHE['ver']}"
    try:
        d = ff("GET", "transactions?limit=1")
        total = d.get("meta", {}).get("pagination", {}).get("total", 0)
        data = d.get("data", [])
        newest = data[0]["id"] if data else "0"
        upd = (data[0]["attributes"].get("updated_at") if data else "") or ""
        ver = f"{total}:{newest}:{upd}"
    except Exception:
        ver = _DATA_CACHE["ver"] or "0:0:"
    _DATA_CACHE["t"], _DATA_CACHE["ver"] = now, ver
    return f"{_DATA_EPOCH}:{ver}"


@app.get("/api/data-version")
def api_data_version():
    return {"ver": _data_version()}


@app.post("/api/webhook/firefly")
async def firefly_webhook(req: Request):
    """Receiver for Firefly III webhooks (STORE/UPDATE/DESTROY transaction). Bumps the data epoch so
    open tabs refresh within seconds. Point a Firefly webhook here (URL /api/webhook/firefly, any
    trigger, delivery JSON). Accepts and 200s even unconfigured — it's harmless groundwork."""
    global _DATA_EPOCH
    _DATA_EPOCH += 1
    _DATA_CACHE["t"] = 0.0     # force a fresh fingerprint on next poll
    try:
        body = await req.json()
        audit("firefly_webhook", trigger=body.get("trigger"), response=body.get("response"))
    except Exception:
        pass
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def index():
    # never let a browser/tunnel/CDN serve a stale desk — the HTML is tiny, always revalidate
    return HTMLResponse(INDEX_HTML, headers=_NOCACHE)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    with open(os.path.join(os.path.dirname(__file__), "dashboard.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/calendar", response_class=HTMLResponse)
def calendar_page():
    with open(os.path.join(os.path.dirname(__file__), "calendar.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/categories", response_class=HTMLResponse)
def categories_page():
    with open(os.path.join(os.path.dirname(__file__), "categories.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/account", response_class=HTMLResponse)
def account_page():
    with open(os.path.join(os.path.dirname(__file__), "account.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/heatmap", response_class=HTMLResponse)
def heatmap_page():
    with open(os.path.join(os.path.dirname(__file__), "heatmap.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/accounts", response_class=HTMLResponse)
def accounts_view_page():
    with open(os.path.join(os.path.dirname(__file__), "accounts.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/api/accounts_grouped")
def accounts_grouped():
    """All accounts grouped, with subtotals — read-only. Now includes Other assets /
    Other liabilities (F) so net worth is whole, and honors hide (≠ close) + custom order."""
    wallet = ("stc", "d360", "barq")
    hidden = _acct_hidden()
    kinds = _acct_kinds_map()
    order = ["Banks", "Wallets", "Cards", "Owed to me", "Other assets", "Other liabilities"]
    groups = {g: [] for g in order}
    accts = ff_all("accounts", type="asset") + ff_all("accounts", type="liability")
    for a in accts:
        at = a["attributes"]
        name = at.get("name") or ""
        nl = name.lower()
        role = at.get("account_role")
        atype = at.get("type")
        bal = round(float(at.get("current_balance") or 0), 2)
        cur = at.get("currency_code") or "SAR"
        archived = not at.get("active", True)
        row = {"id": a["id"], "name": name, "balance": bal, "currency": cur,
               "archived": archived, "hidden": a["id"] in hidden}
        k = kinds.get(str(a["id"]))
        is_liab = atype in ("liability", "liabilities")
        if role == "ccAsset":
            groups["Cards"].append(row)
        elif atype != "asset" and not is_liab:        # skip payees / expense / revenue accounts
            continue
        elif k == "other_asset":
            groups["Other assets"].append(row)
        elif any(x in nl for x in ("owed", "i owe", "مستحقات", "receivable")):
            groups["Owed to me"].append(row)
        elif k == "other_liability" or is_liab:
            groups["Other liabilities"].append(row)
        elif any(w in nl for w in wallet):
            groups["Wallets"].append(row)
        else:
            groups["Banks"].append(row)
    out = []
    for gname in order:
        rows = groups[gname]
        if not rows:
            continue
        # visible active first (by custom order then size), hidden/archived last; totals = visible active
        rows.sort(key=lambda r: (r["archived"] or r["hidden"], _order_key(r["id"]), -abs(r["balance"])))
        live = [r for r in rows if not r["archived"] and not r["hidden"]]
        out.append({"name": gname, "total": round(sum(r["balance"] for r in live), 2),
                    "count": len(live), "closed": sum(1 for r in rows if r["archived"]),
                    "hidden": sum(1 for r in rows if r["hidden"]), "accounts": rows})
    # the hero net worth reads THE canonical computation (FX-correct, active incl hidden) — never the
    # sum of per-group raw totals, which would drift on a foreign balance or a hidden liability.
    return {"groups": out, "networth": _networth()}


# ============================ OPERATOR CONTROL LAYER ============================
def _yaml_load(fn):
    try:
        return yaml.safe_load(open(os.path.join(DATA, fn), encoding="utf-8")) or {}
    except Exception:
        return {}


def _yaml_save(fn, data):
    with open(os.path.join(DATA, fn), "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=True)


_DEFAULT_SETTINGS = {"theme": "dark", "language": "en", "date_format": "gregorian",
                     "landing": "/dashboard", "currency_display": "code"}


@app.get("/api/settings")
def get_settings():
    s = dict(_DEFAULT_SETTINGS)
    s.update(_yaml_load("settings.yaml"))
    return s


@app.post("/api/settings")
async def set_settings(req: Request):
    p = await req.json()
    s = _yaml_load("settings.yaml")
    for k in _DEFAULT_SETTINGS:
        if k in p:
            s[k] = p[k]
    _yaml_save("settings.yaml", s)
    audit("settings", **s)
    return {"ok": True, "settings": {**_DEFAULT_SETTINGS, **s}}


# ---- Rail navigation preferences (Hisham's own order + hidden tabs) — display-only, never deletes ----
# The shared rail (rail.js) renders from this on every page. Hidden = removed from the rail render only;
# the page stays reachable by URL and ⌘K search. Empty order → the rail's default order.
@app.get("/api/nav/prefs")
def nav_prefs():
    d = _yaml_load("nav_prefs.yaml")
    return {"order": list(d.get("order") or []), "hidden": list(d.get("hidden") or [])}


@app.post("/api/nav/prefs")
async def nav_prefs_save(req: Request):
    p = await req.json()
    order = [str(x) for x in (p.get("order") or []) if x]
    hidden = [str(x) for x in (p.get("hidden") or []) if x]
    _yaml_save("nav_prefs.yaml", {"order": order, "hidden": hidden})
    audit("nav_prefs", order=len(order), hidden=len(hidden))
    return {"ok": True, "order": order, "hidden": hidden}


# ---- THE OPENING · honest-maturity foundation ---------------------------------------------------
# The surplus gate is a DIMMER, not a lock: every gated surface opens, computes what its data supports,
# and names — from the REAL ledger, never hardcoded — exactly how much history a stronger claim needs and
# the DATE that requirement is met. `_complete_months()` counts months fully in the past that carry data
# (the current month is in-progress, never "complete"). `_maturity(need)` turns that into a banner.
def _complete_months():
    cur = _date.today().strftime("%Y-%m")
    return sorted({(t["date"] or "")[:7] for t in all_txns()
                   if t.get("date") and (t["date"] or "")[:7] < cur})


def _maturity(need):
    import calendar as _cal
    have = _complete_months()
    k = len(have)
    out = {"have": k, "need": int(need), "met": k >= int(need), "months": have}
    if out["met"]:
        out["ready_date"] = None
        out["ready_label"] = None
        return out
    today = _date.today()
    ahead = int(need) - k - 1          # 0 → the current in-progress month completes the requirement
    ry = today.year + (today.month - 1 + ahead) // 12
    rm = (today.month - 1 + ahead) % 12 + 1
    d = _date(ry, rm, _cal.monthrange(ry, rm)[1])
    out["ready_date"] = d.isoformat()
    try:
        out["ready_label"] = d.strftime("after %-d %B")
    except ValueError:
        out["ready_label"] = "after " + d.isoformat()
    return out


@app.get("/api/maturity")
def api_maturity(need: int = 3):
    return _maturity(need)


# ---- THE OPENING · Today (tab 1) — what's due, what landed, what's committed, the day's shape.
# Forward view (next7/heads) moved here from the dashboard per the charter removal-condition: Today owns
# "what's coming" permanently. Safe-to-spend is honest arithmetic (cash − remaining committed), carried
# with a provisional label because committed money is only as complete as the bills you've priced.
def _forward_due(t=None):
    t = t or _date.today()
    next7, heads = [], []
    try:
        for b in bills_view(t):
            dd = b.get("days")
            if dd is not None and 0 <= dd <= 7:
                next7.append({"name": b["name"], "date": b["next_due"], "days": dd,
                              "amount": b["amount"], "kind": "bill"})
    except Exception:
        pass
    try:
        _accn = {a["id"]: a["name"] for a in accounts()}
        for aid, s in _schedules().items():
            nm = _accn.get(aid) or s.get("item") or "Plan"
            for i in s.get("installments", []):
                if i.get("paid") or i.get("settled_manual") or not i.get("date"):
                    continue
                try:
                    dd = (_date.fromisoformat(i["date"][:10]) - t).days
                except Exception:
                    continue
                if 0 <= dd <= 7:
                    next7.append({"name": (("balloon · " if i.get("balloon") else "") + nm),
                                  "date": i["date"][:10], "days": dd, "amount": i.get("amount"),
                                  "kind": "balloon" if i.get("balloon") else "installment"})
    except Exception:
        pass
    try:
        for c in (api_certificates().get("certificates") or []):
            mt = (c.get("maturity") or "")[:10]
            if not mt:
                continue
            try:
                dd = (_date.fromisoformat(mt) - t).days
            except Exception:
                continue
            if 0 <= dd <= 7:
                next7.append({"name": (c.get("name") or "Certificate") + " matures", "date": mt,
                              "days": dd, "amount": None, "kind": "maturity"})
    except Exception:
        pass
    next7.sort(key=lambda x: (x["days"], x["name"]))
    try:
        for b in (api_balloons().get("balloons") or []):
            m2d = b.get("months_to_due")
            if m2d is None or not (0 <= m2d <= 6):
                continue
            try:
                if (_date.fromisoformat((b.get("date") or "")[:10]) - t).days <= 7:
                    continue
            except Exception:
                pass
            heads.append({"name": (b.get("name") or "Lease") + " · balloon", "date": (b.get("date") or "")[:10],
                          "note": "in %d month%s" % (m2d, "" if m2d == 1 else "s"), "urgent": m2d <= 3,
                          "amount": b.get("amount"), "kind": "balloon"})
    except Exception:
        pass
    try:
        for c in (api_certificates().get("certificates") or []):
            m2m = c.get("months_to_maturity")
            if m2m is None or not (0 <= m2m <= 1):
                continue
            mt = (c.get("maturity") or "")[:10]
            try:
                if mt and (_date.fromisoformat(mt) - t).days <= 7:
                    continue
            except Exception:
                pass
            heads.append({"name": (c.get("name") or "Certificate") + " matures", "date": mt,
                          "note": "renew or collect", "urgent": False, "amount": None, "kind": "maturity"})
    except Exception:
        pass
    try:
        for c in (card_registry().get("cards") or []):
            de = c.get("days_to_expiry")
            if de is None or not (7 < de <= 60):
                continue
            heads.append({"name": "Card •%s expires" % c.get("last4", ""), "date": c.get("expiry_date"),
                          "note": "in %dd" % de, "urgent": de <= 30, "amount": None, "kind": "expiry"})
    except Exception:
        pass
    heads.sort(key=lambda x: (not x["urgent"], x.get("date") or ""))
    return {"next7": next7, "heads": heads}


def _committed_remaining(cm, t):
    """Committed money STILL to leave this month — dated obligations today-or-later + envelope set-asides
    (envelopes carry no date, so counted in full: the conservative reservation)."""
    iso = t.isoformat()
    tot = 0.0
    for b in cm.get("bills", []):
        if any((d or "") >= iso for d in (b.get("dates") or [])):
            tot += b.get("amount") or 0
    for c in cm.get("cards", []):
        if (c.get("date") or "") >= iso:
            tot += c.get("amount") or 0
    for d in cm.get("debt", []):
        if (d.get("date") or "") >= iso:
            tot += d.get("amount") or 0
    for e in cm.get("envelopes", []):
        tot += e.get("amount") or 0
    return round(tot, 2)


@app.get("/api/today")
def api_today():
    return _vcache("today", _date.today().isoformat(), _today_impl)


def _today_impl():
    t = _date.today()
    iso = t.isoformat()
    txns = all_txns()
    landed = [{"id": x["id"], "name": merchant_display(x["desc"]), "signed": x["signed"],
               "account": x["account"], "cat": x["category"], "type": x["type"]}
              for x in txns if (x.get("date") or "")[:10] == iso]
    landed.sort(key=lambda x: -abs(x["signed"]))
    day_in = round(sum(x["signed"] for x in landed if x["signed"] > 0 and x["type"] == "deposit"), 2)
    day_out = round(sum(-x["signed"] for x in landed if x["signed"] < 0 and x["type"] == "withdrawal"), 2)
    fwd = _forward_due(t)
    cm = _committed_impl()
    cash = round(_networth()["cash"], 2)
    remaining = _committed_remaining(cm, t)
    safe = round(cash - remaining, 2)
    return {"date": iso, "weekday": t.strftime("%A"),
            "landed": landed, "day_in": day_in, "day_out": day_out, "landed_count": len(landed),
            "due": fwd["next7"], "heads": fwd["heads"],
            "committed_total": cm.get("total", 0), "committed_remaining": remaining,
            "by_source": cm.get("by_source", {}), "cash": cash, "safe_to_spend": safe,
            "bills_unset": cm.get("bills_amounts_unset", 0),
            "maturity": _maturity(1)}   # a full lived month validates the buffer assumption


# ---- THE OPENING · Family (tab 2) — per-person truth on real person-tags + the qattah/owed ledger.
# Openable now on Sarah's data: flows per person, per-person pockets (accounts they own), qattah balances,
# per-person spend trend across complete months — each carrying its honest sample depth.
@app.get("/api/family")
def api_family():
    return _vcache("family", _date.today().strftime("%Y-%m"), _family_impl)


# ---- THE OPENING · Subscriptions (tab 3) — detected + declared recurring inventory.
# Declared = your recurring bills; detected = merchants that recur monthly in the ledger. Undeclared
# recurring charges become one-tap proposals. Price-creep / unused-detection need history, so they're
# honestly "watching since <first month>" until enough months complete.
@app.get("/api/subscriptions")
def api_subscriptions():
    return _vcache("subs", _date.today().strftime("%Y-%m"), _subs_impl)


# ---- THE OPENING · Forecast (tab 4) — a 90-day cash curve. The KNOWN line is dated obligations only
# (bills, installments, card dues, payouts) — confident. The PROVISIONAL overlay adds a modelled daily
# discretionary burn from history — labelled, and only meaningful once 3 months complete.
@app.get("/api/forecast")
def api_forecast():
    return _vcache("forecast", _date.today().isoformat(), _forecast_impl)


# ---- THE OPENING · Debt coach (tab 5) — payoff strategy on real cards + financing, SIMAH-floor aware.
# Shows the attack order (avalanche by rate / snowball by balance) and the minimums that must always be
# paid. The months-to-debt-free RECOMMENDATION is gated behind a validated monthly surplus — stated plainly
# — because a payoff plan built on a surplus that doesn't exist yet is exactly the guess this system refuses.
@app.get("/api/debt")
def api_debt():
    return _vcache("debt", _date.today().strftime("%Y-%m"), _debt_impl)


# ---- THE OPENING · Insights (tab 6) — the pattern finder. Surfaces ONLY patterns whose sample count
# supports them, with the count visible; everything else is listed as "coming into focus" with the date it
# unlocks. Links to the Reports Sankey and Subscriptions rather than rebuilding either. With 2 complete
# months, most trend/anomaly patterns don't qualify yet — and it says so plainly.
@app.get("/api/insights")
def api_insights():
    return _vcache("insights", _date.today().strftime("%Y-%m"), _insights_impl)


# ---- THE OPENING · Budget (tab 7) — manual targets (already live) + AI-PROPOSED targets from history.
# A proposal is the average of a category's spend across complete months, shown WITH its evidence (the
# monthly figures) and sample count. Accepting one writes a real target via the existing /api/category/target
# door — one write door. Proposals stay labelled provisional until 3 complete months exist.
@app.get("/api/budget")
def api_budget():
    return _vcache("budget", _date.today().strftime("%Y-%m"), _budget_impl)


# ---- THE OPENING · Zakat (tab 8) — hawl · zakatable base · nisab · 2.5%. Full machinery over the existing
# hawl tracker + _zakatable_total; opens honest-empty on the position side until certificates/gold/HISSAR
# are entered (right now the base is cash-only, and the nisab is an estimate until the verified figure is set).
@app.get("/api/zakat")
def api_zakat():
    import json as _json
    cfg = _zakat_cfg()
    try:
        trail = _json.load(open(os.path.join(DATA, "hawl_trail.json"), encoding="utf-8"))
    except Exception:
        trail = {"records": {}}
    state = _hawl_recompute(trail)
    total, parts = _zakatable_total()
    above = total >= cfg["nisab"]
    pos_kinds = {p.get("kind") for p in parts}
    has_positions = bool(_positions()) or bool(pos_kinds & {"gold", "silver", "certificate", "fund", "etf"})
    state.update({"zakatable_total": round(total, 2), "parts": parts,
                  "nisab": round(cfg["nisab"], 2), "nisab_estimated": cfg["nisab_estimated"],
                  "nisab_estimate": round(cfg["nisab_estimate"], 2),
                  "gold_price": cfg["gold_price_sar_per_gram"], "gold_grams": cfg["gold_nisab_grams"],
                  "above": above, "zakat_rate": 0.025,
                  "zakat_due_now": round(total * 0.025, 2) if above else 0.0,
                  "has_positions": has_positions})
    return state


# ---- THE OPENING · Wealth (tab 9) — allocation · currency exposure · restricted-vs-available · net-worth
# trajectory. Allocation classes come from account kinds/groups; investment classes stay empty until the
# positions (gold, certificates, HISSAR, funds) and their prices are entered — honest-empty, not fake.
@app.get("/api/wealth")
def api_wealth():
    return _vcache("wealth", str(_data_version()), _wealth_impl)


def _wealth_impl():
    kinds = _acct_kinds_map()
    fx = fx_rates() or {}

    def sar(amt, cur):
        return float(amt) * (1 if cur == "SAR" else (fx.get(cur) or 1))

    KCLASS = {"gold": "Gold & metals", "silver": "Gold & metals", "certificate": "Certificates",
              "fund": "Funds", "etf": "Equity / ETF", "equity": "Equity / ETF"}
    GCLASS = {"Cash & safes": "Cash", "Banks": "Bank", "Digital": "Digital wallets"}
    alloc, cur_exp, total_asset = {}, {}, 0.0
    for a in ff_all("accounts"):
        at = a["attributes"]
        if at.get("type") != "asset" or not at.get("active", True):
            continue
        grp = _group2(a["id"], at.get("name"), at.get("account_role"), at.get("type"))
        if grp in ("Cards", "Financing", "Receivables & debts"):
            continue
        cur = at.get("currency_code") or "SAR"
        bal = round(sar(at.get("current_balance") or 0, cur), 2)
        if bal <= 0:
            continue
        cls = KCLASS.get(kinds.get(str(a["id"]))) or GCLASS.get(grp) or "Other assets"
        alloc[cls] = round(alloc.get(cls, 0) + bal, 2)
        cur_exp[cur] = round(cur_exp.get(cur, 0) + bal, 2)
        total_asset += bal
    pos = api_positions()
    nwp = _networth()
    invested = round(sum(v for k, v in alloc.items() if k not in ("Cash", "Bank", "Digital wallets")), 2)
    return {"net_worth": nwp["net"], "assets": round(total_asset, 2), "invested": invested,
            "allocation": [{"cls": k, "amount": v} for k, v in sorted(alloc.items(), key=lambda x: -x[1])],
            "currency_exposure": [{"cur": k, "amount": v} for k, v in sorted(cur_exp.items(), key=lambda x: -x[1])],
            "restricted": round(pos.get("restricted", 0), 2),
            "available_of_total": round(pos.get("available_of_total", 0), 2),
            "positions": pos.get("positions", []), "has_positions": pos.get("count", 0) > 0,
            "maturity": _maturity(3)}


def _budget_impl():
    txns = all_txns()
    complete = _complete_months()
    curmo = _date.today().strftime("%Y-%m")
    targets = _cat_targets()
    cats = {}
    for t in txns:
        if t["type"] != "withdrawal":
            continue
        main = _main_cat(t["category"]) or "Uncategorized"
        mo = (t["date"] or "")[:7]
        e = cats.setdefault(main, {})
        e[mo] = round(e.get(mo, 0) + t["amount"], 2)
    rows = []
    for name, months in cats.items():
        hist = [round(months.get(mo, 0), 2) for mo in complete]     # spend per complete month = evidence
        actual = round(months.get(curmo, 0), 2)
        avg = round(sum(hist) / len(hist), 2) if hist else 0.0
        tg = targets.get(name)
        target_monthly = _target_monthly(_target_norm(tg)) if tg else None
        rows.append({"name": name, "actual": actual, "target": target_monthly,
                     "proposed": avg, "evidence": hist, "has_target": target_monthly is not None})
    rows.sort(key=lambda r: -max(r["actual"], r["proposed"] or 0, r["target"] or 0))
    targeted = [r for r in rows if r["has_target"]]
    proposals = [r for r in rows if not r["has_target"] and r["proposed"] > 0]
    return {"rows": rows, "targeted": targeted, "proposals": proposals[:14],
            "total_target": round(sum(r["target"] or 0 for r in rows), 2),
            "total_actual": round(sum(r["actual"] for r in rows), 2),
            "total_proposed": round(sum(r["proposed"] for r in proposals), 2),
            "targeted_count": len(targeted), "untargeted_count": len(proposals),
            "complete_months": complete, "maturity": _maturity(3)}


def _insights_impl():
    txns = all_txns()
    today = _date.today()
    dated = [t["date"][:10] for t in txns if t.get("date")]
    first = min(dated) if dated else None
    weeks = ((today - _date.fromisoformat(first)).days // 7) if first else 0
    cm3 = _maturity(3)
    curmo = today.strftime("%Y-%m")
    now, pending = [], []

    # Observation — spending concentration this month (needs only the live month; qualifies)
    catmap = {}
    for t in txns:
        if t["type"] == "withdrawal" and (t["date"] or "")[:7] == curmo:
            k = _main_cat(t["category"]) or "Uncategorized"
            catmap[k] = catmap.get(k, 0) + t["amount"]
    if catmap:
        tot = sum(catmap.values())
        top = max(catmap.items(), key=lambda x: x[1])
        now.append({"kind": "concentration", "title": "Where this month concentrates",
                    "body": "%s is %d%% of this month's spending (SAR %s of %s)." % (
                        top[0], round(top[1] / tot * 100), f"{round(top[1]):,}", f"{round(tot):,}"),
                    "sample": "this month so far", "link": "/categories"})

    # Observation — heaviest spending weekday (needs >= 6 weeks of history)
    if weeks >= 6:
        dow = [0.0] * 7
        for t in txns:
            if t["type"] != "withdrawal" or not t.get("date"):
                continue
            try:
                dow[_date.fromisoformat(t["date"][:10]).weekday()] += t["amount"]
            except Exception:
                pass
        names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        hi = max(range(7), key=lambda i: dow[i])
        now.append({"kind": "weekday", "title": "Your heaviest spending day",
                    "body": "Across %d weeks, %s is your highest-spend weekday (SAR %s total)." % (
                        weeks, names[hi], f"{round(dow[hi]):,}"),
                    "sample": "%d weeks" % weeks, "link": "/dashboard"})
    else:
        pending.append({"kind": "weekday", "title": "Weekday spending pattern",
                        "need": "6 weeks of history", "ready": "in %d weeks" % max(0, 6 - weeks)})

    # Patterns that genuinely need 3 complete months — listed with their unlock date until then
    if not cm3["met"]:
        pending.append({"kind": "trend", "title": "Rising & falling categories",
                        "need": "3 complete months", "ready": cm3["ready_label"]})
        pending.append({"kind": "anomaly", "title": "Unusual-spend anomalies (2x typical)",
                        "need": "3 complete months", "ready": cm3["ready_label"]})
        pending.append({"kind": "seasonal", "title": "Seasonal rhythms",
                        "need": "a fuller year", "ready": "as the year fills"})

    return {"now": now, "pending": pending, "weeks": weeks, "maturity": cm3,
            "links": {"sankey": "/reports?open=sankey", "subs": "/subscriptions"}}


def _debt_impl():
    accs = accounts()
    cm = _committed_impl()
    mins = {c["name"]: c["amount"] for c in cm.get("cards", [])}
    scheds = _schedules()
    debts = []
    for a in accs:
        role = a.get("role")
        grp = a.get("group") or ""
        bal = a.get("balance") or 0
        if role == "ccAsset" and bal < 0:
            l4 = a["name"].split("•")[-1].strip() if "•" in a["name"] else ""
            limit = _card_limits().get(l4)
            debts.append({"name": a["name"], "kind": "card", "balance": round(-bal, 2),
                          "limit": limit, "util": (round(-bal / limit * 100) if limit else None),
                          "min": mins.get(a["name"]), "rate": None, "rate_known": False, "zero": False})
        elif grp == "Financing" and bal < 0:
            s = scheds.get(a["id"]) or {}
            rate = s.get("annual_rate")
            kind = s.get("kind") or "financing"
            nexti = next((i for i in s.get("installments", []) if not i.get("paid")), None)
            debts.append({"name": a["name"], "kind": kind, "balance": round(-bal, 2),
                          "limit": None, "util": None, "min": (nexti.get("amount") if nexti else None),
                          "rate": rate, "rate_known": rate is not None,
                          "zero": (not rate) and kind == "bnpl"})

    # avalanche: highest cost first. Saudi credit cards carry the highest APR but it isn't stored, so they
    # sort to the top (flagged) ahead of rate-known financing; interest-free BNPL sorts last.
    def av_key(d):
        if d["kind"] == "card":
            return 1e6
        if d["zero"]:
            return -1
        return d.get("rate") or 0
    avalanche = [d["name"] for d in sorted(debts, key=lambda d: -av_key(d))]
    snowball = [d["name"] for d in sorted(debts, key=lambda d: d["balance"])]

    total_debt = round(sum(d["balance"] for d in debts), 2)
    min_total = round(sum(d["min"] or 0 for d in debts), 2)
    try:
        cost_of_debt = round(compute_report({"type": "riba"}).get("totals", {}).get("cost", 0), 2)
    except Exception:
        cost_of_debt = 0.0

    # validated monthly surplus? avg net over complete months, and it must be positive + enough months lived
    complete = _complete_months()
    nets = []
    for mo in complete:
        mt = [t for t in all_txns() if (t["date"] or "")[:7] == mo]
        nets.append(round(sum(t["amount"] for t in mt if t["type"] == "deposit")
                          - sum(t["amount"] for t in mt if t["type"] == "withdrawal"), 2))
    avg_net = round(sum(nets) / len(nets), 2) if nets else 0.0
    mat = _maturity(3)
    surplus_validated = avg_net > 0 and mat["met"]
    return {"debts": debts, "avalanche": avalanche, "snowball": snowball,
            "total_debt": total_debt, "min_total": min_total, "cost_of_debt": cost_of_debt,
            "any_rate_known": any(d["rate_known"] for d in debts),
            "avg_net": avg_net, "surplus_validated": surplus_validated,
            "maturity": mat}


def _month_step(d):
    import calendar as _cal
    y = d.year + (1 if d.month == 12 else 0)
    mth = 1 if d.month == 12 else d.month + 1
    return _date(y, mth, min(d.day, _cal.monthrange(y, mth)[1]))


def _forecast_impl():
    import calendar as _cal
    today = _date.today()
    horizon = today + timedelta(days=90)
    events = []

    def add(dd, amount, kind, name):
        if amount and today <= dd <= horizon:
            events.append({"date": dd.isoformat(), "amount": round(amount, 2), "kind": kind, "name": name})

    # dated installments (BNPL / lease / loan)
    try:
        _accn = {a["id"]: a["name"] for a in accounts()}
        for aid, s in _schedules().items():
            nm = _accn.get(aid) or s.get("item") or "Plan"
            for i in s.get("installments", []):
                if i.get("paid") or i.get("settled_manual") or not i.get("date"):
                    continue
                try:
                    add(_date.fromisoformat(i["date"][:10]), -(i.get("amount") or 0), "installment", nm)
                except Exception:
                    pass
    except Exception:
        pass
    # bills — priced only; monthly ones projected across the window, irregular ones by their schedule
    try:
        for b in bills_view(today):
            amt = b.get("amount")
            sched = b.get("schedule")
            if sched:
                for x in sched:
                    if x.get("paid"):
                        continue
                    try:
                        add(_date.fromisoformat(x["date"][:10]), -(x.get("amount") or 0), "bill", b["name"])
                    except Exception:
                        pass
            elif amt is not None and b.get("next_due"):
                try:
                    d0 = _date.fromisoformat(b["next_due"][:10])
                except Exception:
                    continue
                if (b.get("freq") or "").startswith("month"):
                    d = d0
                    for _ in range(4):
                        add(d, -amt, "bill", b["name"])
                        d = _month_step(d)
                        if d > horizon:
                            break
                else:
                    add(d0, -amt, "bill", b["name"])
    except Exception:
        pass
    # card minimum payments (dated in committed), projected monthly
    cm = _committed_impl()
    for c in cm.get("cards", []):
        if c.get("date") and c.get("amount"):
            try:
                d = _date.fromisoformat(c["date"][:10])
            except Exception:
                continue
            for _ in range(4):
                add(d, -(c["amount"]), "card", c.get("name"))
                d = _month_step(d)
                if d > horizon:
                    break
    # certificate payouts (dated inflow), when an amount is known
    try:
        for c in (api_certificates().get("certificates") or []):
            amt = c.get("payout_amount") or c.get("monthly_payout")
            for pd in (c.get("payout_dates") or []):
                if amt:
                    try:
                        add(_date.fromisoformat(pd[:10]), amt, "payout", c.get("name") or "Certificate")
                    except Exception:
                        pass
    except Exception:
        pass

    cash0 = round(_networth()["cash"], 2)
    events.sort(key=lambda e: e["date"])
    # KNOWN daily curve
    series, bal, ei = [], cash0, 0
    lowest = {"bal": cash0, "date": today.isoformat()}
    neg_date = None
    d = today
    while d <= horizon:
        diso = d.isoformat()
        while ei < len(events) and events[ei]["date"] == diso:
            bal = round(bal + events[ei]["amount"], 2)
            ei += 1
        if bal < lowest["bal"]:
            lowest = {"bal": bal, "date": diso}
        if neg_date is None and bal < 0:
            neg_date = diso
        series.append({"date": diso, "bal": bal})
        d += timedelta(days=1)
    # PROVISIONAL discretionary daily burn (from complete months, minus priced recurring bills)
    complete = _complete_months()
    disc_daily = 0.0
    if complete:
        tot = sum(t["amount"] for t in all_txns()
                  if t["type"] == "withdrawal" and (t["date"] or "")[:7] in complete)
        days = sum(_cal.monthrange(int(mo[:4]), int(mo[5:7]))[1] for mo in complete) or 1
        bills_month = sum(b.get("monthly") or 0 for b in bills_view(today))
        disc_daily = max(0.0, round(tot / days - bills_month / 30.0, 2))
    prov = [{"date": s["date"], "bal": round(s["bal"] - disc_daily * i, 2)} for i, s in enumerate(series)]

    out_total = round(-sum(e["amount"] for e in events if e["amount"] < 0), 2)
    in_total = round(sum(e["amount"] for e in events if e["amount"] > 0), 2)
    return {"cash0": cash0, "series": series, "prov": prov, "events": events[:40],
            "end_known": series[-1]["bal"], "end_prov": prov[-1]["bal"],
            "lowest": lowest, "neg_date": neg_date, "disc_daily": disc_daily,
            "out_total": out_total, "in_total": in_total,
            "unpriced": sum(1 for b in bills_view(today) if b.get("amount") is None),
            "horizon": horizon.isoformat(), "today": today.isoformat(),
            "maturity": _maturity(3)}


def _subs_impl():
    from collections import defaultdict
    txns = all_txns()
    today = _date.today()
    # detect recurring merchants: same merchant across >= 2 distinct months, reasonably stable amount
    bym = defaultdict(list)
    for t in txns:
        if t["type"] != "withdrawal":
            continue
        bym[merchant_key(t["desc"])].append(t)
    detected = []
    for k, ts in bym.items():
        months = sorted({(t["date"] or "")[:7] for t in ts if t.get("date")})
        if len(months) < 2:
            continue
        amts = [t["amount"] for t in ts]
        avg = sum(amts) / len(amts)
        # a subscription is stable-amount + recurring; flag the coefficient of variation for honesty
        spread = (max(amts) - min(amts)) / avg if avg else 1
        last = max(ts, key=lambda t: t.get("date") or "")
        detected.append({"key": k, "name": merchant_display(last["desc"]), "months_seen": len(months),
                         "first_month": months[0], "monthly": round(avg, 2), "stable": spread <= 0.15,
                         "last_date": last.get("date"), "n": len(ts)})
    # declared recurring bills
    declared = []
    unpriced = 0
    for b in bills_view(today):
        known = b.get("monthly") is not None
        if not known:
            unpriced += 1
        declared.append({"name": b["name"], "monthly": b.get("monthly"), "amount": b.get("amount"),
                         "freq": b.get("freq"), "next_due": b.get("next_due"), "days": b.get("days"),
                         "known": known})

    def norm(s):
        return "".join(ch for ch in (s or "").lower() if ch.isalnum())

    dnorms = [norm(d["name"]) for d in declared]
    # a subscription-like charge is STABLE, roughly one-per-month, subscription-sized, and not an obvious
    # transfer/fee/ATM — otherwise "recurs in 2 months" catches villa spend, family transfers and POS runs.
    import re as _re
    EXCL = _re.compile(r"تحويل|حوال|transfer|tawarr|financing|fee|رسوم|atm|cash\s*with|withdraw|"
                       r"salary|راتب|sadad|قسط|installment|pos purchase", _re.I)
    undeclared = []
    for d in detected:
        nm = norm(d["name"])
        if any(nm and (nm in dn or dn in nm) for dn in dnorms if dn):
            continue                                   # already a declared bill
        if not d["stable"] or d["monthly"] > 3000:
            continue                                   # not stable, or too big to be a subscription
        if d["n"] > d["months_seen"] + 1:
            continue                                   # many charges/month → a frequent merchant, not a sub
        if EXCL.search(d["name"] or ""):
            continue                                   # transfers / fees / ATM / installments are not subs
        undeclared.append(d)
    undeclared.sort(key=lambda x: -x["monthly"])

    declared_monthly = round(sum(d["monthly"] for d in declared if d["monthly"]), 2)
    undeclared_monthly = round(sum(d["monthly"] for d in undeclared), 2)
    # next-charge calendar — declared bills with a next date, soonest first
    calendar = sorted(
        [{"name": d["name"], "date": d["next_due"], "days": d["days"], "amount": d.get("amount")}
         for d in declared if d.get("next_due")],
        key=lambda x: x["date"] or "")
    return {"declared": declared, "undeclared": undeclared, "calendar": calendar[:12],
            "declared_monthly": declared_monthly, "undeclared_monthly": undeclared_monthly,
            "monthly_total": round(declared_monthly + undeclared_monthly, 2),
            "declared_count": len(declared), "unpriced": unpriced,
            "watching_since": today.strftime("%b %Y"),
            "maturity": _maturity(3)}


def _family_impl():
    txns = all_txns()
    complete = _complete_months()
    curmo = _date.today().strftime("%Y-%m")
    trend_months = (complete + [curmo])[-4:]        # up to 3 complete + the month in progress

    def own(name):
        n = (name or "").lower()
        for p in PERSON_TAGS:
            if p.lower() in n:
                return p
        return None

    pockets = {}
    for a in accounts():
        # "pocket" = spendable balances a person holds — asset accounts only, never their card/loan debt
        if a.get("role") == "ccAsset" or (a.get("group") or "") in ("Cards", "Financing", "Receivables & debts"):
            continue
        o = own(a["name"])
        if o:
            pockets.setdefault(o, []).append({"name": a["name"], "bal": round(a.get("balance") or 0, 2)})

    rec = api_receivables()
    owed_by = {r["person"]: r for r in (rec.get("by_person") or [])}

    people = []
    for p in PERSON_TAGS:
        pt = [t for t in txns if p in (t.get("tags") or [])]
        this = [t for t in pt if (t["date"] or "")[:7] == curmo]
        spend = round(sum(t["amount"] for t in this if t["type"] == "withdrawal"), 2)
        income = round(sum(t["amount"] for t in this if t["type"] == "deposit"), 2)
        trend = [{"month": mo,
                  "spend": round(sum(t["amount"] for t in pt
                                     if (t["date"] or "")[:7] == mo and t["type"] == "withdrawal"), 2)}
                 for mo in trend_months]
        pk = pockets.get(p, [])
        pocket_total = round(sum(x["bal"] for x in pk), 2)
        owed = owed_by.get(p)
        # skip people with no footprint at all (keep Hisham + Sarah always — the household's two adults)
        if p not in ("Hisham", "Sarah") and not pt and not pk and not owed:
            continue
        people.append({"person": p, "spend": spend, "income": income, "net": round(income - spend, 2),
                       "count": len(this), "all_count": len(pt), "trend": trend,
                       "pockets": pk, "pocket_total": pocket_total,
                       "owed": (owed["outstanding"] if owed else 0.0),
                       "owed_by_origin": (owed.get("by_origin") if owed else {})})
    people.sort(key=lambda x: (-(x["spend"] + x["pocket_total"]), x["person"]))
    return {"month": curmo, "people": people,
            "qattah_total": rec.get("qattah_total", 0), "owed_balance": rec.get("owed_balance", 0),
            "unassigned_owed": rec.get("unattributed", 0),
            "maturity": _maturity(3)}


@app.get("/api/backup/status")
def backup_status():
    """Backups panel data (item C). The app can't run host restic — the nightly job
    publishes status + a snapshot manifest into data/ (via Docker), read here."""
    st, man = {"ok": None}, {}
    try:
        st = json.load(open(os.path.join(DATA, "backup_status.json")))
    except Exception:
        pass
    try:
        man = json.load(open(os.path.join(DATA, "backup_snapshots.json")))
    except Exception:
        pass
    return {"status": st, "manifest": man}


@app.post("/api/backup/run")
async def backup_run():
    """Signal the host to back up now — drop a trigger file a launchd WatchPath agent watches.
    NOT a restore (deliberately no one-click restore — accidental restores are dangerous)."""
    trig = "/app/triggers"
    try:
        os.makedirs(trig, exist_ok=True)
        with open(os.path.join(trig, "backup_request"), "w") as fh:
            fh.write(datetime.now().isoformat())
        audit("backup_run_requested")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": f"could not signal the host backup agent ({e}). "
                "Is com.hakim.backup-trigger loaded?"}


# Dead-man's switch: every agent's last-run + status, read live from the mounted logs.
# (name, logfile-basename, success-marker, expected-max-age-hours, runnable-now)
_AGENTS = [
    ("Nightly backup", "backup", "backup complete", 30, True),
    ("Backup trigger", "backup", "backup complete", None, False),   # event-driven (Back up now)
    ("Restore drill", "restore_drill", "PASSED", 24 * 8 + 12, False),
    ("Weekly health", "health", "", 24 * 8 + 12, False),
    ("Morning brief", "brief", "ok ", 30, False),
    ("SMS capture", "sms", "live:", 1, False),
    ("Hawl tracker", "hawl", "OK ", 30, False),   # nightly zakatable snapshot — must never miss a day
]
_LOG_DIRS = ["/app/joblogs", "/app/logs"]   # ~/Library/Logs/hakim (backup/restore) + Documents/logs


def _agent_status(logfile, marker, max_h):
    cands = [os.path.join(d, logfile + ".log") for d in _LOG_DIRS]
    cands = [p for p in cands if os.path.exists(p)]
    if not cands:
        return {"ok": None, "last": None, "age_h": None, "note": "never run"}
    p = max(cands, key=os.path.getmtime)
    age_h = (datetime.now(timezone.utc).timestamp() - os.path.getmtime(p)) / 3600
    last = datetime.fromtimestamp(os.path.getmtime(p), tz=timezone.utc).isoformat()
    try:
        tail = "".join(open(p, encoding="utf-8", errors="ignore").readlines()[-30:])
    except Exception:
        tail = ""
    has = (marker in tail) if marker else True
    ok = has and (max_h is None or age_h <= max_h)
    note = "ok" if ok else ("stale — last run too old" if has else "last run failed / never succeeded")
    return {"ok": ok, "last": last, "age_h": round(age_h, 1), "note": note}


@app.get("/api/agents")
def api_agents():
    """Dead-man's switch data — the 7 launchd agents, last-run + green/red status. Read-only
    except the backup run-now trigger. Silent death is the enemy; this makes silence loud."""
    out = []
    for name, lf, mk, mh, run in _AGENTS:
        out.append({"name": name, "logfile": lf, "interval_h": mh, "runnable": run,
                    **_agent_status(lf, mk, mh)})
    down = [a["name"] for a in out if a["ok"] is False or a["ok"] is None]
    return {"agents": out, "down": down, "all_ok": not down}


@app.get("/api/queue_history")
def queue_history():
    """Daily review-queue-size snapshots (written by the morning brief) → the To-review
    burn-down trend, real once a week of history accumulates."""
    try:
        h = json.load(open(os.path.join(DATA, "queue_history.json"), encoding="utf-8"))
    except Exception:
        h = []
    return {"history": h}


def _cat_meta():
    return _yaml_load("category_meta.yaml")


def _cat_targets():
    return _yaml_load("category_targets.yaml")


# Budget periodicity (addendum A). Stored per target as {amount, period[, days]}.
# Back-compat: a bare number means a monthly amount. Everything the UI compares
# is month-scoped, so we also expose a monthly-equivalent for the circle/bar fill
# while the label keeps the real period honest.
_PERIOD_DAYS = {"weekly": 7.0, "biweekly": 14.0, "monthly": 30.437,
                "quarterly": 91.31, "yearly": 365.25,
                "hijri": 29.53}   # B8: a Hijri (lunar) month — for Ramadan/seasonal budgeting


def _target_norm(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return {"amount": round(float(v), 2), "period": "monthly"}
    if isinstance(v, dict) and v.get("amount") not in (None, "", 0, "0"):
        period = v.get("period") or "monthly"
        d = {"amount": round(float(v["amount"]), 2), "period": period}
        if period == "custom":
            d["days"] = float(v.get("days") or 30.437)
        return d
    return None


def _target_of(name):
    return _target_norm(_cat_targets().get(name))


def _target_monthly(t):
    """Monthly-equivalent amount for a periodic target (for month-scoped fills)."""
    if not t:
        return None
    days = t.get("days") if t.get("period") == "custom" else _PERIOD_DAYS.get(t.get("period"), 30.437)
    return round(t["amount"] * 30.437 / float(days or 30.437), 2)


def _cat_id(name):
    for c in ff_all("categories"):
        if (c["attributes"].get("name") or "") == name:
            return c["id"]
    return None


@app.post("/api/category/meta")
async def category_meta(req: Request):
    p = await req.json()
    name = (p.get("name") or "").strip()
    if not name:
        return {"ok": False, "error": "name required"}
    m = _cat_meta()
    e = dict(m.get(name) or {})
    if p.get("icon"):
        e["icon"] = p["icon"]
    if p.get("color"):
        e["color"] = p["color"]
    if "flex" in p:                                    # fixed | flexible | '' (unset)
        v = (p.get("flex") or "").strip()
        if v in ("fixed", "flexible"):
            e["flex"] = v
        else:
            e.pop("flex", None)
    if "rollover" in p:                                # Z4 strictness: carry (default) | strict
        v = (p.get("rollover") or "").strip()
        if v == "strict":
            e["rollover"] = "strict"
        else:
            e.pop("rollover", None)
    m[name] = e
    _yaml_save("category_meta.yaml", m)
    audit("category_meta", name=name, **e)
    return {"ok": True}


@app.post("/api/category/target")
async def category_target(req: Request):
    p = await req.json()
    name = (p.get("name") or "").strip()
    if not name:
        return {"ok": False, "error": "name required"}
    t = _cat_targets()
    amt = p.get("amount")
    if amt in (None, "", 0, "0") and not p.get("envelope"):
        t.pop(name, None)
    else:
        period = (p.get("period") or "monthly").strip()
        if period not in _PERIOD_DAYS and period != "custom":
            period = "monthly"
        entry = {"amount": round(float(amt or 0), 2), "period": period}
        if period == "custom":
            entry["days"] = float(p.get("days") or 30.437)
        # Envelope fields (arithmetic budgeting — Part A). amount = monthly contribution.
        if p.get("envelope"):
            entry["envelope"] = True
            entry["start"] = (p.get("start") or _date.today().isoformat())[:10]
            if p.get("link_account"):
                entry["link_account"] = str(p["link_account"])
            if p.get("goal") not in (None, "", 0, "0"):        # sinking-fund: due-dated goal
                entry["goal"] = round(float(p["goal"]), 2)
                entry["due"] = (p.get("due") or "")[:10]
            if p.get("paused") is not None:                    # Hisham-set self-note only
                entry["paused"] = bool(p["paused"])
        t[name] = entry
    _yaml_save("category_targets.yaml", t)
    audit("category_target", name=name, amount=amt, envelope=bool(p.get("envelope")))
    return {"ok": True}


# ── Envelope budgeting (Part A — arithmetic only; coaching stays gated) ─────
# An envelope is a pot: monthly contribution accumulates from a start date; category
# spending draws it down; the balance IS the permission. available = Σcontributions −
# Σspending. Negative is allowed and shown honestly (rose) with a pure-math recovery
# countdown. NO proposing sizes, NO "stop spending", NO safe-to-spend — that's the
# Budget engine, gated on surplus data. This is a calculator with a calendar.
def _months_incl(a_iso, b_iso):
    """Whole calendar months from a to b, inclusive of both endpoints (min 1 if a<=b)."""
    ya, ma = int(a_iso[:4]), int(a_iso[5:7])
    yb, mb = int(b_iso[:4]), int(b_iso[5:7])
    return (yb - ya) * 12 + (mb - ma) + 1


def _month_add(ym, n):
    y, m = int(ym[:4]), int(ym[5:7])
    z = (m - 1) + n
    return f"{y + z // 12:04d}-{z % 12 + 1:02d}"


_MONTH_NAMES = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _month_label(ym):
    return f"{_MONTH_NAMES[int(ym[5:7])]} {ym[:4]}"


def _acct_balance_by_id(aid):
    for a in ff_all("accounts", type="asset"):
        if a["id"] == str(aid):
            return round(float(a["attributes"].get("current_balance") or 0), 2)
    return None


def _envelope_state(name, t, txns):
    """Full envelope arithmetic for category `name` with target `t`. None if not an envelope."""
    if not (t and t.get("envelope")):
        return None
    today = _date.today().isoformat()
    ym = today[:7]
    # Z4 strictness: a STRICT envelope resets every month (no carry-over) — the window is just this
    # month; a CARRY envelope (default) accumulates from its start date.
    strict = (_cat_meta().get(name) or {}).get("rollover") == "strict"
    start = (ym + "-01") if strict else (t.get("start") or (today[:4] + "-01-01"))[:10]
    contrib = round(float(t.get("amount") or 0), 2)
    months = 1 if strict else max(1, _months_incl(start, today))
    spent = round(sum(x["amount"] for x in txns
                      if x["type"] == "withdrawal" and _main_cat(x["category"]) == name
                      and (x["date"] or "") >= start), 2)
    accumulated = round(contrib * months, 2)
    available = round(accumulated - spent, 2)
    st = {"name": name, "kind": "envelope", "contrib": contrib, "start": start,
          "months": months, "accumulated": accumulated, "spent": spent,
          "available": available, "paused": bool(t.get("paused")),
          "rollover": "strict" if strict else "carry"}
    if available < 0 and contrib > 0:                    # recovery countdown (pure arithmetic)
        rec = int((-available + contrib - 0.01) // contrib)   # ceil(|available|/contrib)
        st["overdrawn"] = round(-available, 2)
        st["recovery_months"] = rec
        st["recovery_label"] = _month_label(_month_add(ym, rec))
    elif available < 0:
        st["overdrawn"] = round(-available, 2)
    if t.get("goal") and t.get("due"):                   # sinking fund: due-dated goal
        st["kind"] = "sinking"
        st["goal"] = round(float(t["goal"]), 2)
        st["due"] = t["due"]
        ml = max(1, _months_incl(ym + "-01", t["due"]))
        st["months_left"] = ml
        st["required_monthly"] = round(max(0.0, st["goal"] - available) / ml, 2)
    if t.get("link_account"):                            # optional real-account reconciliation
        st["link_account"] = str(t["link_account"])
        bal = _acct_balance_by_id(t["link_account"])
        if bal is not None:
            st["account_balance"] = bal
            st["drift"] = round(bal - available, 2)      # flag, never auto-fix
    return st


@app.get("/api/category/averages")
def api_category_averages(name: str):
    """Recent monthly spend for a category → last / 3-mo avg / 6-mo avg for the 'set from history'
    buttons. Offers a window only if the ledger actually has that many complete months (honest)."""
    today = _date.today()
    months = []
    y, m = today.year, today.month
    for i in range(1, 7):
        mm, yy = m - i, y
        while mm <= 0:
            mm += 12
            yy -= 1
        months.append(f"{yy:04d}-{mm:02d}")           # newest-first, excludes current partial month
    spend = {mn: 0.0 for mn in months}
    dates = []
    for t in all_txns():
        d = t.get("date") or ""
        if d:
            dates.append(d)
        if t["type"] == "withdrawal" and _main_cat(t["category"]) == name and d[:7] in spend:
            spend[d[:7]] += t["amount"]
    vals = [round(spend[mn], 2) for mn in months]
    hist = 0
    if dates:
        first = min(dates)[:7]
        hist = (today.year - int(first[:4])) * 12 + (today.month - int(first[5:7]))

    def avg(n):
        return round(sum(vals[:n]) / n, 2) if hist >= n else None
    return {"name": name, "last": vals[0] if hist >= 1 else None,
            "avg3": avg(3), "avg6": avg(6), "hist_months": hist}


@app.get("/api/envelopes")
def api_envelopes():
    """All envelope states (arithmetic budgeting). Read-only."""
    targets = _cat_targets()
    txns = all_txns()
    out = []
    for name, raw in targets.items():
        # raw may be a bare-number legacy target — envelopes are always dicts
        if isinstance(raw, dict) and raw.get("envelope"):
            st = _envelope_state(name, raw, txns)
            if st:
                out.append(st)
    out.sort(key=lambda s: s["available"])
    return {"envelopes": out, "count": len(out),
            "overdrawn": sum(1 for s in out if s["available"] < 0)}


@app.post("/api/category/add")
async def category_add(req: Request):
    """Add a top-level category. ATOMIC and idempotent: creates the Firefly category (if new)
    AND registers it in our tree under expense|income in one call — no fragile client-side
    seed-dance (that two-step could half-fail and leave a category in Firefly but not the tree,
    the exact 'drift' that made the Manage add look broken). One owner for both add doors."""
    p = await req.json()
    name = (p.get("name") or "").strip()
    role = (p.get("role") or "expense").strip()
    if role not in ("expense", "income"):
        role = "expense"
    if not name:
        return {"ok": False, "error": "name required"}
    # create in Firefly if it doesn't exist yet (idempotent — a lazily-created cat is fine)
    if not _cat_id(name):
        ff("POST", "categories", {"name": name})
    # register in our tree so it shows immediately (Money Pro doctrine: every category visible)
    t = tree()
    t.setdefault(role, {}).setdefault(name, [])
    _tree_save(t)
    audit("category_add", name=name, role=role)
    return {"ok": True, "name": name, "role": role}


@app.post("/api/category/rename")
async def category_rename(req: Request):
    p = await req.json()
    old, new = (p.get("old") or "").strip(), (p.get("new") or "").strip()
    if not old or not new:
        return {"ok": False, "error": "old and new required"}
    cid = _cat_id(old)
    in_tree = _cat_in_tree(old)
    if not cid and not in_tree:
        return {"ok": False, "error": "category not found"}
    if cid:
        ff("PUT", f"categories/{cid}", {"name": new})    # Firefly (moves real transactions)
    _tree_rename(old, new)                                # keep the tree key in sync
    # carry over local meta/target
    for fn, load in (("category_meta.yaml", _cat_meta), ("category_targets.yaml", _cat_targets)):
        d = load()
        if old in d:
            d[new] = d.pop(old)
            _yaml_save(fn, d)
    audit("category_rename", old=old, new=new)
    return {"ok": True}


@app.post("/api/category/delete")
async def category_delete(req: Request):
    p = await req.json()
    name = (p.get("name") or "").strip()
    cid = _cat_id(name)                       # Firefly store
    in_tree = _cat_in_tree(name)              # our tree store
    if not cid and not in_tree:               # truly gone from both — only now is "not found" honest
        return {"ok": False, "error": "category not found"}
    # count affected first (honest — transactions become uncategorized, never deleted)
    n = sum(1 for t in all_txns() if (t.get("category") or "").split(":")[0].strip() == name)
    if n and not p.get("confirm"):
        return {"ok": False, "needs_confirm": True, "count": n}
    if cid:
        ff("DELETE", f"categories/{cid}")     # remove from Firefly (if it materialised there)
    _tree_remove(name)                        # remove from the tree (both roles)
    for fn, load in (("category_meta.yaml", _cat_meta), ("category_targets.yaml", _cat_targets)):
        d = load()
        if name in d:
            d.pop(name, None)
            _yaml_save(fn, d)
    audit("category_delete", name=name, uncategorized=n, was_ff=bool(cid), was_tree=in_tree)
    return {"ok": True, "uncategorized": n}


@app.post("/api/category/merge")
async def category_merge(req: Request):
    p = await req.json()
    src, dst = (p.get("from") or "").strip(), (p.get("into") or "").strip()
    if not src or not dst or src == dst:
        return {"ok": False, "error": "pick two different categories"}
    rows = [t for t in all_txns() if (t.get("category") or "").split(":")[0].strip() == src]
    if not p.get("confirm"):
        return {"ok": False, "needs_confirm": True, "count": len(rows), "from": src, "into": dst}
    moved = 0
    for t in rows:
        try:
            full = ff("GET", f"transactions/{t['id']}")
            s = full["data"]["attributes"]["transactions"][0]
            ff("PUT", f"transactions/{t['id']}", {"transactions": [{
                "transaction_journal_id": s["transaction_journal_id"], "category_name": dst}]})
            moved += 1
        except Exception as e:
            print("merge move fail", e, flush=True)
    cid = _cat_id(src)
    if cid:
        ff("DELETE", f"categories/{cid}")
    _tree_remove(src)                       # was leaking an orphaned tree entry after merge
    # ensure the destination exists in the tree (so a merge into a fresh name still shows)
    if not _cat_in_tree(dst):
        t = tree()
        t.setdefault("expense", {}).setdefault(dst, [])
        _tree_save(t)
    for fn, load in (("category_meta.yaml", _cat_meta), ("category_targets.yaml", _cat_targets)):
        d = load()
        if src in d:
            d.pop(src, None)
            _yaml_save(fn, d)
    audit("category_merge", **{"from": src, "into": dst, "moved": moved})
    return {"ok": True, "moved": moved}


# ---- subcategory hierarchy (item 3). The tree (category_tree.yaml) is OURS — the
# presentation hierarchy. Firefly stays flat truth; a sub only becomes a real Firefly
# category ("Parent: Sub") when first used. Reparent/rename move real transactions by
# renaming (or merging) that flat Firefly category so one-owner-per-resource holds. ----
def _tree_save(data):
    with _lock:
        with open(TREE_PATH, "w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)


# ── Two-store sync (the category lives in Firefly AND our tree). Every verb that touches a
# category must resolve through BOTH stores and keep them in sync — else a category can exist
# in one store and not the other, and lookups by the wrong id give a lying "not found"
# (the delete/rename bug of 10 Sep). Single source of truth for existence = "in either store". ──
def _cat_in_tree(name):
    t = tree()
    return any(name in (t.get(r) or {}) for r in ("expense", "income"))


def _tree_remove(name):
    t = tree()
    changed = False
    for r in ("expense", "income"):
        if name in (t.get(r) or {}):
            t[r].pop(name, None)
            changed = True
    if changed:
        _tree_save(t)
    return changed


def _tree_rename(old, new):
    t = tree()
    changed = False
    for r in ("expense", "income"):
        if old in (t.get(r) or {}):
            # preserve subs + position order
            t[r] = {(new if k == old else k): v for k, v in t[r].items()}
            changed = True
    if changed:
        _tree_save(t)
    return changed


def _move_ff_category(old, new):
    """Rename flat Firefly category old->new; if new already exists, merge (retag
    transactions then delete old). Returns count moved (0 if old never materialised)."""
    oid = _cat_id(old)
    if not oid:
        return 0
    nid = _cat_id(new)
    if not nid:
        ff("PUT", f"categories/{oid}", {"name": new})
        return 1
    moved = 0
    for t in all_txns():
        if (t.get("category") or "") == old:
            try:
                full = ff("GET", f"transactions/{t['id']}")
                s = full["data"]["attributes"]["transactions"][0]
                ff("PUT", f"transactions/{t['id']}", {"transactions": [{
                    "transaction_journal_id": s["transaction_journal_id"], "category_name": new}]})
                moved += 1
            except Exception as e:
                print("reparent move fail", e, flush=True)
    ff("DELETE", f"categories/{oid}")
    return moved


@app.post("/api/tree/sub_add")
async def tree_sub_add(req: Request):
    p = await req.json()
    role = p.get("role", "expense")
    parent, sub = (p.get("parent") or "").strip(), (p.get("sub") or "").strip()
    if not parent or not sub:
        return {"ok": False, "error": "parent and sub required"}
    t = tree()
    lst = t.setdefault(role, {}).setdefault(parent, [])
    if sub in lst:
        return {"ok": False, "error": "sub already exists"}
    lst.append(sub)
    _tree_save(t)
    audit("tree_sub_add", parent=parent, sub=sub, role=role)
    return {"ok": True}


@app.post("/api/tree/sub_delete")
async def tree_sub_delete(req: Request):
    p = await req.json()
    role = p.get("role", "expense")
    parent, sub = (p.get("parent") or "").strip(), (p.get("sub") or "").strip()
    t = tree()
    lst = (t.get(role) or {}).get(parent, [])
    if sub in lst:
        lst.remove(sub)
        _tree_save(t)
    # We never delete Firefly data here — any real "Parent: Sub" transactions simply
    # keep their flat category; the sub just disappears from the picker hierarchy.
    audit("tree_sub_delete", parent=parent, sub=sub, role=role)
    return {"ok": True}


@app.post("/api/tree/sub_rename")
async def tree_sub_rename(req: Request):
    p = await req.json()
    role = p.get("role", "expense")
    parent = (p.get("parent") or "").strip()
    old, new = (p.get("old") or "").strip(), (p.get("new") or "").strip()
    if not new or old == new:
        return {"ok": False, "error": "new name required"}
    t = tree()
    lst = t.setdefault(role, {}).setdefault(parent, [])
    if old in lst:
        lst[lst.index(old)] = new
    elif new not in lst:
        lst.append(new)
    _tree_save(t)
    moved = _move_ff_category(f"{parent}: {old}", f"{parent}: {new}")
    audit("tree_sub_rename", parent=parent, old=old, new=new, moved=moved)
    return {"ok": True, "moved": moved}


@app.post("/api/tree/reparent")
async def tree_reparent(req: Request):
    p = await req.json()
    role = p.get("role", "expense")
    sub = (p.get("sub") or "").strip()
    frm, to = (p.get("from") or "").strip(), (p.get("to") or "").strip()
    if not sub or not to or frm == to:
        return {"ok": False, "error": "sub, from and to required"}
    t = tree()
    sec = t.setdefault(role, {})
    if sub in sec.get(frm, []):
        sec[frm].remove(sub)
    lst = sec.setdefault(to, [])
    if sub not in lst:
        lst.append(sub)
    _tree_save(t)
    moved = _move_ff_category(f"{frm}: {sub}", f"{to}: {sub}")
    audit("tree_reparent", sub=sub, moved=moved, **{"from": frm, "to": to, "role": role})
    return {"ok": True, "moved": moved}


# ---- custom category icons (item 4). Stored under DATA (the mounted, writable volume)
# — NOT the baked image assets — so uploads persist across rebuilds. Client crops to a
# circle on a canvas and posts a PNG data-URL. ----
@app.post("/api/category/icon")
async def category_icon(req: Request):
    import base64
    p = await req.json()
    name = (p.get("name") or "").strip()
    if not name:
        return {"ok": False, "error": "name required"}
    m = _cat_meta()
    e = dict(m.get(name) or {})
    if p.get("clear"):
        e.pop("custom_icon", None)
        m[name] = e
        _yaml_save("category_meta.yaml", m)
        audit("category_icon_clear", name=name)
        return {"ok": True}
    data_url = p.get("data") or ""
    if not data_url.startswith("data:image"):
        return {"ok": False, "error": "image data required"}
    try:
        raw = base64.b64decode(data_url.split(",", 1)[1])
    except Exception:
        return {"ok": False, "error": "bad image data"}
    if len(raw) > 2_000_000:
        return {"ok": False, "error": "image too large (max ~2MB after crop)"}
    icons_dir = os.path.join(DATA, "category-icons")
    os.makedirs(icons_dir, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "cat"
    fn = f"{slug}.png"
    with open(os.path.join(icons_dir, fn), "wb") as fh:
        fh.write(raw)
    e["custom_icon"] = fn
    m[name] = e
    _yaml_save("category_meta.yaml", m)
    audit("category_icon", name=name, file=fn, bytes=len(raw))
    return {"ok": True, "file": fn}


@app.get("/data/category-icons/{fn}")
def category_icon_file(fn: str):
    safe = os.path.basename(fn)
    path = os.path.join(DATA, "category-icons", safe)
    if not os.path.exists(path):
        return JSONResponse({"error": "not found"}, 404)
    return FileResponse(path, headers={"Cache-Control": "max-age=86400"})


# ==================== REPORTS (item 7) ====================
# A Money Pro-style report builder over the live ledger — READ-ONLY. Every report type
# except Projected Balance (forecasting, blocked). CSV/PDF/QIF export + saved configs.
REPORT_TYPES = {"income_expense": "Income & Expenses", "net_worth": "Net Worth",
                "cash_flow": "Cash Flow", "debt": "Debt Balance",
                "assets_liabilities": "Assets & Liabilities",
                "transactions": "Transactions", "by_person": "By Person"}


def _report_filter(txns, p):
    frm, to = p.get("from") or "", p.get("to") or ""
    accts = {a for a in (p.get("accounts") or "").split("|") if a.strip()}
    cats = {c for c in (p.get("categories") or "").split("|") if c.strip()}
    ttype = p.get("txn_type") or "all"
    person = (p.get("person") or "").strip()
    klass = (p.get("klass") or "").strip()
    out = []
    for t in txns:
        d = t.get("date") or ""
        if frm and d < frm:
            continue
        if to and d > to:
            continue
        if ttype != "all" and t["type"] != ttype:
            continue
        if accts and not ({t.get("source"), t.get("destination")} & accts):
            continue
        if cats and _main_cat(t["category"]) not in cats:
            continue
        if person and person not in (t.get("tags") or []):
            continue
        if klass and f"class:{klass}" not in (t.get("tags") or []):
            continue
        out.append(t)
    return out


def _group_key(t, gb):
    if gb == "account":
        return t.get("account") or "—"
    if gb == "person":
        for tag in (t.get("tags") or []):
            if tag in PERSON_TAGS:
                return tag
        return "Untagged"
    if gb == "class":
        for tag in (t.get("tags") or []):
            if tag.startswith("class:"):
                return tag.split(":", 1)[1]
        return "Unclassified"
    if gb == "month":
        return (t.get("date") or "")[:7]
    return _main_cat(t["category"]) or "Uncategorized"


def _sar_fn():
    fx = fx_rates() or {}
    return lambda amt, cur: float(amt) * (1 if cur == "SAR" else (fx.get(cur) or 1))


def _balance_accounts():
    """(list of {name,role,type,bal_sar,cur,group,ids}, sar_fn)."""
    sar = _sar_fn()
    out = []
    for a in ff_all("accounts"):
        at = a["attributes"]
        if at.get("type") not in ("asset", "liability"):
            continue
        bal = float(at.get("current_balance") or 0)
        cur = at.get("currency_code") or "SAR"
        out.append({"id": a["id"], "name": at.get("name") or "", "role": at.get("account_role"),
                    "type": at["type"], "bal": bal, "sar": sar(bal, cur), "cur": cur,
                    "group": _group(at.get("name") or "", at.get("account_role"))})
    return out


def compute_report(p):
    rtype = p.get("type", "income_expense")
    gb = p.get("group_by", "category")
    txns = all_txns()
    frm, to = p.get("from") or "", p.get("to") or ""

    # ---- balance-based reports ----
    if rtype in ("net_worth", "debt"):
        accs = _balance_accounts()
        if rtype == "debt":
            ids = {a["id"] for a in accs if a["role"] == "ccAsset" or a["type"] == "liability"}
            now = -round(sum(a["sar"] for a in accs if a["id"] in ids), 2)
            groups = sorted(({"label": a["name"], "value": round(-a["sar"], 2)}
                             for a in accs if a["id"] in ids and abs(a["sar"]) > 0.001),
                            key=lambda x: -x["value"])
            unit = "debt"
        else:
            ids = {a["id"] for a in accs}
            now = round(sum(a["sar"] for a in accs), 2)
            groups = sorted(({"label": a["name"], "value": round(a["sar"], 2)}
                             for a in accs if abs(a["sar"]) > 0.001), key=lambda x: -x["value"])
            unit = "net worth"
        sar = _sar_fn()

        def delta(t):
            d = 0.0
            if t.get("source_id") in ids:
                d -= sar(t["amount"], t.get("currency") or "SAR")
            if t.get("destination_id") in ids:
                d += sar(t["amount"], t.get("currency") or "SAR")
            return d
        flows = sorted(((t["date"], delta(t)) for t in txns if t.get("date")), key=lambda x: x[0])

        def val_at(dstr):
            tot = now - sum(x for dd, x in flows if dd > dstr)
            return round(-tot if rtype == "debt" else tot, 2)
        months = sorted({(t["date"] or "")[:7] for t in txns if t.get("date")})
        series = []
        for mo in months:
            last = mo + "-31"
            if frm and last < frm:
                continue
            if to and (mo + "-01") > to:
                continue
            series.append({"x": mo, "label": mo, "value": val_at(last)})
        series.append({"x": "now", "label": "now", "value": round(now, 2)})
        return {"type": rtype, "group_by": gb, "range": {"from": frm, "to": to},
                "groups": groups, "series": series, "rows": [],
                "totals": {"current": round(now, 2), "unit": unit, "count": len(groups)}}

    if rtype == "assets_liabilities":
        accs = _balance_accounts()
        gmap = {}
        for a in accs:
            g = gmap.setdefault(a["group"], {"label": a["group"], "value": 0.0, "items": []})
            g["value"] += a["sar"]
            g["items"].append({"name": a["name"], "value": round(a["sar"], 2), "cur": a["cur"]})
        groups = [{"label": k, "value": round(v["value"], 2), "items": v["items"]}
                  for k, v in gmap.items()]
        groups.sort(key=lambda x: -x["value"])
        assets = round(sum(a["sar"] for a in accs if a["sar"] > 0), 2)
        liabs = round(sum(a["sar"] for a in accs if a["sar"] < 0), 2)
        rows = [{"date": "", "desc": a["name"], "account": a["group"],
                 "category": a["type"], "type": a["type"],
                 "amount": round(a["sar"], 2)} for a in sorted(accs, key=lambda x: -x["sar"])]
        return {"type": rtype, "group_by": "group", "range": {"from": frm, "to": to},
                "groups": groups, "series": [], "rows": rows,
                "totals": {"assets": assets, "liabilities": liabs,
                           "net": round(assets + liabs, 2), "count": len(accs)}}

    # ---- riba & fees: the cost-of-debt lens (real financing-cost data from Wave M's flows) ----
    if rtype == "riba":
        def _is_cost(t):
            c = (t.get("category") or "").lower()
            return t["type"] == "withdrawal" and any(
                k in c for k in ("financing cost", "interest", "riba", "فائدة", "مرابحة", "late fee"))
        cost = [t for t in txns if _is_cost(t)]
        if frm:
            cost = [t for t in cost if (t.get("date") or "") >= frm]
        if to:
            cost = [t for t in cost if (t.get("date") or "") <= to]
        # per-card / per-loan breakdown (the source account carrying the cost)
        gmap = {}
        for t in cost:
            k = t.get("account") or "—"
            e = gmap.setdefault(k, {"label": k, "value": 0.0, "count": 0})
            e["value"] += t["amount"]
            e["count"] += 1
        groups = sorted(({"label": e["label"], "value": round(e["value"], 2), "count": e["count"]}
                         for e in gmap.values()), key=lambda x: -x["value"])
        # monthly trend
        mo_map = {}
        for t in cost:
            k = (t.get("date") or "")[:7]
            mo_map[k] = mo_map.get(k, 0.0) + t["amount"]
        series = [{"x": k, "label": k, "value": round(v, 2)} for k, v in sorted(mo_map.items())]
        total = round(sum(t["amount"] for t in cost), 2)
        months = len(mo_map) or 1
        return {"type": rtype, "group_by": "account", "range": {"from": frm, "to": to},
                "groups": groups, "series": series, "rows": _report_rows(cost),
                "totals": {"cost": total, "unit": "cost of debt", "count": len(cost),
                           "avg_month": round(total / months, 2), "months": months}}

    # ---- flow-based reports ----
    rows = _report_filter(txns, p)
    income = round(sum(t["amount"] for t in rows if t["type"] == "deposit"), 2)
    expense = round(sum(t["amount"] for t in rows if t["type"] == "withdrawal"), 2)
    totals = {"income": income, "expense": expense, "net": round(income - expense, 2),
              "count": len(rows)}

    if rtype == "sankey":
        # Ribbon flow: income sources → the pool → expense categories → (Saved | drawn from reserves).
        # Honest by construction — the diagram conserves flow: sum(left) == sum(right) == max(in,out).
        inc_map, exp_map = {}, {}
        for t in rows:
            if t["type"] == "deposit":
                k = _main_cat(t["category"]) or "Other income"
                inc_map[k] = inc_map.get(k, 0.0) + t["amount"]
            elif t["type"] == "withdrawal":
                k = _main_cat(t["category"]) or "Uncategorized"
                exp_map[k] = exp_map.get(k, 0.0) + t["amount"]
        inc_src = sorted(({"label": k, "value": round(v, 2)} for k, v in inc_map.items()),
                         key=lambda x: -x["value"])
        exp_cat = sorted(({"label": k, "value": round(v, 2)} for k, v in exp_map.items()),
                         key=lambda x: -x["value"])
        return {"type": rtype, "group_by": "category", "range": {"from": frm, "to": to},
                "income_src": inc_src, "expense_cat": exp_cat, "groups": [], "series": [],
                "rows": _report_rows(rows), "totals": totals}

    if rtype == "cash_flow":
        mo_map = {}
        for t in rows:
            k = (t["date"] or "")[:7]
            e = mo_map.setdefault(k, {"in": 0.0, "out": 0.0})
            if t["type"] == "deposit":
                e["in"] += t["amount"]
            elif t["type"] == "withdrawal":
                e["out"] += t["amount"]
        series = [{"x": k, "label": k, "in": round(v["in"], 2), "out": round(v["out"], 2),
                   "value": round(v["in"] - v["out"], 2)} for k, v in sorted(mo_map.items())]
        # M: planned line — monthly-equivalent budget targets (income − expense)
        kinds = _cat_kinds()
        pin = pout = 0.0
        for kk, vv in _cat_targets().items():
            tm = _target_monthly(_target_norm(vv)) or 0
            if kinds.get(_main_cat(kk)) == "inc":
                pin += tm
            else:
                pout += tm
        planned_net = round(pin - pout, 2)
        for s in series:
            s["planned"] = planned_net
        groups = [{"label": s["label"], "value": s["value"], "income": s["in"],
                   "expense": s["out"]} for s in series]
        return {"type": rtype, "group_by": "month", "range": {"from": frm, "to": to},
                "groups": groups, "series": series, "rows": _report_rows(rows),
                "planned_net": planned_net, "totals": totals}

    if rtype == "transactions":
        return {"type": rtype, "group_by": gb, "range": {"from": frm, "to": to},
                "groups": [], "series": [], "rows": _report_rows(rows), "totals": totals}

    # income_expense / by_person → grouped
    if rtype == "by_person":
        gb = "person"
    gmap = {}
    for t in rows:
        k = _group_key(t, gb)
        e = gmap.setdefault(k, {"label": k, "income": 0.0, "expense": 0.0, "count": 0})
        if t["type"] == "deposit":
            e["income"] += t["amount"]
        elif t["type"] == "withdrawal":
            e["expense"] += t["amount"]
        e["count"] += 1
    groups = []
    for e in gmap.values():
        e["income"] = round(e["income"], 2)
        e["expense"] = round(e["expense"], 2)
        e["net"] = round(e["income"] - e["expense"], 2)
        e["value"] = e["expense"] if e["expense"] >= e["income"] else e["income"]
        groups.append(e)
    groups.sort(key=lambda x: -(x["expense"] or x["income"]))
    return {"type": rtype, "group_by": gb, "range": {"from": frm, "to": to},
            "groups": groups, "series": [], "rows": _report_rows(rows), "totals": totals}


def _report_rows(rows):
    out = []
    for t in sorted(rows, key=lambda x: x.get("date") or "", reverse=True):
        klass = next((tg.split(":", 1)[1] for tg in (t.get("tags") or [])
                      if tg.startswith("class:")), "")
        person = next((tg for tg in (t.get("tags") or []) if tg in PERSON_TAGS), "")
        out.append({"date": t["date"], "desc": merchant_display(t["desc"]),
                    "account": t.get("account") or "", "category": t["category"] or "",
                    "type": t["type"], "amount": t["signed"], "person": person,
                    "klass": klass, "reconciled": "reconciled" in (t.get("tags") or [])})
    return out


@app.get("/api/report")
def api_report(request: Request):
    return compute_report(dict(request.query_params))


# ---- export: CSV / QIF / PDF (reuse the exports engine's spirit) ----
def _pdf_escape(s):
    return "".join(c if 32 <= ord(c) < 127 else "?" for c in str(s)).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_pdf(title, lines):
    content = "BT\n/F1 16 Tf 1 0 0 1 50 780 Tm 20 TL\n(" + _pdf_escape(title) + ") Tj\n"
    content += "/F1 10 Tf 0 -28 TD\n"
    for text, size in lines:
        content += f"/F1 {size} Tf ({_pdf_escape(text)}) Tj 0 -{size+6} TD\n"
    content += "ET"
    cb = content.encode("latin-1", "replace")
    objs = ["<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
            f"<< /Length {len(cb)} >>\nstream\n".encode() + cb + b"\nendstream",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out = b"%PDF-1.4\n"
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        ob = o if isinstance(o, bytes) else o.encode()
        out += f"{i} 0 obj\n".encode() + ob + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out


@app.get("/api/report/export")
def api_report_export(request: Request):
    from fastapi.responses import Response
    import csv as _csv
    import io
    p = dict(request.query_params)
    fmt = (p.get("fmt") or "csv").lower()
    rep = compute_report(p)
    name = REPORT_TYPES.get(rep["type"], rep["type"])
    rng = rep["range"]
    stamp = f"{rng.get('from') or 'start'}_{rng.get('to') or 'now'}"
    base = f"hakim-report-{rep['type']}-{stamp}"
    if fmt == "qif":
        # QIF only makes sense for transaction rows
        lines = ["!Type:Bank"]
        for r in rep.get("rows", []):
            if not r.get("date"):
                continue
            lines += [f"D{r['date']}", f"T{r['amount']:.2f}",
                      f"P{r['desc']}", f"L{r['category']}", "^"]
        data = "\n".join(lines) + "\n"
        return Response(data, media_type="application/qif",
                        headers={"Content-Disposition": f'attachment; filename="{base}.qif"'})
    if fmt == "pdf":
        lines = [(f"{name}  ·  {rng.get('from') or 'start'} → {rng.get('to') or 'now'}", 11), ("", 6)]
        tot = rep["totals"]
        if "income" in tot:
            lines += [(f"Income:  SAR {tot['income']:,.2f}", 11),
                      (f"Expense: SAR {tot['expense']:,.2f}", 11),
                      (f"Net:     SAR {tot['net']:,.2f}", 11), ("", 6)]
        elif "current" in tot:
            lines += [(f"{tot['unit'].title()}: SAR {tot['current']:,.2f}", 11), ("", 6)]
        elif "assets" in tot:
            lines += [(f"Assets:      SAR {tot['assets']:,.2f}", 11),
                      (f"Liabilities: SAR {tot['liabilities']:,.2f}", 11),
                      (f"Net worth:   SAR {tot['net']:,.2f}", 11), ("", 6)]
        for g in rep.get("groups", [])[:28]:
            v = g.get("net", g.get("value", 0))
            lines.append((f"{g['label'][:40]:<42} SAR {v:,.2f}", 10))
        lines += [("", 8), ("Read-only export. HAKIM Finance — personal ledger only.", 9)]
        return Response(_build_pdf(name, lines), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{base}.pdf"'})
    # CSV (default)
    buf = io.StringIO()
    w = _csv.writer(buf)
    if rep.get("rows"):
        w.writerow(["date", "description", "account", "category", "type", "amount", "person", "class", "reconciled"])
        for r in rep["rows"]:
            w.writerow([r["date"], r["desc"], r["account"], r["category"], r["type"],
                        f"{r['amount']:.2f}", r.get("person", ""), r.get("klass", ""),
                        "yes" if r.get("reconciled") else ""])
    else:
        w.writerow(["group", "income", "expense", "net", "value", "count"])
        for g in rep.get("groups", []):
            w.writerow([g["label"], g.get("income", ""), g.get("expense", ""),
                        g.get("net", ""), g.get("value", ""), g.get("count", "")])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{base}.csv"'})


# ---- saved reports ----
def _saved_reports():
    d = _yaml_load("saved_reports.yaml")
    return d.get("reports", []) if isinstance(d, dict) else []


@app.get("/api/reports/saved")
def reports_saved():
    return {"reports": _saved_reports()}


@app.post("/api/reports/save")
async def reports_save(req: Request):
    p = await req.json()
    name = (p.get("name") or "").strip()
    if not name:
        return {"ok": False, "error": "name required"}
    cfg = p.get("config") or {}
    reps = _saved_reports()
    rid = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "report"
    reps = [r for r in reps if r.get("id") != rid]
    reps.append({"id": rid, "name": name, "config": cfg})
    _yaml_save("saved_reports.yaml", {"reports": reps})
    audit("report_save", name=name, id=rid)
    return {"ok": True, "id": rid}


@app.post("/api/reports/delete")
async def reports_delete(req: Request):
    p = await req.json()
    rid = (p.get("id") or "").strip()
    reps = [r for r in _saved_reports() if r.get("id") != rid]
    _yaml_save("saved_reports.yaml", {"reports": reps})
    audit("report_delete", id=rid)
    return {"ok": True}


# ==================== GOALS (item E) ====================
# Simple goals: save toward X, or pay down card Y. Progress is computed from REAL
# live balances vs a baseline captured when the goal was created. No coaching, no
# projections (those stay blocked) — just an honest progress bar.
def _goals():
    d = _yaml_load("goals.yaml")
    return d.get("goals", []) if isinstance(d, dict) else []


def _goal_math(remaining, deadline):
    """Arithmetic only: months left to the deadline and the required per-month to close `remaining`.
    Returns (months_left, per_month) or (None, None) when there's no future deadline / nothing left."""
    if not deadline or remaining <= 0:
        return None, None
    import datetime as _dt
    try:
        y, m, d = (int(x) for x in deadline[:10].split("-"))
        days = (_dt.date(y, m, d) - _dt.date.today()).days
    except Exception:
        return None, None
    if days <= 0:
        return 0, None
    months = max(1, round(days / 30.44))
    return months, round(remaining / months, 2)


@app.get("/api/goals")
def goals_list():
    accs = {a["id"]: a for a in _balance_accounts()}
    out = []
    for g in _goals():
        a = accs.get(g.get("account_id"))
        bal = a["sar"] if a else 0.0
        base = float(g.get("baseline") or 0)
        target = float(g.get("target") or 0)
        # seasonal goals roll their deadline forward to the next occurrence every time we read them
        season = g.get("season")
        deadline = _season_date(season) if season else (g.get("deadline") or "")
        season_meta = _SEASONS.get(season)
        if g.get("kind") == "debt":
            cur_debt = round(-bal, 2)
            denom = base - target
            pct = 0 if denom <= 0 else max(0, min(100, round((base - cur_debt) / denom * 100)))
            remaining = round(max(0, cur_debt - target), 2)
            cur = cur_debt
        else:
            cur = round(bal, 2)
            denom = target - base
            pct = 0 if denom <= 0 else max(0, min(100, round((cur - base) / denom * 100)))
            remaining = round(max(0, target - cur), 2)
        months_left, per_month = _goal_math(remaining, deadline)
        milestone = max([m for m in (0, 25, 50, 75, 100) if pct >= m], default=0)
        out.append({**g, "current": cur, "remaining": remaining, "pct": pct,
                    "account_name": a["name"] if a else g.get("account_name", ""),
                    "deadline": deadline, "season": season,
                    "season_icon": season_meta[0] if season_meta else "",
                    "season_label": season_meta[1] if season_meta else "",
                    "months_left": months_left, "per_month": per_month, "milestone": milestone})
    return {"goals": out, "accounts": [{"id": a["id"], "name": a["name"], "sar": round(a["sar"], 2),
            "role": a["role"], "type": a["type"]} for a in _balance_accounts()]}


@app.post("/api/goal/add")
async def goal_add(req: Request):
    p = await req.json()
    name = (p.get("name") or "").strip()
    if not name:
        return {"ok": False, "error": "name required"}
    accs = {a["id"]: a for a in _balance_accounts()}
    aid = p.get("account_id")
    a = accs.get(aid)
    kind = p.get("kind") or "save"
    # Debt goals baseline = the debt when the goal is set (progress = amount paid since).
    # Save goals count existing balance toward the target, so baseline = 0 (or a chosen start).
    if kind == "debt":
        baseline = -a["sar"] if a else float(p.get("baseline") or 0)
    else:
        baseline = float(p.get("baseline") or 0)
    goals = _goals()
    gid = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "goal"
    goals = [x for x in goals if x.get("id") != gid]
    season = (p.get("season") or "").strip()
    if season not in _SEASONS:
        season = ""
    goals.append({"id": gid, "name": name, "kind": kind, "account_id": aid,
                  "account_name": a["name"] if a else "", "target": round(float(p.get("target") or 0), 2),
                  "deadline": p.get("deadline") or "", "baseline": round(baseline, 2),
                  "season": season})
    _yaml_save("goals.yaml", {"goals": goals})
    audit("goal_add", name=name, kind=kind, target=p.get("target"))
    return {"ok": True, "id": gid}


@app.post("/api/goal/delete")
async def goal_delete(req: Request):
    p = await req.json()
    gid = (p.get("id") or "").strip()
    _yaml_save("goals.yaml", {"goals": [x for x in _goals() if x.get("id") != gid]})
    audit("goal_delete", id=gid)
    return {"ok": True}


@app.get("/api/hijri/current")
def hijri_current():
    import datetime as _dt
    from hijri_converter import Gregorian, Hijri
    t = _dt.date.today()
    h = Gregorian(t.year, t.month, t.day).to_hijri()
    start = Hijri(h.year, h.month, 1).to_gregorian()
    ny, nm = (h.year + 1, 1) if h.month == 12 else (h.year, h.month + 1)
    nxt = Hijri(ny, nm, 1).to_gregorian()
    end = _dt.date(nxt.year, nxt.month, nxt.day) - _dt.timedelta(days=1)
    return {"from": f"{start.year:04d}-{start.month:02d}-{start.day:02d}",
            "to": end.isoformat(), "label": f"{_HIJRI_AR[h.month]} {h.year} هـ"}


# ---------------------------------------------------------------- WAVE H
# Islamic-calendar seasons (Umm al-Qura next-occurrence) — powers seasonal goal deadlines.
_SEASONS = {
    "ramadan":  ("🌙", "Ramadan",             ("hijri", 9, 1)),
    "eid_fitr": ("🎉", "Eid al-Fitr",          ("hijri", 10, 1)),
    "eid_adha": ("🕋", "Eid al-Adha · Hajj",   ("hijri", 12, 10)),
    "school":   ("🎒", "School start",         ("greg", 8, 24)),
}


def _season_date(key):
    """Gregorian date (iso) of the NEXT occurrence of a season, today or later. None if unknown."""
    spec = _SEASONS.get(key)
    if not spec:
        return None
    import datetime as _dt
    from hijri_converter import Gregorian, Hijri
    today = _dt.date.today()
    cal, m, d = spec[2]
    if cal == "hijri":
        hy = Gregorian(today.year, today.month, today.day).to_hijri().year
        for yy in (hy, hy + 1, hy + 2):
            g = Hijri(yy, m, d).to_gregorian()
            gd = _dt.date(g.year, g.month, g.day)
            if gd >= today:
                return gd.isoformat()
    else:
        for yy in (today.year, today.year + 1):
            gd = _dt.date(yy, m, d)
            if gd >= today:
                return gd.isoformat()
    return None


@app.get("/api/seasons")
def api_seasons():
    """Next occurrence of each Islamic-calendar / school season — for the goal date picker."""
    out = []
    for k, (icon, label, _spec) in _SEASONS.items():
        dt = _season_date(k)
        out.append({"key": k, "icon": icon, "label": label, "date": dt})
    return {"seasons": out}


# --- Owed-to-me ledger (per-person receivables layered over the 'Owed to me' asset account) ---
def _receivables():
    d = _yaml_load("receivables.yaml")
    return d.get("receivables", []) if isinstance(d, dict) else []


def _recv_save(rows):
    _yaml_save("receivables.yaml", {"receivables": rows})


def _owed_accounts():
    """Firefly asset accounts that hold money others owe Hisham (مستحقات / receivable)."""
    out = []
    for a in ff_all("accounts", type="asset"):
        at = a["attributes"]
        nl = (at.get("name") or "").lower()
        if any(x in nl for x in ("owed", "i owe", "مستحقات", "receivable")):
            out.append({"id": a["id"], "name": at.get("name") or "",
                        "bal": round(float(at.get("current_balance") or 0), 2),
                        "cur": at.get("currency_code") or "SAR"})
    return out


def _acct_bal(aid):
    """Live balance of one account (as-of-today) — for balance proofs. 0.0 on failure."""
    try:
        at = ff("GET", f"accounts/{aid}")["data"]["attributes"]
        return round(float(at.get("current_balance") or 0), 2)
    except Exception:
        return 0.0


def _recv_outstanding(r):
    return round(float(r.get("principal") or 0) - sum(float(x.get("amount") or 0)
                 for x in (r.get("repayments") or [])), 2)


@app.get("/api/receivables")
def api_receivables():
    """The owed-to-me ledger: per-person outstanding, aging, and the invariant check that the
    sum of what people owe matches the Firefly 'Owed to me' account balance."""
    import datetime as _dt
    today = _dt.date.today()
    owed = _owed_accounts()
    accs = [a for a in _balance_accounts()
            if a["type"] == "asset" and a["role"] != "ccAsset"]
    rows = []
    total_out = 0.0
    for r in _receivables():
        out = _recv_outstanding(r)
        total_out += out
        age_days = None
        if r.get("date_lent"):
            try:
                y, m, d = (int(x) for x in r["date_lent"].split("-"))
                age_days = (today - _dt.date(y, m, d)).days
            except Exception:
                pass
        rows.append({**r, "origin": r.get("origin") or "loan", "outstanding": out,
                     "settled": out <= 0.009, "age_days": age_days,
                     "repaid": round(sum(float(x.get("amount") or 0)
                     for x in (r.get("repayments") or [])), 2)})
    rows.sort(key=lambda x: (x["settled"], -(x["outstanding"])))
    # per-person roll-up with origin breakdown ("Noura: 300 — qattah 250 · loan 50")
    people = {}
    for r in rows:
        e = people.setdefault(r["person"], {"person": r["person"], "outstanding": 0.0,
                                            "by_origin": {}, "count": 0})
        e["outstanding"] = round(e["outstanding"] + r["outstanding"], 2)
        e["by_origin"][r["origin"]] = round(e["by_origin"].get(r["origin"], 0.0) + r["outstanding"], 2)
        e["count"] += 1
    by_person = sorted(people.values(), key=lambda x: -x["outstanding"])
    owed_bal = round(sum(a["bal"] for a in owed), 2)
    qattah_total = round(sum(r["outstanding"] for r in rows if r["origin"] == "qattah"), 2)
    return {"receivables": rows, "owed_accounts": owed, "by_person": by_person,
            "total_outstanding": round(total_out, 2), "owed_balance": owed_bal,
            "qattah_total": qattah_total,
            "unattributed": round(owed_bal - total_out, 2),
            "cash_accounts": [{"id": a["id"], "name": a["name"], "sar": round(a["sar"], 2),
                               "cur": a["cur"]} for a in accs]}


@app.post("/api/receivable/lend")
async def receivable_lend(req: Request):
    """Record money lent: a real transfer cash → Owed-to-me (money leaves cash, becomes a receivable),
    plus a per-person ledger record. Balance-proven."""
    p = await req.json()
    person = (p.get("person") or "").strip()
    amt = round(float(p.get("amount") or 0), 2)
    from_id = p.get("from_account_id")
    owed = _owed_accounts()
    owed_id = p.get("owed_account_id") or (owed[0]["id"] if owed else None)
    if not person or amt <= 0 or not from_id or not owed_id:
        return {"ok": False, "error": "person, amount, from-account and an Owed-to-me account are required"}
    date = (p.get("date") or datetime.now().strftime("%Y-%m-%d"))[:10]
    note = (p.get("note") or "").strip()
    before_owed, before_cash = _acct_bal(owed_id), _acct_bal(from_id)
    desc = f"Lent to {person}" + (f": {note}" if note else "")
    body = {"type": "transfer", "date": date, "amount": f"{amt:.2f}", "description": desc[:120],
            "source_id": from_id, "destination_id": owed_id, "notes": note,
            "tags": ["loan-out", "manual", "trust:verified"]}
    new = ff("POST", "transactions", {"error_if_duplicate_hash": False, "transactions": [body]})
    tid = new["data"]["id"]
    after_owed, after_cash = _acct_bal(owed_id), _acct_bal(from_id)
    rows = _receivables()
    base = re.sub(r"[^a-z0-9]+", "-", person.lower()).strip("-") or "person"
    rid = base
    i = 2
    while any(x.get("id") == rid for x in rows):
        rid = f"{base}-{i}"
        i += 1
    rows.append({"id": rid, "person": person, "principal": amt, "date_lent": date,
                 "note": note, "account_id": owed_id, "lend_txn": tid, "migrated": False,
                 "repayments": []})
    _recv_save(rows)
    audit("receivable_lend", person=person, amount=amt, txn=tid)
    return {"ok": True, "id": rid, "txn": tid,
            "proof": {"owed_before": before_owed, "owed_after": after_owed,
                      "cash_before": before_cash, "cash_after": after_cash,
                      "proof_ok": abs((after_owed - before_owed) - amt) < 0.02
                      and abs((before_cash - after_cash) - amt) < 0.02}}


@app.post("/api/receivable/repay")
async def receivable_repay(req: Request):
    """Record a repayment: transfer Owed-to-me → cash (money comes back), reduce the person's
    outstanding. Balance-proven."""
    p = await req.json()
    rid = (p.get("id") or "").strip()
    amt = round(float(p.get("amount") or 0), 2)
    to_id = p.get("to_account_id")
    rows = _receivables()
    r = next((x for x in rows if x.get("id") == rid), None)
    if not r or amt <= 0 or not to_id:
        return {"ok": False, "error": "receivable, amount and a destination cash account are required"}
    owed_id = r.get("account_id") or (_owed_accounts()[0]["id"] if _owed_accounts() else None)
    date = (p.get("date") or datetime.now().strftime("%Y-%m-%d"))[:10]
    before_owed, before_cash = _acct_bal(owed_id), _acct_bal(to_id)
    desc = f"{r.get('person','')} repaid" + (f" ({p.get('note').strip()})" if p.get("note") else "")
    body = {"type": "transfer", "date": date, "amount": f"{amt:.2f}", "description": desc[:120],
            "source_id": owed_id, "destination_id": to_id, "notes": p.get("note") or "",
            "tags": ["repayment", "manual", "trust:verified"]}
    new = ff("POST", "transactions", {"error_if_duplicate_hash": False, "transactions": [body]})
    tid = new["data"]["id"]
    after_owed, after_cash = _acct_bal(owed_id), _acct_bal(to_id)
    r.setdefault("repayments", []).append({"date": date, "amount": amt, "txn": tid})
    _recv_save(rows)
    audit("receivable_repay", id=rid, amount=amt, txn=tid)
    return {"ok": True, "outstanding": _recv_outstanding(r), "txn": tid,
            "proof": {"owed_before": before_owed, "owed_after": after_owed,
                      "cash_before": before_cash, "cash_after": after_cash,
                      "proof_ok": abs((before_owed - after_owed) - amt) < 0.02
                      and abs((after_cash - before_cash) - amt) < 0.02}}


@app.post("/api/receivable/migrate")
async def receivable_migrate(req: Request):
    """Attribute the pre-existing Owed-to-me lump (e.g. the 250 already on the account) to a person,
    WITHOUT moving money — the balance already reflects it. Keeps the ledger's total honest."""
    p = await req.json()
    person = (p.get("person") or "").strip()
    owed = _owed_accounts()
    owed_id = p.get("owed_account_id") or (owed[0]["id"] if owed else None)
    if not person or not owed_id:
        return {"ok": False, "error": "person and an Owed-to-me account are required"}
    owed_bal = next((a["bal"] for a in owed if a["id"] == owed_id), 0.0)
    attributed = sum(_recv_outstanding(r) for r in _receivables() if r.get("account_id") == owed_id)
    amt = round(float(p.get("amount") or (owed_bal - attributed)), 2)
    if amt <= 0:
        return {"ok": False, "error": f"nothing unattributed on this account (balance {owed_bal}, already attributed {round(attributed,2)})"}
    rows = _receivables()
    base = re.sub(r"[^a-z0-9]+", "-", person.lower()).strip("-") or "person"
    rid, i = base, 2
    while any(x.get("id") == rid for x in rows):
        rid = f"{base}-{i}"; i += 1
    rows.append({"id": rid, "person": person, "principal": amt,
                 "date_lent": p.get("date_lent") or "", "note": p.get("note") or "(migrated existing balance)",
                 "account_id": owed_id, "lend_txn": None, "migrated": True, "repayments": []})
    _recv_save(rows)
    audit("receivable_migrate", person=person, amount=amt)
    return {"ok": True, "id": rid, "amount": amt}


@app.post("/api/receivable/delete")
async def receivable_delete(req: Request):
    """Remove a ledger record (does NOT touch the Firefly money — only the per-person layer)."""
    p = await req.json()
    rid = (p.get("id") or "").strip()
    _recv_save([x for x in _receivables() if x.get("id") != rid])
    audit("receivable_delete", id=rid)
    return {"ok": True}


def _qattah_circle():
    """The inner circle — close family + best friends you actually share meals with. Self-service,
    editable. The general owed-to-me ledger stays open to ANYONE; the circle only decides who appears
    in the quick Qattah picker. One person universe underneath."""
    d = _yaml_load("qattah_circle.yaml")
    return d.get("circle", []) if isinstance(d, dict) else []


@app.get("/api/qattah/roster")
def qattah_roster():
    """The Qattah picker: the inner circle, plus anyone you already have a qattah tab with (so recent
    partners surface even before you add them). Free-add in the UI joins the circle."""
    circle = list(_qattah_circle())
    for r in _receivables():
        nm = r.get("person")
        if nm and r.get("origin") == "qattah" and nm not in circle:
            circle.append(nm)
    d = _yaml_load("qattah_circle.yaml")
    groups = d.get("groups", []) if isinstance(d, dict) else []
    return {"circle": circle, "groups": groups}


@app.post("/api/qattah/circle")
async def qattah_circle_edit(req: Request):
    """Add or drop a person from the inner circle (does NOT touch their ledger history)."""
    p = await req.json()
    d = _yaml_load("qattah_circle.yaml")
    if not isinstance(d, dict):
        d = {}
    circle = d.get("circle", [])
    add, rm = (p.get("add") or "").strip(), (p.get("remove") or "").strip()
    if add and add not in circle:
        circle.append(add)
    if rm and rm in circle:
        circle.remove(rm)
    d["circle"] = circle
    _yaml_save("qattah_circle.yaml", d)
    audit("qattah_circle", add=add, remove=rm)
    return {"ok": True, "circle": circle}


@app.post("/api/qattah")
async def qattah(req: Request):
    """قطة — split a shared order into three simultaneous truths: the FULL cash stays out of the
    account (untouched), only HIS share stays in the expense category (consumption truth), and each
    other person's share becomes a per-person receivable tagged origin:qattah (owed-to-me truth).
    Mechanism: re-point the one expense into (his share = expense) + (each other share = transfer →
    Owed-to-me + a receivable record). Balance-proven."""
    p = await req.json()
    tid = str(p["id"])
    shares = [{"person": (s.get("person") or "").strip(), "amount": round(float(s.get("amount") or 0), 2)}
              for s in (p.get("shares") or []) if (s.get("person") or "").strip() and float(s.get("amount") or 0) > 0]
    if not shares:
        return {"ok": False, "error": "Add at least one other person and their share."}
    orig = ff("GET", f"transactions/{tid}")["data"]["attributes"]["transactions"][0]
    if orig.get("type") != "withdrawal":
        return {"ok": False, "error": "Qattah works on an expense you paid."}
    total = round(float(orig["amount"]), 2)
    src = orig.get("source_id")
    date = (orig.get("date") or datetime.now().strftime("%Y-%m-%d"))[:10]
    merch = orig.get("destination_name") or merchant_display(orig.get("description") or "") or "order"
    cat = orig.get("category_name") or ""
    ext = orig.get("external_id")
    others = round(sum(s["amount"] for s in shares), 2)
    my_amount = round(float(p["my_amount"]), 2) if p.get("my_amount") not in (None, "") else round(total - others, 2)
    if my_amount < -0.01 or abs(my_amount + others - total) > 0.02:
        return {"ok": False, "error": f"The shares don't add up: {others} for others + {my_amount} for "
                f"you must equal the SAR {total} you paid."}
    owed = _owed_accounts()
    if not owed:
        return {"ok": False, "error": "No “Owed to me” account exists to hold the shares."}
    owed_id = owed[0]["id"]
    src_before, owed_before = _acct_bal(src), _acct_bal(owed_id)
    # re-point: delete the single expense, recreate his share as the expense (keep provenance)
    ff("DELETE", f"transactions/{tid}")
    if my_amount > 0.009:
        ff("POST", "transactions", {"error_if_duplicate_hash": False, "transactions": [{
            "type": "withdrawal", "date": date, "amount": f"{my_amount:.2f}",
            "description": (orig.get("description") or merch)[:120], "source_id": src,
            "destination_name": merch, "category_name": cat,
            "tags": sorted(set((orig.get("tags") or []) + ["qattah", "manual", "trust:verified"])),
            **({"external_id": ext} if ext else {})}]})
    recs = _receivables()
    made = []
    for s in shares:
        t = ff("POST", "transactions", {"error_if_duplicate_hash": False, "transactions": [{
            "type": "transfer", "date": date, "amount": f"{s['amount']:.2f}",
            "description": f"Qattah — {s['person']}'s share of {merch}"[:120],
            "source_id": src, "destination_id": owed_id,
            "tags": ["qattah", "loan-out", "manual", "trust:verified"]}]})
        base = re.sub(r"[^a-z0-9]+", "-", s["person"].lower()).strip("-") or "person"
        rid, i = f"{base}-q{date.replace('-', '')}", 2
        while any(x.get("id") == rid for x in recs):
            rid = f"{base}-q{date.replace('-', '')}-{i}"; i += 1
        recs.append({"id": rid, "person": s["person"], "principal": s["amount"], "date_lent": date,
                     "note": f"Qattah — {merch} ({date})", "account_id": owed_id, "origin": "qattah",
                     "merchant": merch, "lend_txn": t["data"]["id"], "migrated": False, "repayments": []})
        made.append({"person": s["person"], "amount": s["amount"]})
    _recv_save(recs)
    # anyone you split with joins the inner circle, and remember this group as a frequent "the usual"
    cd = _yaml_load("qattah_circle.yaml")
    if not isinstance(cd, dict):
        cd = {}
    circle = cd.get("circle", [])
    for s in shares:
        if s["person"] not in circle:
            circle.append(s["person"])
    grp = sorted(s["person"] for s in shares)
    groups = [g for g in cd.get("groups", []) if sorted(g) != grp][:4]
    cd["circle"], cd["groups"] = circle, ([grp] + groups)[:5]
    _yaml_save("qattah_circle.yaml", cd)
    src_after, owed_after = _acct_bal(src), _acct_bal(owed_id)
    audit("qattah", txn=tid, merchant=merch, total=total, my_share=my_amount, others=made)
    cash_unchanged = abs(src_after - src_before) < 0.02          # full order still out of the account
    owed_grew = abs((owed_after - owed_before) - others) < 0.02  # others' shares now owed to me
    return {"ok": True, "merchant": merch, "total": total, "my_share": my_amount, "shares": made,
            "proof": {"account_before": src_before, "account_after": src_after,
                      "owed_before": owed_before, "owed_after": owed_after,
                      "cash_unchanged": cash_unchanged, "owed_grew": owed_grew,
                      "proof_ok": cash_unchanged and owed_grew}}


@app.get("/owed", response_class=HTMLResponse)
def owed_page():
    with open(os.path.join(os.path.dirname(__file__), "owed.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/today", response_class=HTMLResponse)
def today_page():
    with open(os.path.join(os.path.dirname(__file__), "today.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/family", response_class=HTMLResponse)
def family_page():
    with open(os.path.join(os.path.dirname(__file__), "family.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/subscriptions", response_class=HTMLResponse)
def subscriptions_page():
    with open(os.path.join(os.path.dirname(__file__), "subscriptions.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/forecast", response_class=HTMLResponse)
def forecast_page():
    with open(os.path.join(os.path.dirname(__file__), "forecast.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/debt", response_class=HTMLResponse)
def debt_page():
    with open(os.path.join(os.path.dirname(__file__), "debt.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/insights", response_class=HTMLResponse)
def insights_page():
    with open(os.path.join(os.path.dirname(__file__), "insights.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/budget", response_class=HTMLResponse)
def budget_page():
    with open(os.path.join(os.path.dirname(__file__), "budget.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/zakat", response_class=HTMLResponse)
def zakat_page():
    with open(os.path.join(os.path.dirname(__file__), "zakat.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/wealth", response_class=HTMLResponse)
def wealth_page():
    with open(os.path.join(os.path.dirname(__file__), "wealth.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


# --- Cash-count wizard (guided count of every physical-cash account → adjustment entries) ---
def _counted():
    d = _yaml_load("counted.yaml")
    return d.get("counted", {}) if isinstance(d, dict) else {}


def _counted_save(m):
    _yaml_save("counted.yaml", {"counted": m})


def _is_cash_account(name, role, kind):
    if role == "ccAsset":
        return False
    if kind == "cash":
        return True
    n = (name or "").lower()
    return any(k in n for k in ("wallet", "safe", "cash", "محفظة", "خزنة", "نقد"))


@app.get("/api/cashcount/accounts")
def cashcount_accounts():
    """Every physical-cash account (wallets, safes, kids'/currency safes) with its book balance,
    native currency, and staleness since last counted."""
    import datetime as _dt
    today = _dt.date.today()
    counted = _counted()
    kinds = _acct_kinds_map()
    out = []
    for a in ff_all("accounts", type="asset"):
        at = a["attributes"]
        if not _is_cash_account(at.get("name"), at.get("account_role"), kinds.get(str(a["id"]))):
            continue
        last = counted.get(str(a["id"]))
        stale = None
        if last:
            try:
                y, m, d = (int(x) for x in last[:10].split("-"))
                stale = (today - _dt.date(y, m, d)).days
            except Exception:
                pass
        out.append({"id": a["id"], "name": at.get("name") or "",
                    "balance": round(float(at.get("current_balance") or 0), 2),
                    "currency": at.get("currency_code") or "SAR",
                    "last_counted": last, "stale_days": stale})
    out.sort(key=lambda x: ((x["stale_days"] is None), -(x["stale_days"] or 0)))
    return {"accounts": out, "today": today.isoformat()}


@app.post("/api/cashcount/apply")
async def cashcount_apply(req: Request):
    """Apply counted amounts: for each account where counted ≠ book, post an adjustment (in the
    account's OWN currency), stamp 'counted {date}', and record the count. Balance-proven per line."""
    p = await req.json()
    date = (p.get("date") or datetime.now().strftime("%Y-%m-%d"))[:10]
    counts = p.get("counts") or []
    counted = _counted()
    results = []
    for c in counts:
        aid = c.get("account_id")
        if aid is None or c.get("counted") in (None, ""):
            continue
        at = ff("GET", f"accounts/{aid}")["data"]["attributes"]
        cur = at.get("currency_code") or "SAR"
        book = round(float(at.get("current_balance") or 0), 2)
        want = round(float(c["counted"]), 2)
        diff = round(want - book, 2)
        entry = {"account_id": aid, "name": at.get("name") or "", "currency": cur,
                 "book": book, "counted": want, "diff": diff, "txn": None}
        if abs(diff) >= 0.01:
            note = f"Cash count {date}: {book} → {want} ({'+' if diff > 0 else ''}{diff})"
            ensure_currency(cur)
            # a cash-count adjustment is a correction (ledger meets reality) — excluded from flow
            # analytics, no category; it moves the balance only.
            cc_tags = ["counted", "cash-count", "correction", "excluded", "manual", "trust:verified"]
            if diff > 0:
                body = {"type": "deposit", "date": date, "amount": f"{diff:.2f}",
                        "description": "⚖ Cash count adjustment", "source_name": "Cash count",
                        "destination_id": aid, "category_name": "",
                        "notes": note, "tags": cc_tags}
            else:
                body = {"type": "withdrawal", "date": date, "amount": f"{abs(diff):.2f}",
                        "description": "⚖ Cash count adjustment", "source_id": aid,
                        "destination_name": "Cash count", "category_name": "",
                        "notes": note, "tags": cc_tags}
            new = ff("POST", "transactions", {"error_if_duplicate_hash": False, "transactions": [body]})
            entry["txn"] = new["data"]["id"]
            entry["after"] = _acct_bal(aid)
            entry["proof_ok"] = abs(entry["after"] - want) < 0.02
        else:
            entry["after"] = book
            entry["proof_ok"] = True
        counted[str(aid)] = date
        results.append(entry)
    _counted_save(counted)
    audit("cashcount_apply", date=date, accounts=len(results),
          adjusted=sum(1 for r in results if r["txn"]))
    return {"ok": True, "date": date, "results": results}


@app.get("/reports", response_class=HTMLResponse)
def reports_page():
    with open(os.path.join(os.path.dirname(__file__), "reports.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/rules", response_class=HTMLResponse)
def rules_page():
    with open(os.path.join(os.path.dirname(__file__), "rules.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/guide", response_class=HTMLResponse)
def guide_page():
    with open(os.path.join(os.path.dirname(__file__), "guide.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/changelog", response_class=HTMLResponse)
def changelog_page():
    with open(os.path.join(os.path.dirname(__file__), "changelog.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


_MON = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


@app.get("/api/changelog")
def api_changelog():
    """'What's new', rendered from STATE.md — zero manual upkeep. Splits on '## ' headers,
    pulls a date from each header where present, returns newest-first."""
    # STATE.md is mounted read-only at /app/STATE.md (see docker-compose) so the changelog stays
    # live without a rebuild. Fall back to a repo-relative path for non-container runs.
    path = "/app/STATE.md"
    if not os.path.exists(path):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "STATE.md")
    try:
        text = open(path, encoding="utf-8").read()
    except Exception:
        return {"entries": []}
    entries = []
    cur = None
    for line in text.splitlines():
        if line.startswith("## "):
            if cur:
                entries.append(cur)
            title = line[3:].strip()
            m = re.search(r"\((\d{1,2})\s+([A-Z][a-z]{2})(?:\s+(\d{4}))?", title)
            date = None
            if m:
                mon = _MON.get(m.group(2))
                if mon:
                    date = f"{m.group(3) or '2026'}-{mon:02d}-{int(m.group(1)):02d}"
            cur = {"title": title, "date": date, "body": []}
        elif cur is not None:
            cur["body"].append(line)
    if cur:
        entries.append(cur)
    for e in entries:
        # trim body to a readable preview (bullet/prose lines, no huge dumps)
        body = [b for b in e["body"] if b.strip()]
        e["body"] = "\n".join(body[:14]).strip()
    entries = [e for e in entries if e["title"] and not e["title"].startswith("Tokens")]
    entries.sort(key=lambda e: (e["date"] or "0000-00-00"), reverse=True)
    return {"entries": entries[:40]}


@app.get("/goals", response_class=HTMLResponse)
def goals_page():
    with open(os.path.join(os.path.dirname(__file__), "goals.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/rail.js")
def rail_js():
    from fastapi.responses import Response
    with open(os.path.join(os.path.dirname(__file__), "rail.js"), encoding="utf-8") as fh:
        return Response(fh.read(), media_type="application/javascript", headers=_NOCACHE)


@app.get("/face.css")
def face_css():
    from fastapi.responses import Response
    with open(os.path.join(os.path.dirname(__file__), "face.css"), encoding="utf-8") as fh:
        return Response(fh.read(), media_type="text/css", headers=_NOCACHE)


@app.get("/face.js")
def face_js():
    from fastapi.responses import Response
    with open(os.path.join(os.path.dirname(__file__), "face.js"), encoding="utf-8") as fh:
        return Response(fh.read(), media_type="application/javascript", headers=_NOCACHE)


@app.get("/hakim-grotesk.woff2")
def hakim_grotesk():
    # Hero display face (Space Grotesk 600, SIL OFL 1.1) — SELF-HOSTED, no CDN (local-first intact).
    # Immutable + long cache: the file only changes when we ship a new one under a new name.
    path = os.path.join(os.path.dirname(__file__), "hakim-grotesk.woff2")
    return FileResponse(path, media_type="font/woff2",
                        headers={"Cache-Control": "public, max-age=31536000, immutable"})


@app.get("/soon", response_class=HTMLResponse)
def soon_page():
    with open(os.path.join(os.path.dirname(__file__), "soon.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/settings", response_class=HTMLResponse)
def settings_page():
    with open(os.path.join(os.path.dirname(__file__), "settings.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


@app.get("/home")
def home_redirect():
    """Send the ✦ logo to the user's chosen landing page (a real, working setting)."""
    s = {**_DEFAULT_SETTINGS, **_yaml_load("settings.yaml")}
    dest = s.get("landing") or "/dashboard"
    if dest not in ("/dashboard", "/", "/calendar", "/categories", "/recurring"):
        dest = "/dashboard"
    return RedirectResponse(dest)


@app.get("/api/heatmap")
def heatmap_data():
    """Daily spending totals across the ledger's date range — for a GitHub-style
    spending heatmap. Read-only. Honest: few weeks of data yet, so the UI beta-tags it."""
    txns = all_txns()
    dmap, cmap = {}, {}
    for t in txns:
        d = t.get("date") or ""
        if not d:
            continue
        if t["type"] == "withdrawal":
            dmap[d] = round(dmap.get(d, 0.0) + t["amount"], 2)
        cmap[d] = cmap.get(d, 0) + 1
    dates = sorted(dmap.keys())
    days_span = len({(t["date"] or "")[:10] for t in txns if t.get("date")})
    return {"days": dmap, "counts": cmap,
            "from": dates[0] if dates else None, "to": dates[-1] if dates else None,
            "max": max(dmap.values()) if dmap else 0,
            "total_days_with_data": days_span,
            "today": datetime.now().strftime("%Y-%m-%d")}


@app.get("/api/account_series")
def account_series(account: str = ""):
    """Running-balance-over-time for one account, reconstructed from the ledger and
    anchored to the live Firefly balance. Read-only. Plus recent transactions."""
    accs = {a["name"]: a for a in accounts()}
    names = list(accs.keys())
    if account not in accs:
        account = names[0] if names else ""
    if not account:
        return {"account": "", "accounts": [], "series": [], "current": 0, "recent": [], "count": 0}
    cur = float(accs[account].get("balance") or 0)
    owned = set(names)                     # every account HAKIM owns (for the ⇄ two-sided view)
    # BOTH-SIDED: include transactions where this account is source OR destination (Money Pro model).
    txns = [t for t in all_txns() if t.get("date")
            and account in (t.get("account"), t.get("source"), t.get("destination"))]
    txns.sort(key=lambda t: t["date"])

    def effect(t):
        # From THIS account's perspective: money in (or debt reduced) = +, money out = −.
        if t.get("destination") == account:
            return t["amount"]
        if t.get("source") == account:
            return -t["amount"]
        return t["signed"]
    total = round(sum(effect(t) for t in txns), 2)
    opening = round(cur - total, 2)
    bal = opening
    daymap = {}
    for t in txns:
        bal = round(bal + effect(t), 2)
        daymap[t["date"]] = bal
    series = [{"date": d, "balance": b} for d, b in sorted(daymap.items())]

    def row_name(t):
        # a transfer/discharge (the OTHER side is an owned account) reads two-sided, per perspective
        other = t.get("destination") if t.get("source") == account else t.get("source")
        if other in owned and other != account:
            return ("⇄ to " + other) if t.get("source") == account else ("⇄ from " + other)
        if t.get("counterparty"):
            return "↔ " + t["counterparty"]
        return (t.get("display") or t.get("desc") or "").split(" — ")[0] or "(no description)"
    recent = [{"id": t["id"], "name": row_name(t), "date": t["date"], "amount": t["amount"],
               "signed": effect(t), "type": t["type"], "category": t["category"] or ""}
              for t in sorted(txns, key=lambda t: t["date"], reverse=True)[:12]]
    return {"account": account, "accounts": names, "series": series, "current": round(cur, 2),
            "opening": opening, "count": len(txns), "recent": recent,
            "currency": accs[account].get("currency", "SAR")}


@app.get("/recurring", response_class=HTMLResponse)
def recurring_page():
    with open(os.path.join(os.path.dirname(__file__), "recurring.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers=_NOCACHE)


# ---- Recurring / bills (Firefly bills = source of truth, read-only) ----
from datetime import date as _date  # noqa: E402

_FREQ_MONTHLY = {"weekly": 52 / 12, "monthly": 1.0, "quarterly": 1 / 3,
                 "half-year": 1 / 6, "yearly": 1 / 12}


def _add_freq(d, freq):
    if freq == "weekly":
        return d + timedelta(days=7)
    months = {"monthly": 1, "quarterly": 3, "half-year": 6, "yearly": 12}.get(freq, 1)
    y, m = d.year, d.month + months
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    day = min(d.day, _calendar.monthrange(y, m)[1])
    return _date(y, m, day)


def _bill_next_due(date_iso, freq, today):
    """Next occurrence strictly today-or-later, rolled forward from the bill's anchor date."""
    try:
        d = _date.fromisoformat((date_iso or "")[:10])
    except Exception:
        return None
    guard = 0
    while d < today and guard < 600:
        d = _add_freq(d, freq)
        guard += 1
    return d


def _bill_occurrences(date_iso, freq, y, mo):
    """ISO dates on which this bill falls due within month (y, mo)."""
    try:
        d = _date.fromisoformat((date_iso or "")[:10])
    except Exception:
        return []
    first, last = _date(y, mo, 1), _date(y, mo, _calendar.monthrange(y, mo)[1])
    occ, guard = [], 0
    while d < first and guard < 4000:
        d = _add_freq(d, freq)
        guard += 1
    while d <= last and guard < 4000:
        occ.append(d.isoformat())
        d = _add_freq(d, freq)
        guard += 1
    return occ


def _bill_amount(a):
    """Real amount or None. Firefly placeholder here is min==max==1.00 (Hisham's 'to fill' marker)."""
    try:
        lo, hi = float(a.get("amount_min") or 0), float(a.get("amount_max") or 0)
    except Exception:
        return None
    if lo <= 0 and hi <= 0:
        return None
    if lo == 1.0 and hi == 1.0:  # placeholder marker
        return None
    return round((lo + hi) / 2, 2)


def _bill_marks():
    """Manual paid/unpaid marks: {bill_id: {"YYYY-MM": bool}}. HAKIM-side because SMS imports don't
    carry Firefly's bill_id, so native paid_dates stays empty — this is the honest paid ledger."""
    d = _yaml_load("bill_marks.yaml")
    return d.get("marks", {}) if isinstance(d, dict) else {}


def _bill_marks_save(m):
    _yaml_save("bill_marks.yaml", {"marks": m})


def bills_view(today=None):
    """Shared bill projection used by both the Recurring page and the dashboard's Upcoming.
    paid = manual mark this period if set, else the conservative name-match heuristic (paid_source
    tells which)."""
    today = today or datetime.now().date()
    cur_month = today.strftime("%Y-%m")
    txns = all_txns()
    month_out = [t for t in txns if (t["date"] or "")[:7] == cur_month and t["type"] == "withdrawal"]
    marks = _bill_marks()
    out = []
    for b in ff_all("bills"):
        a = b["attributes"]
        if not a.get("active", True):
            continue
        freq = a.get("repeat_freq") or "monthly"
        amt = _bill_amount(a)
        nd = _bill_next_due(a.get("date"), freq, today)
        monthly = round(amt * _FREQ_MONTHLY.get(freq, 1.0), 2) if amt is not None else None
        name = a.get("name") or ""
        # best-effort paid-this-month by name match (conservative: distinctive token >= 5 chars)
        token = _norm(name).split()[0] if name else ""
        auto = bool(token) and len(token) >= 5 and any(token in _norm(t["desc"]) for t in month_out)
        mark = marks.get(str(b["id"]), {}).get(cur_month)
        paid = bool(mark) if mark is not None else auto
        sched = _bill_sched(b["id"])                       # B10: irregular dated instalments
        row = {"id": b["id"], "name": name, "freq": freq, "amount": amt,
               "monthly": monthly, "next_due": nd.isoformat() if nd else None,
               "days": (nd - today).days if nd else None, "paid": paid,
               "paid_source": "marked" if mark is not None else ("auto" if auto else "")}
        if sched:
            upcoming = [d for d in sched if d["date"] >= today.isoformat() and not d.get("paid")]
            nd2 = upcoming[0]["date"] if upcoming else None
            row.update({"irregular": True, "schedule": sched,
                        "sched_total": round(sum(d["amount"] for d in sched), 2),
                        "sched_remaining": round(sum(d["amount"] for d in sched if not d.get("paid")), 2),
                        "next_due": nd2, "days": ((_date.fromisoformat(nd2) - today).days if nd2 else None)})
        out.append(row)
    out.sort(key=lambda x: (x["next_due"] is None, x["next_due"] or ""))
    return out


# B10 — irregular bill schedule: N specific dates + per-date amounts over ONE bill (the school-fees
# shape). A thin overlay in data/bill_schedules.yaml, never three fake monthly bills.
def _bill_sched_all():
    d = _yaml_load("bill_schedules.yaml")
    return d.get("schedules", {}) if isinstance(d, dict) else {}


def _bill_sched(bid):
    return _bill_sched_all().get(str(bid), {}).get("dates", [])


# ── Loyalty miles tracker (Alfursan) — a non-monetary asset earned from spending ─────────────────
# Miles are NOT money: they never enter net worth SAR totals (stored outside Firefly on purpose). The
# balance is the airline's truth — always MANUALLY entered (the monthly ritual), never computed. The
# system adds honest context only: an ESTIMATE of miles earned this month from card spend (labeled, not
# added), and an expiry alert keyed off the nearest miles BATCH's date (Alfursan miles die in batches).
def _loyalty():
    d = _yaml_load("loyalty.yaml")
    return d.get("programs", {}) if isinstance(d, dict) else {}


def _loyalty_save(programs):
    _yaml_save("loyalty.yaml", {"programs": programs})


def _months_until(iso):
    if not iso:
        return None
    try:
        y, m = int(iso[:4]), int(iso[5:7])
        t = _date.today()
        return (y - t.year) * 12 + (m - t.month)
    except Exception:
        return None


@app.get("/api/loyalty")
def api_loyalty():
    """Loyalty programs (Alfursan) — the manually-entered balance + nearest batch expiry, plus honest
    context: estimated miles earned THIS month from the linked cards' spend (spend ÷ earn-rate, a label
    never added to the balance so actual-vs-expected gaps are visible → 'claim missing miles'). Expiry
    alert keys off the next batch's date (amber ≤6mo, red ≤3mo). Read-only; never touches net worth."""
    progs = _loyalty()
    ym = _date.today().strftime("%Y-%m")
    out = []
    for key, p in progs.items():
        cards = p.get("earn_cards") or []
        rate = float(p.get("earn_rate") or 0)
        spend = 0.0
        if cards:
            for t in all_txns():
                if t["type"] == "withdrawal" and (t.get("date") or "")[:7] == ym \
                        and any(c and c in (t.get("account") or "") for c in cards):
                    spend += t["amount"]
        est = round(spend / rate) if rate > 0 else None
        m2e = _months_until(p.get("next_expiry_date"))
        alert = "red" if (m2e is not None and m2e <= 3) else ("amber" if (m2e is not None and m2e <= 6) else "")
        hist = sorted(p.get("history") or [], key=lambda h: h.get("date", ""))
        out.append({"key": key, "name": p.get("name") or key, "balance": p.get("balance"),
                    "as_of": p.get("as_of"), "next_expiry_date": p.get("next_expiry_date"),
                    "next_expiry_amount": p.get("next_expiry_amount"), "months_to_expiry": m2e,
                    "alert": alert, "tier": p.get("tier"), "membership": p.get("membership"),
                    "earn_rate": rate or None, "earn_cards": cards,
                    "spend_this_month": round(spend, 2), "est_earned_this_month": est,
                    "history": hist})
    return {"programs": out, "count": len(out)}


@app.post("/api/loyalty/update")
async def loyalty_update(req: Request):
    """The monthly ritual — enter the balance + nearest-batch expiry from the Saudia app (both the
    airline's face, never computed). Snapshots to history so the miles-over-time line grows."""
    p = await req.json()
    key = str(p.get("key") or "alfursan")
    progs = _loyalty()
    prog = progs.get(key) or {"name": p.get("name") or "Saudia Alfursan", "history": []}
    as_of = (p.get("as_of") or datetime.now().strftime("%Y-%m-%d"))[:10]
    if p.get("balance") not in (None, ""):
        prog["balance"] = round(float(p["balance"]))
    if "next_expiry_date" in p:
        prog["next_expiry_date"] = (p.get("next_expiry_date") or "")[:10] or None
    if "next_expiry_amount" in p:
        prog["next_expiry_amount"] = round(float(p["next_expiry_amount"])) if p.get("next_expiry_amount") not in (None, "") else None
    prog["as_of"] = as_of
    hist = [h for h in (prog.get("history") or []) if h.get("date") != as_of]   # replace same-date
    hist.append({"date": as_of, "balance": prog.get("balance"),
                 "next_expiry_date": prog.get("next_expiry_date"),
                 "next_expiry_amount": prog.get("next_expiry_amount")})
    prog["history"] = sorted(hist, key=lambda h: h["date"])
    progs[key] = prog
    _loyalty_save(progs)
    audit("loyalty_update", key=key, balance=prog.get("balance"), as_of=as_of)
    return {"ok": True, "key": key, "balance": prog.get("balance")}


@app.post("/api/loyalty/config")
async def loyalty_config(req: Request):
    """Edit the program's context fields — tier (a note; Alfursan membership never expires), earn rate
    (e.g. 1 mile per SAR 4), and which cards earn. All editable; changes take effect immediately."""
    p = await req.json()
    key = str(p.get("key") or "alfursan")
    progs = _loyalty()
    prog = progs.get(key) or {"name": p.get("name") or "Saudia Alfursan", "history": []}
    for f in ("name", "tier", "membership"):
        if f in p:
            prog[f] = (p.get(f) or "").strip() or None
    if p.get("earn_rate") not in (None, ""):
        prog["earn_rate"] = float(p["earn_rate"])
    if "earn_cards" in p:
        prog["earn_cards"] = [str(c).strip() for c in (p.get("earn_cards") or []) if str(c).strip()]
    progs[key] = prog
    _loyalty_save(progs)
    audit("loyalty_config", key=key)
    return {"ok": True, "key": key}


@app.get("/api/bill/schedule")
def bill_schedule_get(id: str):
    return {"id": id, "dates": _bill_sched(id)}


@app.post("/api/bill/schedule")
async def bill_schedule_set(req: Request):
    """Set the dated instalments for a bill: [{date, amount, paid?}]. Empty list clears it back to a
    regular repeating bill."""
    p = await req.json()
    bid = str(p["id"])
    dates = []
    for d in (p.get("dates") or []):
        iso = (d.get("date") or "")[:10]
        if not iso:
            continue
        dates.append({"date": iso, "amount": round(float(d.get("amount") or 0), 2),
                      "paid": bool(d.get("paid"))})
    dates.sort(key=lambda x: x["date"])
    alls = _bill_sched_all()
    if dates:
        alls[bid] = {"dates": dates}
    else:
        alls.pop(bid, None)
    _yaml_save("bill_schedules.yaml", {"schedules": alls})
    audit("bill_schedule", id=bid, n=len(dates), total=round(sum(x["amount"] for x in dates), 2))
    return {"ok": True, "dates": dates, "total": round(sum(x["amount"] for x in dates), 2)}


@app.post("/api/bill/mark")
async def bill_mark(req: Request):
    """Mark a bill paid/unpaid for the current month (or clear the override → back to auto-detect)."""
    p = await req.json()
    bid = str(p["id"])
    month = (p.get("month") or datetime.now().strftime("%Y-%m"))[:7]
    marks = _bill_marks()
    slot = marks.setdefault(bid, {})
    if p.get("paid") is None:
        slot.pop(month, None)
    else:
        slot[month] = bool(p["paid"])
    if not slot:
        marks.pop(bid, None)
    _bill_marks_save(marks)
    audit("bill_mark", id=bid, month=month, paid=p.get("paid"))
    return {"ok": True}


_AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


@app.get("/api/brief")
def brief_data():
    """Everything the Morning Brief whisper needs — computed from the same ledger
    sources as the dashboard. Read-only; one call so the script stays thin."""
    fx = fx_rates() or {}

    def sar(amt, cur):
        return float(amt) * (1 if cur == "SAR" else (fx.get(cur) or 1))
    today = datetime.now().date()
    yday = (today - timedelta(days=1)).isoformat()
    txns = all_txns()
    yd = [t for t in txns if (t["date"] or "") == yday]
    y_in = round(sum(t["amount"] for t in yd if t["type"] == "deposit"), 2)
    y_out = round(sum(t["amount"] for t in yd if t["type"] == "withdrawal"), 2)
    _nwp = _networth()               # canonical money position — same number as Dashboard & Accounts
    cash, cards = _nwp["cash"], _nwp["cards_debt"]
    qi = [t for t in txns if t["category"] == REVIEW_CATEGORY]
    merch, one = {}, []
    for it in qi:
        (one.append(it) if TRANSFERISH.search(it["desc"])
         else merch.setdefault(merchant_key(it["desc"]), []).append(it))
    qcount = len(merch) + len(one)
    nb = None
    for b in bills_view(today):
        if b["days"] is not None and b["days"] >= 0:
            nb = {"name": b["name"], "days": b["days"], "amount": b["amount"]}
            break
    h = _hijri(today.isoformat())
    hijri_ar = f"{h['y']} {h['mname']} {h['d']}".translate(_AR_DIGITS)
    return {
        "date": {"greg": today.strftime("%a %d %b %Y"), "hijri_ar": hijri_ar},
        "yesterday": {"in": y_in, "out": y_out, "net": round(y_in - y_out, 2), "count": len(yd)},
        "cash": round(cash, 2), "cards_debt": round(abs(cards), 2),
        "queue": qcount, "next_bill": nb}


@app.get("/api/recurring")
def recurring_data():
    today = datetime.now().date()
    bills = bills_view(today)
    amounts_set = [b for b in bills if b["amount"] is not None]
    monthly_total = round(sum(b["monthly"] for b in amounts_set), 2) if amounts_set else None
    nxt = next((b for b in bills if b["days"] is not None and b["days"] >= 0), None)
    paid = [b for b in bills if b["paid"]]
    return {"today": today.isoformat(), "count": len(bills), "amounts_set": len(amounts_set),
            "summary": {"monthly_total": monthly_total, "active": len(bills),
                        "next": {"name": nxt["name"], "days": nxt["days"]} if nxt else None,
                        "paid_count": len(paid), "paid_total": len(bills)},
            "bills": bills, "freqs": ["weekly", "monthly", "quarterly", "half-year", "yearly"]}


# ── In-app bill management (doctrine: the truth engine's screens are not your screens) ──
# All bill CRUD happens inside HAKIM via the Firefly API — no kick-out to Firefly's own UI.
_BILL_FREQS = ("weekly", "monthly", "quarterly", "half-year", "yearly")


@app.post("/api/bill/update")
async def bill_update(req: Request):
    """Edit a bill in-app: amount / schedule / name / active / notes / anchor date. Amount is
    stored as amount_min == amount_max (a fixed bill); blank clears it back to the placeholder."""
    p = await req.json()
    bid = str(p["id"])
    cur = ff("GET", f"bills/{bid}")["data"]["attributes"]
    body = {"name": p.get("name", cur.get("name")),
            "repeat_freq": p.get("freq") if p.get("freq") in _BILL_FREQS else cur.get("repeat_freq", "monthly"),
            "date": (p.get("date") or cur.get("date") or datetime.now().strftime("%Y-%m-%d"))[:10],
            "active": bool(p["active"]) if "active" in p else cur.get("active", True),
            "currency_code": cur.get("currency_code") or "SAR"}
    if "notes" in p:
        body["notes"] = p["notes"] or ""
    if "amount" in p:
        a = p["amount"]
        if a in (None, "", 0, "0"):
            body["amount_min"] = body["amount_max"] = "1.00"     # placeholder marker (Hisham's 'to fill')
        else:
            v = f"{float(a):.2f}"
            body["amount_min"] = body["amount_max"] = v
    ff("PUT", f"bills/{bid}", body)
    audit("bill_update", id=bid, amount=p.get("amount"), freq=p.get("freq"))
    return {"ok": True}


@app.post("/api/bill/create")
async def bill_create(req: Request):
    p = await req.json()
    name = (p.get("name") or "").strip()
    if not name:
        return {"ok": False, "error": "name required"}
    freq = p.get("freq") if p.get("freq") in _BILL_FREQS else "monthly"
    a = p.get("amount")
    v = f"{float(a):.2f}" if a not in (None, "", 0, "0") else "1.00"
    body = {"name": name, "amount_min": v, "amount_max": v,
            "date": (p.get("date") or datetime.now().strftime("%Y-%m-%d"))[:10],
            "repeat_freq": freq, "skip": 0, "active": True, "currency_code": "SAR",
            "notes": p.get("notes") or ""}
    d = ff("POST", "bills", body)
    audit("bill_create", name=name, freq=freq)
    return {"ok": True, "id": d["data"]["id"]}


@app.post("/api/bill/delete")
async def bill_delete(req: Request):
    p = await req.json()
    ff("DELETE", f"bills/{p['id']}")
    audit("bill_delete", id=p["id"])
    return {"ok": True}


@app.get("/api/committed")
def api_committed():
    return _vcache("committed", "", _committed_impl)


def _committed_impl():
    """Committed money this month — what's already spoken for before any discretionary spending:
    bills due THIS month (counted in their real month, never smeared) + envelope contributions
    (+ scheduled loan/lease/BNPL once Wave M ships them). Backward/forward FACTS only — this is
    NOT 'available to spend' (that framing is safe-to-spend, gated on lived surplus data)."""
    today = _date.today()
    y, mo = today.year, today.month
    paid_ids = {str(b["id"]) for b in bills_view(today) if b["paid"]}   # N3: exclude already-paid
    ym = f"{y:04d}-{mo:02d}"
    bills_total, bill_items, unset, paid_skipped = 0.0, [], 0, 0.0
    for b in ff_all("bills"):
        a = b["attributes"]
        if not a.get("active", True):
            continue
        sched = _bill_sched(b["id"])
        if sched:                                 # B10: irregular dated instalments — count this month's unpaid
            due_items = [d for d in sched if d["date"][:7] == ym and not d.get("paid")]
            due = round(sum(d["amount"] for d in due_items), 2)
            if due > 0:
                bills_total += due
                bill_items.append({"name": a.get("name"), "amount": due,
                                   "dates": [d["date"] for d in due_items], "irregular": True})
            continue
        amt = _bill_amount(a)
        if amt is None:
            unset += 1
            continue
        occ = _bill_occurrences(a.get("date"), a.get("repeat_freq") or "monthly", y, mo)
        if occ:
            due = round(amt * len(occ), 2)
            if str(b["id"]) in paid_ids:          # already paid this month → not still 'committed'
                paid_skipped += due
                continue
            bills_total += due
            bill_items.append({"name": a.get("name"), "amount": due, "dates": occ})
    bills_total = round(bills_total, 2)
    paid_skipped = round(paid_skipped, 2)
    env_total, env_items = 0.0, []
    for name, raw in _cat_targets().items():
        if isinstance(raw, dict) and raw.get("envelope"):
            c = round(float(raw.get("amount") or 0), 2)
            if c > 0:
                env_total += c
                env_items.append({"name": name, "amount": c})
    env_total = round(env_total, 2)
    # financing schedules (loans/BNPL/lease) — this month's unpaid installments (real month)
    debt_total, debt_items = 0.0, []
    ym = f"{y:04d}-{mo:02d}"
    for aid, s in _schedules().items():
        due = [i for i in s.get("installments", []) if not i.get("paid") and (i.get("date") or "")[:7] == ym]
        amt = round(sum(i["amount"] for i in due), 2)
        if amt > 0:
            debt_total += amt
            nextd = min((i.get("date") for i in due), default=None)
            debt_items.append({"account": aid, "kind": s.get("kind"), "amount": amt,
                               "item": s.get("item"), "category": s.get("category"),
                               "person": s.get("person"), "date": nextd})
    debt_total = round(debt_total, 2)
    # credit-card expected payments due THIS month (from each card's payment contract)
    card_total, card_items = 0.0, []
    for a in ff_all("accounts", type="liability") + ff_all("accounts", type="asset"):
        at = a["attributes"]
        if at.get("account_role") != "ccAsset":
            continue
        nm = at.get("name") or ""
        last4 = nm.split("•")[-1].strip() if "•" in nm else ""
        due = _card_due(last4, at.get("current_balance")) if last4 else None
        if due and due["due_amount"] > 0 and due["due_date"][:7] == ym:
            card_total += due["due_amount"]
            card_items.append({"name": nm, "amount": due["due_amount"], "date": due["due_date"],
                               "mode": due["mode"]})
    card_total = round(card_total, 2)
    total = round(bills_total + env_total + debt_total + card_total, 2)
    return {"month": f"{y:04d}-{mo:02d}", "total": total,
            "by_source": {"bills": bills_total, "envelopes": env_total, "debt": debt_total,
                          "cards": card_total},
            "bills": sorted(bill_items, key=lambda x: -x["amount"]), "envelopes": env_items,
            "cards": sorted(card_items, key=lambda x: -x["amount"]),
            "debt": sorted(debt_items, key=lambda x: -x["amount"]),
            "bills_amounts_unset": unset}


def _main_cat(c):
    return (c or "").split(":")[0].strip()


def _sub_cat(c):
    c = c or ""
    return c.split(":", 1)[1].strip() if ":" in c else ""


def _cat_kinds():
    """main-category name -> 'exp' | 'inc' from the local tree (presentation truth)."""
    t = tree()
    out = {}
    for m in (t.get("expense") or {}):
        out[m] = "exp"
    for m in (t.get("income") or {}):
        out[m] = "inc"
    return out


def _prev_month(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    return f"{y-1:04d}-12" if m == 1 else f"{y:04d}-{m-1:02d}"


def _spend_by_cat(txns, ym):
    """{main_category -> withdrawal total} for month ym."""
    out = {}
    for t in txns:
        if (t["date"] or "")[:7] == ym and t["type"] == "withdrawal":
            m = _main_cat(t["category"])
            out[m] = round(out.get(m, 0.0) + t["amount"], 2)
    return out


@app.get("/api/category/compare")
def category_compare(a: str = "", b: str = ""):
    """Z5 — two-period compare. a,b = 'YYYY-MM'. Defaults: this month vs last month.
    Returns per-category spend for both + delta, biggest movers first."""
    txns = all_txns()
    months = sorted({(t["date"] or "")[:7] for t in txns if t.get("date")})
    now = datetime.now().strftime("%Y-%m")
    a = a or now
    b = b or (_month_add(a, -1))
    sa, sb = _spend_by_cat(txns, a), _spend_by_cat(txns, b)
    kinds = _cat_kinds()
    rows = []
    for name in sorted(set(sa) | set(sb)):
        if kinds.get(name) == "inc":
            continue
        va, vb = round(sa.get(name, 0.0), 2), round(sb.get(name, 0.0), 2)
        rows.append({"name": name, "a": va, "b": vb, "delta": round(va - vb, 2),
                     "pct": round((va - vb) / vb * 100, 1) if vb else None})
    rows.sort(key=lambda r: -abs(r["delta"]))
    ta, tb = round(sum(r["a"] for r in rows), 2), round(sum(r["b"] for r in rows), 2)
    return {"a": a, "b": b, "a_label": _month_label(a), "b_label": _month_label(b),
            "rows": rows, "total_a": ta, "total_b": tb, "delta": round(ta - tb, 2)}


@app.get("/api/budget/history")
def budget_history(months: int = 6):
    """B9 — budget history grid: recent months × categories that carry a target, actual vs target
    with ✓/✗, honest only from months that actually have ledger data."""
    txns = all_txns()
    have = sorted({(t["date"] or "")[:7] for t in txns if t.get("date")})
    now = datetime.now().strftime("%Y-%m")
    have = [m for m in have if m <= now]
    cols = have[-max(1, min(int(months or 6), 18)):]
    targets = _cat_targets()
    kinds = _cat_kinds()
    per_month = {ym: _spend_by_cat(txns, ym) for ym in cols}
    rows = []
    for name, raw in targets.items():
        t = _target_norm(raw)
        if not t or kinds.get(name) == "inc":
            continue
        tm = _target_monthly(t)
        cells = []
        for ym in cols:
            actual = round(per_month[ym].get(name, 0.0), 2)
            cells.append({"month": ym, "actual": actual,
                          "ok": (tm is None) or actual <= tm + 0.001})
        rows.append({"name": name, "target_monthly": tm,
                     "period": t.get("period"), "cells": cells})
    rows.sort(key=lambda r: -(r["target_monthly"] or 0))
    return {"months": cols, "labels": [_month_label(m) for m in cols], "rows": rows}


@app.post("/api/txn/trip")
async def txn_trip(req: Request):
    """Z7 — tag/untag a transaction with a trip ('trip:<name>'). Blank name removes any trip tag."""
    p = await req.json()
    tid = str(p["id"])
    name = (p.get("trip") or "").strip()
    s = ff("GET", f"transactions/{tid}")["data"]["attributes"]["transactions"][0]
    tags = [t for t in (s.get("tags") or []) if not t.lower().startswith("trip:")]
    if name:
        tags.append(f"trip:{name}")
    ff("PUT", f"transactions/{tid}", {"transactions": [
        {"transaction_journal_id": s["transaction_journal_id"], "tags": tags}]})
    audit("txn_trip", id=tid, trip=name)
    return {"ok": True, "trip": name}


@app.get("/api/trips")
def api_trips(tag: str = ""):
    """Z7 — trips are tags starting 'trip:'. Lists each trip with total spend, count, date span;
    with ?tag= returns that trip's transactions."""
    txns = all_txns()
    trips = {}
    for t in txns:
        for tg in (t.get("tags") or []):
            if not tg.lower().startswith("trip:"):
                continue
            nm = tg.split(":", 1)[1].strip() or "trip"
            e = trips.setdefault(nm, {"name": nm, "tag": tg, "spend": 0.0, "income": 0.0,
                                      "count": 0, "first": "", "last": "", "txns": []})
            if t["type"] == "withdrawal":
                e["spend"] += t["amount"]
            elif t["type"] == "deposit":
                e["income"] += t["amount"]
            e["count"] += 1
            d = t.get("date") or ""
            e["first"] = d if not e["first"] else min(e["first"], d)
            e["last"] = d if not e["last"] else max(e["last"], d)
            if tag and nm == tag:
                e["txns"].append({"id": t["id"], "date": d, "desc": merchant_display(t["desc"]),
                                  "amount": t["signed"], "category": t["category"],
                                  "account": t["account"]})
    out = []
    for e in trips.values():
        e["spend"] = round(e["spend"], 2)
        e["income"] = round(e["income"], 2)
        e["net"] = round(e["income"] - e["spend"], 2)
        if not tag:
            e.pop("txns", None)
        out.append(e)
    out.sort(key=lambda x: (x["last"] or ""), reverse=True)
    return {"trips": out, "tag": tag}


@app.get("/api/merchants")
def api_merchants():
    """Z6 — the merchant-normalization map (data/merchants.yaml rules). What the ingest engine uses
    to turn raw statement lines into clean names + categories. Manageable in-app (Settings)."""
    y = _merch_yaml()
    rules = y.get("rules", []) if isinstance(y, dict) else []
    out = [{"i": i, "pattern": r.get("pattern", ""), "merchant": r.get("merchant", ""),
            "category": r.get("category", ""), "tags": r.get("tags", [])}
           for i, r in enumerate(rules)]
    return {"rules": out, "count": len(out), "sadad_names": (y.get("sadad_names", {}) if isinstance(y, dict) else {})}


@app.post("/api/merchant/save")
async def merchant_save(req: Request):
    """Add or edit a merchant rule (by index i, or append when i is null)."""
    p = await req.json()
    pattern = (p.get("pattern") or "").strip()
    merchant = (p.get("merchant") or "").strip()
    if not pattern or not merchant:
        return {"ok": False, "error": "pattern and merchant are required"}
    with _lock:
        y = _merch_yaml()
        rules = y.setdefault("rules", [])
        entry = {"pattern": pattern, "merchant": merchant}
        if p.get("category"):
            entry["category"] = p["category"]
        if p.get("tags"):
            entry["tags"] = p["tags"]
        i = p.get("i")
        if i is not None and 0 <= int(i) < len(rules):
            rules[int(i)] = entry
        else:
            rules.append(entry)
        yaml.safe_dump(y, open(MERCHANTS_PATH, "w", encoding="utf-8"), allow_unicode=True, sort_keys=False)
    audit("merchant_save", pattern=pattern, merchant=merchant)
    return {"ok": True}


@app.post("/api/merchant/delete")
async def merchant_delete(req: Request):
    p = await req.json()
    i = p.get("i")
    with _lock:
        y = _merch_yaml()
        rules = y.get("rules", [])
        if i is not None and 0 <= int(i) < len(rules):
            rules.pop(int(i))
            yaml.safe_dump(y, open(MERCHANTS_PATH, "w", encoding="utf-8"), allow_unicode=True, sort_keys=False)
            audit("merchant_delete", index=i)
    return {"ok": True}


@app.get("/api/categories")
def categories_data(month: str = ""):
    return _vcache("categories", month, lambda: _categories_impl(month))


def _categories_impl(month: str = ""):
    """Read-only category breakdown for a month (or 'all'). Shows EVERY category
    (Money Pro doctrine — zero-spend included, honestly 0 and dimmed), rolls up
    subcategories onto their parent, and carries budget targets (periodic + income)
    with the parent = sum-of-children roll-up rule. 'To review' surfaced separately."""
    txns = all_txns()
    months = sorted({(t["date"] or "")[:7] for t in txns if t.get("date")})
    alltime = month == "all"
    if not alltime and month not in months:
        month = months[-1] if months else datetime.now().strftime("%Y-%m")

    # ⑂ cross-month amortization: a withdrawal tagged 'amortize:N' contributes amount/N to each of
    # the N months from its date — in ANALYSIS only; the ledger keeps its single true entry.
    def _amz(t):
        for tg in (t.get("tags") or []):
            if tg.startswith("amortize:"):
                try:
                    return int(tg.split(":")[1])
                except Exception:
                    return 0
        return 0

    def _eff(t, ym):
        n = _amz(t)
        st = (t["date"] or "")[:7]
        if not n:
            return t["amount"] if st == ym else 0.0
        idx = (int(ym[:4]) - int(st[:4])) * 12 + (int(ym[5:7]) - int(st[5:7]))
        return round(t["amount"] / n, 2) if 0 <= idx < n else 0.0

    if alltime:
        scope = txns
    else:
        scope = []
        for t in txns:
            if t["type"] == "withdrawal":
                eff = _eff(t, month)
                if eff > 0:
                    tc = dict(t)
                    tc["amount"] = eff
                    tc["amortized"] = bool(_amz(t))
                    scope.append(tc)
            elif (t["date"] or "")[:7] == month:
                scope.append(t)

    # Canonical "needs review" = genuinely undecided (category == "To review"), the SAME definition the
    # Desk queue uses. Empty-category rows (transfers, excluded corrections, opening/BNPL-funding legs) are
    # category-less BY DESIGN and need no decision — counting them forked this number from the Desk's
    # (7 phantom items vs the Desk's honest 0). One meaning, one computation, both surfaces.
    review_items = [t for t in scope if _main_cat(t["category"]) == "To review"]
    review = None
    if review_items:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        added_7d = sum(1 for t in review_items if (t.get("created") or "") >= cutoff)
        review = {"count": len(review_items),
                  "amount": round(sum(t["amount"] for t in review_items), 2),
                  "added_7d": added_7d}

    if alltime:
        trend_months = months[-3:]
    else:
        trend_months = [_prev_month(_prev_month(month)), _prev_month(month), month]

    def cat_month_total(main, ym):
        return round(sum(t["amount"] for t in txns
                         if (t["date"] or "")[:7] == ym and t["type"] == "withdrawal"
                         and _main_cat(t["category"]) == main), 2)

    kinds = _cat_kinds()
    treedata = tree()
    meta = _cat_meta()
    targets = _cat_targets()

    # aggregate observed activity per (main, sub)
    agg = {}
    for t in scope:
        cstr = t["category"] or ""
        main = _main_cat(cstr)
        if main in ("", "To review"):
            continue
        kind = "exp" if t["type"] == "withdrawal" else "inc" if t["type"] == "deposit" else None
        if kind is None:
            continue
        e = agg.setdefault(main, {"total": 0.0, "count": 0, "kind": None, "subs": {}})
        e["total"] += t["amount"]
        e["count"] += 1
        e["kind"] = e["kind"] or kind
        sub = _sub_cat(cstr)
        if sub:
            s = e["subs"].setdefault(sub, {"total": 0.0, "count": 0})
            s["total"] += t["amount"]
            s["count"] += 1

    # full universe of main categories: tree ∪ observed ∪ anything with a target/meta.
    # 'To review' is surfaced separately (the amber banner), never as a category tile.
    universe = [k for k in kinds if k != "To review"]
    for n in list(agg) + list(targets) + list(meta):
        base = _main_cat(n)
        if base and base != "To review" and base not in universe:
            universe.append(base)

    total_spend = round(sum(a["total"] for a in agg.values() if a["kind"] == "exp"), 2)
    total_income = round(sum(a["total"] for a in agg.values() if a["kind"] == "inc"), 2)

    cats = []
    for name in universe:
        a = agg.get(name, {"total": 0.0, "count": 0, "kind": None, "subs": {}})
        kind = a["kind"] or kinds.get(name, "exp")
        total = round(a["total"], 2)
        defined = list((treedata.get("expense" if kind == "exp" else "income") or {}).get(name, []) or [])
        sub_names = list(defined)
        for s in a["subs"]:
            if s not in sub_names:
                sub_names.append(s)
        subs = []
        for s in sub_names:
            sd = a["subs"].get(s, {"total": 0.0, "count": 0})
            st = _target_norm(targets.get(f"{name}: {s}"))
            subs.append({"name": s, "total": round(sd["total"], 2), "count": sd["count"],
                         "zero": sd["count"] == 0,
                         "target": st["amount"] if st else None,
                         "period": st["period"] if st else None,
                         "target_monthly": _target_monthly(st) if st else None})
        subs.sort(key=lambda x: (x["total"] == 0, -x["total"], x["name"]))
        tg = _target_norm(targets.get(name))
        child_month = round(sum(x["target_monthly"] for x in subs if x["target_monthly"]), 2)
        rolled = False
        if tg:
            eff_amt, eff_period, eff_month = tg["amount"], tg["period"], _target_monthly(tg)
        elif child_month:
            eff_amt, eff_period, eff_month, rolled = child_month, "monthly", child_month, True
        else:
            eff_amt = eff_period = eff_month = None
        mm = meta.get(name) or {}
        # money booked directly on the parent (not on any sub) — must be visible so subs+direct
        # always sum to the parent header (math-transparency law).
        direct = round(total - sum(x["total"] for x in subs), 2)
        cats.append({
            "name": name, "kind": kind, "total": total, "count": a["count"],
            "pct": round(total / total_spend * 100, 1) if (kind == "exp" and total_spend) else 0.0,
            "trend": [cat_month_total(name, ym) for ym in trend_months],
            "target": eff_amt, "period": eff_period, "target_monthly": eff_month,
            "target_rolled": rolled, "direct": direct,
            "icon": mm.get("icon") or "", "color": mm.get("color") or "",
            "custom_icon": mm.get("custom_icon") or "", "flex": mm.get("flex") or "",
            "rollover": mm.get("rollover") or "carry",
            "zero": a["count"] == 0, "subs": subs})
    cats.sort(key=lambda x: (x["kind"] != "exp", x["total"] == 0, -x["total"], x["name"]))

    exp_active = [c for c in cats if c["kind"] == "exp" and c["total"] > 0]
    biggest = exp_active[0] if exp_active else None
    delta = None
    if not alltime:
        prev = _prev_month(month)
        prev_spend = round(sum(t["amount"] for t in txns
                               if (t["date"] or "")[:7] == prev and t["type"] == "withdrawal"), 2)
        if prev_spend:
            pct = round((total_spend - prev_spend) / prev_spend * 100, 1)
            delta = {"pct": pct, "prev": prev_spend,
                     "dir": "exp" if total_spend > prev_spend else "inc"}

    income_delta = None
    if not alltime:
        prev = _prev_month(month)
        prev_inc = round(sum(t["amount"] for t in txns
                             if (t["date"] or "")[:7] == prev and t["type"] == "deposit"), 2)
        if prev_inc:
            income_delta = {"pct": round((total_income - prev_inc) / prev_inc * 100, 1),
                            "prev": prev_inc, "dir": "inc" if total_income >= prev_inc else "exp"}

    season = None if alltime else _season(month)
    greg = "All time" if alltime else datetime(int(month[:4]), int(month[5:7]), 1).strftime("%B %Y")
    monthly_avg = None
    if alltime:
        spend_months = {(t["date"] or "")[:7] for t in txns
                        if t["type"] == "withdrawal" and t.get("date")}
        if spend_months:
            monthly_avg = round(total_spend / len(spend_months), 2)

    budget = [c for c in cats if c["target_monthly"]]
    total_target_exp = round(sum(c["target_monthly"] for c in budget if c["kind"] == "exp"), 2)
    total_target_inc = round(sum(c["target_monthly"] for c in budget if c["kind"] == "inc"), 2)

    return {"month": "all" if alltime else month, "months": months, "greg_label": greg,
            "trend_months": trend_months, "count_txns": len(scope),
            "summary": {"total_spend": total_spend, "total_income": total_income,
                        "net": round(total_income - total_spend, 2), "active": len(exp_active),
                        "biggest": {"name": biggest["name"], "amount": biggest["total"]} if biggest else None,
                        "delta": delta, "income_delta": income_delta, "season": season,
                        "monthly_avg": monthly_avg,
                        "total_target_exp": total_target_exp, "total_target_inc": total_target_inc},
            "review": review, "cats": cats}


@app.get("/api/category_detail")
def category_detail(name: str = ""):
    """Drill dossier for one category (Addendum E) — all plain math, no coaching: monthly
    average, highest month, txn count, first-seen, top merchants within it, 6-month trend."""
    kind = _cat_kinds().get(name, "exp")
    want = "deposit" if kind == "inc" else "withdrawal"
    rows = [t for t in all_txns() if _main_cat(t["category"]) == name
            and t["type"] == want and t.get("date")]
    if not rows:
        return {"name": name, "kind": kind, "count": 0, "total": 0, "monthly_avg": 0,
                "highest": None, "first_seen": None, "merchants": [], "trend": []}
    mo = {}
    for t in rows:
        k = t["date"][:7]
        mo[k] = round(mo.get(k, 0) + t["amount"], 2)
    total = round(sum(mo.values()), 2)
    hi_k = max(mo, key=lambda k: mo[k])
    mm = {}
    for t in rows:
        e = mm.setdefault(merchant_key(t["desc"]),
                          {"name": merchant_display(t["desc"]), "total": 0.0, "count": 0})
        e["total"] += t["amount"]
        e["count"] += 1
    merch = sorted(mm.values(), key=lambda x: -x["total"])[:5]
    for x in merch:
        x["total"] = round(x["total"], 2)
    ym, trend = sorted(mo)[-1], []
    for _ in range(6):
        trend.append({"month": ym, "amount": mo.get(ym, 0.0)})
        ym = _prev_month(ym)
    trend.reverse()
    return {"name": name, "kind": kind, "count": len(rows), "total": total,
            "monthly_avg": round(total / len(mo), 2),
            "highest": {"month": hi_k, "amount": mo[hi_k]},
            "first_seen": min(t["date"] for t in rows), "merchants": merch, "trend": trend}


# ---- Hijri (Umm al-Qura, the Saudi civil calendar) via hijri-converter ----
from hijri_converter import Gregorian  # noqa: E402
_HIJRI_AR = ["", "محرم", "صفر", "ربيع الأول", "ربيع الآخر", "جمادى الأولى",
             "جمادى الآخرة", "رجب", "شعبان", "رمضان", "شوال", "ذو القعدة", "ذو الحجة"]


def _hijri(iso):
    """iso 'YYYY-MM-DD' -> {'d':int,'m':int,'y':int,'mname':str}. Umm al-Qura."""
    y, m, d = (int(x) for x in iso.split("-"))
    h = Gregorian(y, m, d).to_hijri()
    return {"d": h.day, "m": h.month, "y": h.year, "mname": _HIJRI_AR[h.month]}


def _season(month):
    """Hijri/seasonal context for a 'YYYY-MM' month (the Umm al-Qura edge). None if ordinary."""
    try:
        y, mo = int(month[:4]), int(month[5:7])
    except Exception:
        return None
    last = _calendar.monthrange(y, mo)[1]
    hm = set()
    for d in (1, 15, last):
        try:
            hm.add(Gregorian(y, mo, d).to_hijri().month)
        except Exception:
            pass
    if 9 in hm:
        return {"label": "includes Ramadan", "kind": "ramadan"}
    if 10 in hm:
        return {"label": "includes Eid al-Fitr", "kind": "eid"}
    if 12 in hm:
        return {"label": "includes Hajj & Eid al-Adha", "kind": "hajj"}
    if mo in (8, 9):
        return {"label": "back-to-school season", "kind": "school"}
    return None


def _cal_lead_ref(t):
    """Same display logic as the Desk's descParts: person over code, else split on em-dash."""
    if t.get("counterparty"):
        return "↔ " + t["counterparty"], (t.get("display") or t.get("desc") or "").strip()
    f = (t.get("display") or t.get("desc") or "").strip()
    i = f.find(" — ")
    return (f[:i], f[i + 3:]) if i > 0 else (f, "")


@app.get("/api/calendar")
def calendar_data(month: str = ""):
    return _vcache("calendar", month, lambda: _calendar_impl(month))


def _calendar_impl(month: str = ""):
    """Read-only month view: per-day money signal + full day transactions, with
    Umm al-Qura Hijri dates. `month`='YYYY-MM' (defaults to the current month)."""
    txns = all_txns()
    if not month:
        allm = sorted({(t["date"] or "")[:7] for t in txns if t.get("date")})
        month = allm[-1] if allm else datetime.now().strftime("%Y-%m")
    y, mo = int(month[:4]), int(month[5:7])
    ndays = _calendar.monthrange(y, mo)[1]
    days = {}
    for dnum in range(1, ndays + 1):
        iso = f"{y:04d}-{mo:02d}-{dnum:02d}"
        days[iso] = {"date": iso, "hijri": _hijri(iso), "net": 0.0,
                     "in": 0.0, "out": 0.0, "types": [], "review": False, "txns": [], "bills": [],
                     "payouts": []}
    typemap = {"deposit": "in", "withdrawal": "out", "transfer": "xfer"}
    for t in txns:
        dt = t.get("date") or ""
        if dt[:7] != month or dt not in days:
            continue
        cell = days[dt]
        kind = typemap.get(t["type"], "xfer")
        if kind not in cell["types"]:
            cell["types"].append(kind)
        if t["type"] == "deposit":
            cell["in"] += t["amount"]
            cell["net"] += t["amount"]
        elif t["type"] == "withdrawal":
            cell["out"] += t["amount"]
            cell["net"] -= t["amount"]
        review = (t.get("category") or "") in ("", "To review") or t.get("trust") != "verified"
        if review:
            cell["review"] = True
        lead, ref = _cal_lead_ref(t)
        cell["txns"].append({
            "id": t["id"], "name": lead or "(no description)", "ref": ref,
            "account": t["account"] or "", "category": t["category"] or "",
            "amount": t["amount"], "signed": t["signed"], "type": t["type"],
            "kind": kind, "trust": t["trust"], "review": review,
            "currency": t["currency"], "date": dt})
    for cell in days.values():
        cell["in"] = round(cell["in"], 2)
        cell["out"] = round(cell["out"], 2)
        cell["net"] = round(cell["net"], 2)
        cell["txns"].sort(key=lambda x: (-abs(x["signed"]), x["name"]))
    # project active bills onto their due days this month (state-aware empty-day panel)
    try:
        marks = _bill_marks()
        ym = f"{y:04d}-{mo:02d}"
        month_out = [t for t in txns if (t["date"] or "")[:7] == ym and t["type"] == "withdrawal"]

        def _paid(bid, name):                      # N3: paid dot flips green when settled
            mk = marks.get(str(bid), {}).get(ym)
            if mk is not None:
                return bool(mk)
            tok = _norm(name).split()[0] if name else ""
            return bool(tok) and len(tok) >= 5 and any(tok in _norm(t["desc"]) for t in month_out)
        for b in ff_all("bills"):
            a = b["attributes"]
            if not a.get("active", True):
                continue
            sched = _bill_sched(b["id"])
            if sched:                              # B10: dated instalments land on their own days
                for d in sched:
                    if d["date"] in days:
                        days[d["date"]]["bills"].append({"name": a.get("name"), "freq": "once",
                                                         "amount": d["amount"], "paid": bool(d.get("paid")),
                                                         "irregular": True})
                continue
            freq = a.get("repeat_freq") or "monthly"
            amt = _bill_amount(a)
            paid = _paid(b["id"], a.get("name") or "")
            for iso in _bill_occurrences(a.get("date"), freq, y, mo):
                if iso in days:
                    days[iso]["bills"].append({"name": a.get("name"), "freq": freq,
                                               "amount": amt, "paid": paid})
    except Exception:
        pass
    try:                                                   # certificate payout dots (income) this month
        for c in api_certificates().get("certificates", []):
            for iso in c.get("payout_dates", []):
                if iso[:7] == f"{y:04d}-{mo:02d}" and iso in days:
                    days[iso]["payouts"].append({"name": c["name"], "amount": c["per_payout"],
                                                 "kind": "certificate"})
        for aid, s in _schedules().items():                # lease balloon — a distinct dated marker
            if s.get("kind") == "lease" and s.get("balloon_date"):
                b = next((i for i in s["installments"] if i.get("balloon") and not i.get("paid")), None)
                if b and b["date"][:7] == f"{y:04d}-{mo:02d}" and b["date"] in days:
                    days[b["date"]]["bills"].append({"name": s.get("car_id") and "🎈 Balloon", "freq": "once",
                                                     "amount": b["amount"], "balloon": True})
        for a in ff_all("accounts", type="liability") + ff_all("accounts", type="asset"):
            at = a["attributes"]                            # credit-card payment due dots
            if at.get("account_role") != "ccAsset":
                continue
            nm = at.get("name") or ""
            l4 = nm.split("•")[-1].strip() if "•" in nm else ""
            due = _card_due(l4, at.get("current_balance")) if l4 else None
            if due and due["due_amount"] > 0 and due["due_date"] in days:
                days[due["due_date"]]["bills"].append({"name": f"💳 {nm} payment", "freq": "monthly",
                                                        "amount": due["due_amount"], "card": True,
                                                        "mode": due["mode"]})
    except Exception:
        pass
    # header hijri label — name the month(s) the Gregorian month spans
    h1, h2 = _hijri(f"{y:04d}-{mo:02d}-01"), _hijri(f"{y:04d}-{mo:02d}-{ndays:02d}")
    if (h1["m"], h1["y"]) == (h2["m"], h2["y"]):
        hlabel = f"{h1['mname']} {h1['y']}"
    elif h1["y"] == h2["y"]:
        hlabel = f"{h1['mname']} – {h2['mname']} {h2['y']}"
    else:
        hlabel = f"{h1['mname']} {h1['y']} – {h2['mname']} {h2['y']}"
    allm = sorted({(t["date"] or "")[:7] for t in txns if t.get("date")})
    greg = datetime(y, mo, 1).strftime("%B %Y")
    return {"month": month, "greg_label": greg, "hijri_label": hlabel,
            "today": datetime.now().strftime("%Y-%m-%d"), "days_in": ndays,
            "days": days, "months_with_data": allm}


# ---------------------------------------------------------------- APIs
@app.get("/api/tree")
def api_tree():
    """The live category tree (expense + income, with subcategories) + the person list — read fresh so
    a category or subcategory created a minute ago appears in any picker without a page reload."""
    return {"tree": tree(), "persons": PERSON_TAGS}


@app.get("/api/bootstrap")
def bootstrap():
    cat = currency_catalog()
    dates = [t["date"] for t in all_txns() if t["date"]]
    return {"accounts": accounts(), "tree": tree(), "recents": recents()[:6],
            "persons": PERSON_TAGS, "contexts": CONTEXT_TAGS, "fx": fx_rates(),
            "currencies": cat.get("list", {}), "fav_currencies": cat.get("favorites", []),
            "ledger_start": min(dates) if dates else None}


@app.post("/api/fx/save")
async def fx_save(req: Request):
    p = await req.json()
    save_fx(p["code"], p["rate"])
    audit("fx_saved", code=p["code"], rate=p["rate"])
    return {"ok": True}


@app.get("/api/queue")
def queue():
    items = [t for t in all_txns() if t["category"] == REVIEW_CATEGORY]
    merch, one = {}, []
    for it in items:
        if TRANSFERISH.search(it["desc"]):
            one.append(it)
        else:
            merch.setdefault(merchant_key(it["desc"]), []).append(it)
    groups = [{"key": k, "items": g, "count": len(g),
               "total": round(sum(x["amount"] for x in g), 2), "sample": g[0]}
              for k, g in merch.items()]
    groups.sort(key=lambda x: -x["count"])
    for it in one + [g["sample"] for g in groups]:
        it["suggestions"] = suggestions(it)
    return {"merchants": groups, "onebyone": one,
            "merch_sar": round(sum(g["total"] for g in groups), 2),
            "one_sar": round(sum(x["amount"] for x in one), 2)}


@app.get("/api/new")
def new_since(since: str = ""):
    """Everything that entered the ledger since the given ISO timestamp (my last visit),
    split into auto-sorted-by-rules vs needs-my-answer. The daily glance."""
    import datetime as _dt
    def parse(s):
        try:
            return _dt.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
        except Exception:
            return None
    cutoff = parse(since)
    rows = []
    if cutoff:
        for r in all_txns():
            c = parse(r.get("created"))
            if c and c > cutoff:
                rows.append(r)
    rows.sort(key=lambda r: r.get("created") or "", reverse=True)
    auto = [r for r in rows if r["category"] and r["category"] != REVIEW_CATEGORY]
    needs = [r for r in rows if r["category"] == REVIEW_CATEGORY]
    for r in rows:
        r["suggestions"] = suggestions(r)
    return {"auto": auto, "needs": needs, "count": len(rows),
            "auto_n": len(auto), "needs_n": len(needs)}


@app.get("/api/transactions")
def transactions(q: str = "", account: str = "", category: str = "", tag: str = "",
                 source: str = "", pstatus: str = "", klass: str = "", reconciled: str = "",
                 merchant: str = "", dow: str = "", catexact: str = "",
                 dfrom: str = "", dto: str = "", amin: str = "", amax: str = "",
                 unverified: str = "", ttype: str = "", excluded: str = "",
                 offset: int = 0, limit: int = 40):
    rows = all_txns(include_excluded=True)   # Desk shows excluded (struck-through), analytics don't
    ql = _norm(q.strip())
    def keep(r, with_date=True):
        is_excl = "excluded" in (r.get("tags") or [])
        if excluded == "only" and not is_excl:
            return False
        if excluded != "only" and excluded != "with" and is_excl:
            return False    # default: hide excluded unless explicitly shown
        if ttype and r["type"] != ttype:
            return False
        if ql and ql not in _norm(r["desc"] + " " + r["notes"] + " " + r["category"]
                                  + " " + (r["account"] or "")):
            return False
        if tag and tag not in (r.get("tags") or []):
            return False
        if source and (r.get("prov") or {}).get("src_key") != source:
            return False
        if pstatus and (r.get("prov") or {}).get("st_key") != pstatus:
            return False
        if account and account not in (r.get("account"), r.get("source"), r.get("destination")):
            return False   # match EITHER side, so a discharge (→ liability) shows under the debt too
        if category and category not in r["category"]:
            return False
        if catexact and r["category"] != catexact:   # direct-on-parent: exact category, excludes subs
            return False
        if with_date and dfrom and r["date"] < dfrom:
            return False
        if with_date and dto and r["date"] > dto:
            return False
        if amin and r["amount"] < float(amin):
            return False
        if amax and r["amount"] > float(amax):
            return False
        if unverified and r["trust"] == "verified":
            return False
        if klass and r.get("klass") != klass:
            return False
        if reconciled == "yes" and not r.get("reconciled"):
            return False
        if reconciled == "no" and r.get("reconciled"):
            return False
        if merchant and merchant_key(r["desc"]) != merchant:   # dashboard merchant deep-link
            return False
        if dow != "":                                          # day-of-week deep-link (0=Mon..6=Sun)
            try:
                if datetime.fromisoformat(r["date"]).weekday() != int(dow):
                    return False
            except Exception:
                return False
        return True
    rows = [r for r in rows if keep(r)]
    rows.sort(key=lambda r: r["date"], reverse=True)
    sum_in = round(sum(r["amount"] for r in rows if r["type"] == "deposit"), 2)
    sum_out = round(sum(r["amount"] for r in rows if r["type"] == "withdrawal"), 2)
    for r in rows[offset:offset + limit]:
        r["suggestions"] = suggestions(r)
    # rows matching every filter EXCEPT the date window — so no transaction can hide outside the
    # current view (the June-ghost / October-200 reachability class). Split past vs future.
    outside = {"past": 0, "future": 0}
    if dfrom or dto:
        for r in all_txns(include_excluded=True):
            if not keep(r, with_date=False):
                continue
            if dfrom and r["date"] < dfrom:
                outside["past"] += 1
            elif dto and r["date"] > dto:
                outside["future"] += 1
    return {"total": len(rows), "rows": rows[offset:offset + limit],
            "sum_in": sum_in, "sum_out": sum_out, "outside": outside,
            "next": offset + limit if offset + limit < len(rows) else None}


@app.get("/api/txn/{tid}")
def one_txn(tid: str):
    try:
        data = ff("GET", f"transactions/{tid}")["data"]
    except Exception:
        raise HTTPException(status_code=404, detail=f"transaction {tid} no longer exists")
    r = norm(data)
    r["suggestions"] = suggestions(r)
    r["links"] = links_of(r.get("jid") or tid)
    return r


@app.post("/api/txn/edit")
async def txn_edit(req: Request):
    """Full edit of an existing transaction (amount/date/description/account). A deliberate
    write surface — every change appends an honest audit note ('edited by Hisham …: amount
    150→161') so corrections leave a trail, never a silent rewrite. Undoable. Provenance
    fields (bank reference, statement line) are read-only and never touched here."""
    p = await req.json()
    tid = str(p["id"])
    s = ff("GET", f"transactions/{tid}")["data"]["attributes"]["transactions"][0]
    jid = s["transaction_journal_id"]
    tp = s["type"]
    acct_key = "destination_id" if tp == "deposit" else "source_id"
    fields = {"transaction_journal_id": jid}
    changes = []
    if p.get("amount") not in (None, ""):
        old, new = round(float(s["amount"]), 2), round(float(p["amount"]), 2)
        if abs(old - new) > 0.001:
            fields["amount"] = f"{new}"
            changes.append(f"amount {old:g}→{new:g}")
    if p.get("date") and p["date"][:10] != (s.get("date") or "")[:10]:
        fields["date"] = p["date"][:10]
        changes.append(f"date {(s.get('date') or '')[:10]}→{p['date'][:10]}")
    if "description" in p and (p.get("description") or "") != (s.get("description") or ""):
        fields["description"] = p["description"]
        changes.append("description")
    if p.get("account_id") and str(p["account_id"]) != str(s.get(acct_key)):
        fields[acct_key] = str(p["account_id"])
        changes.append("account")
    if not changes:
        return {"ok": True, "changed": False}
    stamp = f"edited by Hisham, {datetime.now().strftime('%-d %b %Y')}: {', '.join(changes)}"
    fields["notes"] = ((s.get("notes") or "") + ("\n" if s.get("notes") else "") + stamp).strip()
    restore = [{"id": tid, "jid": jid, "fields": {
        "amount": s["amount"], "date": (s.get("date") or "")[:10],
        "description": s.get("description") or "", "notes": s.get("notes") or "",
        acct_key: s.get(acct_key)}}]
    ff("PUT", f"transactions/{tid}", {"transactions": [fields]})
    record_undo("edit", f"Edited txn {tid}: {', '.join(changes)}", restore=restore)
    audit("txn_edit", txn=tid, changes=changes)
    return {"ok": True, "changed": True, "changes": changes}


@app.post("/api/txn/amortize")
async def txn_amortize(req: Request):
    """⑂ Spread this expense across N months in the ANALYSIS views (Categories/Reports/budget) —
    the ledger keeps its single true entry. Stored as an 'amortize:N' tag; N≤1 clears it."""
    p = await req.json()
    tid = str(p["id"])
    months = int(p.get("months") or 0)
    s = ff("GET", f"transactions/{tid}")["data"]["attributes"]["transactions"][0]
    tags = [t for t in (s.get("tags") or []) if not t.startswith("amortize:")]
    if months > 1:
        tags.append(f"amortize:{months}")
    ff("PUT", f"transactions/{tid}", {"transactions": [
        {"transaction_journal_id": s["transaction_journal_id"], "tags": sorted(tags)}]})
    audit("txn_amortize", txn=tid, months=months if months > 1 else 0)
    return {"ok": True, "months": months if months > 1 else 0}


@app.post("/api/txn/delete")
async def txn_delete(req: Request):
    """Manual entries → hard delete (typed-confirm in the UI). Imported → EXCLUDE, not delete:
    the statement line is truth and stays in the ledger, flagged 'excluded' (out of analytics)
    with an audit note. Preserves reconciliation against the bank."""
    p = await req.json()
    tid = str(p["id"])
    mode = p.get("mode") or "auto"
    s = ff("GET", f"transactions/{tid}")["data"]["attributes"]["transactions"][0]
    tags = s.get("tags") or []
    is_manual = "manual" in tags
    # exclude path (imported, or explicitly requested)
    if mode == "exclude" or (mode == "auto" and not is_manual):
        if "excluded" in tags:                     # toggle back on re-request
            newtags = [t for t in tags if t != "excluded"]
            act = "restored"
        else:
            newtags = sorted(set(tags + ["excluded"]))
            act = "excluded"
        note = ((s.get("notes") or "") + ("\n" if s.get("notes") else "") +
                f"{act} by Hisham, {datetime.now().strftime('%-d %b %Y')}"
                + (": flagged error, out of analytics" if act == "excluded" else "")).strip()
        ff("PUT", f"transactions/{tid}", {"transactions": [
            {"transaction_journal_id": s["transaction_journal_id"], "tags": newtags, "notes": note}]})
        audit("txn_" + act, txn=tid)
        return {"ok": True, "mode": act}
    # hard delete — manual entries only
    if not is_manual:
        return {"ok": False, "error": "Imported transactions can't be hard-deleted — exclude them instead."}
    ff("DELETE", f"transactions/{tid}")
    audit("txn_delete", txn=tid)
    return {"ok": True, "mode": "deleted"}


@app.get("/api/unconfirmed")
def unconfirmed_count():
    """First-class confirmation state: everything not yet verified by a human (white), by type.
    Distinct from the categorization queue (uncategorized) — a txn can be categorized-by-rule
    but still unconfirmed."""
    rows = [t for t in all_txns() if t["trust"] != "verified"]
    by = {"withdrawal": 0, "deposit": 0, "transfer": 0}
    for t in rows:
        by[t["type"]] = by.get(t["type"], 0) + 1
    return {"total": len(rows), "by_type": by,
            "expenses": by["withdrawal"], "income": by["deposit"], "transfers": by["transfer"]}


@app.get("/api/txn/{tid}/attachments")
def txn_attachments(tid: str):
    """List a transaction's attachments (C — viewable receipts, Firefly-native)."""
    try:
        data = ff("GET", f"transactions/{tid}/attachments").get("data", [])
    except Exception:
        return {"attachments": []}
    out = []
    for a in data:
        at = a["attributes"]
        out.append({"id": a["id"], "name": at.get("filename") or at.get("title") or "file",
                    "size": at.get("size"), "mime": at.get("mime") or ""})
    return {"attachments": out}


@app.get("/api/attachment/{aid}/view")
def attachment_view(aid: str):
    """Proxy an attachment's bytes from Firefly (the browser can't hold the API token)."""
    from fastapi.responses import Response
    try:
        meta = ff("GET", f"attachments/{aid}")["data"]["attributes"]
    except Exception:
        return JSONResponse({"error": "not found"}, 404)
    with httpx.Client(timeout=60) as c:
        r = c.get(f"{FIREFLY_URL}/api/v1/attachments/{aid}/download",
                  headers={"Authorization": f"Bearer {TOKEN}", "Accept": "*/*"},
                  follow_redirects=True)
    mime = meta.get("mime") or "application/octet-stream"
    fn = meta.get("filename") or "attachment"
    return Response(r.content, media_type=mime,
                    headers={"Content-Disposition": f'inline; filename="{fn}"'})


_LINK_TYPES = {}
def _link_types():
    """id -> {name, inward, outward}. Firefly's endpoint is `link-types` (hyphen) — the old code
    used `link_types` and silently 404'd, so links never worked. Cached."""
    if not _LINK_TYPES:
        try:
            for lt in ff("GET", "link-types").get("data", []):
                a = lt["attributes"]
                _LINK_TYPES[lt["id"]] = {"name": a.get("name"), "inward": a.get("inward"),
                                         "outward": a.get("outward")}
        except Exception:
            pass
    return _LINK_TYPES


def _journal_brief(jid):
    """Readable one-liner for the other end of a link. Empty dict if it's gone."""
    try:
        s = ff("GET", f"transaction-journals/{jid}")["data"]["attributes"]["transactions"][0]
        return {"jid": jid, "desc": merchant_display(s.get("description") or ""),
                "amount": round(float(s.get("amount") or 0), 2), "type": s.get("type"),
                "date": (s.get("date") or "")[:10],
                "currency": s.get("currency_code") or "SAR"}
    except Exception:
        return {"jid": jid, "desc": "(deleted transaction)", "amount": 0, "type": "", "date": ""}


def links_of(jid):
    """All Firefly links touching journal `jid`, from ITS perspective (so the relationship phrase
    reads correctly). Scans the transaction-links collection (no per-journal endpoint exists)."""
    jid = str(jid)
    types = _link_types()
    out = []
    try:
        for lk in ff_all("transaction-links"):
            a = lk["attributes"]
            iid, oid = str(a.get("inward_id")), str(a.get("outward_id"))
            if jid not in (iid, oid):
                continue
            lt = types.get(str(a.get("link_type_id")), {})
            if jid == iid:                      # this txn is inward → use the inward phrase toward outward
                rel, other = lt.get("inward") or "relates to", oid
            else:
                rel, other = lt.get("outward") or "relates to", iid
            b = _journal_brief(other)
            out.append({"id": lk["id"], "rel": rel, "type": lt.get("name") or "Related",
                        "other": b, "notes": a.get("notes") or ""})
    except Exception:
        pass
    return out


def _put_split(tid, fields):
    g = ff("GET", f"transactions/{tid}")
    s = g["data"]["attributes"]["transactions"][0]
    body = {"transaction_journal_id": s["transaction_journal_id"], **fields}
    ff("PUT", f"transactions/{tid}", {"transactions": [body]})
    return s


def ensure_category(name):
    return name  # Firefly creates the category on first use via category_name


@app.post("/api/apply")
async def apply(req: Request):
    p = await req.json()
    ids = _group_ids(p["key"]) if p.get("key") else [{"id": p["id"]}]
    cat = p.get("category")
    if cat and p.get("sub"):
        cat = f"{cat}: {p['sub']}"
    tags_add = (p.get("persons") or []) + (p.get("contexts") or [])
    if p.get("verify"):
        tags_add.append("trust:verified")
    restore = []
    for it in ids:
        s = ff("GET", f"transactions/{it['id']}")["data"]["attributes"]["transactions"][0]
        restore.append({"id": it["id"], "jid": s["transaction_journal_id"],
                        "fields": {"tags": s.get("tags") or [],
                                   "category_name": s.get("category_name") or "",
                                   "notes": s.get("notes") or ""}})
        newtags = set((s.get("tags") or []) + tags_add)
        if "klass" in p:                       # K: Personal/Business class (mutually exclusive)
            newtags = {t for t in newtags if not t.startswith("class:")}
            if p["klass"] in ("Personal", "Business"):
                newtags.add(f"class:{p['klass']}")
        if "reconciled" in p:                  # D: per-transaction reconciled flag
            if p["reconciled"]:
                newtags.add("reconciled")
            else:
                newtags.discard("reconciled")
        newtags = sorted(newtags)
        fields = {"transaction_journal_id": s["transaction_journal_id"], "tags": newtags}
        if cat:
            fields["category_name"] = cat
        if p.get("note") is not None:
            fields["notes"] = p["note"]
        if p.get("verify"):
            fields["notes"] = (p.get("note") or s.get("notes") or "") + \
                f"\nReviewed by Hisham, {datetime.now().strftime('%-d %b %Y')}"
        ff("PUT", f"transactions/{it['id']}", {"transactions": [fields]})
        audit("apply", txn=it["id"], category=cat, tags=tags_add, note=bool(p.get("note")),
              verify=bool(p.get("verify")))
    lbl = (f"{'Verified' if p.get('verify') else 'Categorised'} "
           f"{len(ids)} · {cat or ', '.join(tags_add) or 'note'}")
    record_undo("edit", lbl, restore=restore)
    if cat:
        push_recent(cat)
        if p.get("always") and p.get("key"):
            sample_desc = ids[0].get("desc", p["key"]) if ids else p["key"]
            add_rule(sample_desc, cat, tags_add)          # importer map (ingest-time)
            try:                                           # R3: also mirror into Firefly's engine
                _make_native_rule(sample_desc, cat, tags_add)
            except Exception as e:
                audit("rule_native_fail", error=str(e)[:120])
    return {"ok": True, "count": len(ids)}


def _group_ids(key):
    return [{"id": t["id"], "desc": t["desc"]} for t in all_txns()
            if t["category"] == REVIEW_CATEGORY and not TRANSFERISH.search(t["desc"])
            and merchant_key(t["desc"]) == key]


def add_rule(sample, cat, tags):
    added, pat = False, ""
    with _lock:
        y = {}
        if os.path.exists(MERCHANTS_PATH):
            y = yaml.safe_load(open(MERCHANTS_PATH, encoding="utf-8")) or {}
        rules = y.setdefault("rules", [])
        pat = re.escape((sample or "").strip()[:40])
        if pat and not any(r.get("pattern") == pat for r in rules):
            rules.append({"pattern": pat, "merchant": (sample or "")[:60],
                          "category": cat, **({"tags": tags} if tags else {})})
            yaml.safe_dump(y, open(MERCHANTS_PATH, "w", encoding="utf-8"),
                           allow_unicode=True, sort_keys=False)
            added = True
    if added:
        audit("rule_added", pattern=pat, category=cat)


@app.post("/api/sadad")
async def sadad_save(req: Request):
    """Name a SADAD biller once → named forever (like the merchants map)."""
    p = await req.json()
    code = (p.get("biller") or "").strip()
    name = (p.get("name") or "").strip()
    if not code or not name:
        return {"ok": False, "error": "biller and name required"}
    with _lock:
        y = _merch_yaml()
        y.setdefault("sadad_names", {})[code] = name
        yaml.safe_dump(y, open(MERCHANTS_PATH, "w", encoding="utf-8"),
                       allow_unicode=True, sort_keys=False)
    audit("sadad_named", biller=code, name=name)
    return {"ok": True, "biller": code, "name": name}


@app.post("/api/verify")
async def verify(req: Request):
    p = await req.json()
    ids = _group_ids(p["key"]) if p.get("key") else [{"id": p["id"]}]
    restore = []
    for it in ids:
        s = ff("GET", f"transactions/{it['id']}")["data"]["attributes"]["transactions"][0]
        restore.append({"id": it["id"], "jid": s["transaction_journal_id"],
                        "fields": {"tags": s.get("tags") or [], "notes": s.get("notes") or ""}})
        tags = sorted(set((s.get("tags") or []) + ["trust:verified"]))
        note = (s.get("notes") or "") + f"\nReviewed by Hisham, {datetime.now().strftime('%-d %b %Y')}"
        ff("PUT", f"transactions/{it['id']}",
           {"transactions": [{"transaction_journal_id": s["transaction_journal_id"],
                              "tags": tags, "notes": note}]})
        audit("verify", txn=it["id"])
    record_undo("edit", f"Verified {len(ids)} 🟢", restore=restore)
    return {"ok": True, "count": len(ids)}


@app.post("/api/transfer")
async def transfer(req: Request):
    p = await req.json()
    # direction: 'to' (withdrawal->transfer to acct) or 'from' (deposit->transfer from acct)
    s = ff("GET", f"transactions/{p['id']}")["data"]["attributes"]["transactions"][0]
    accts = {a["id"]: a for a in accounts()}
    other = p["account_id"]
    if p["dir"] == "to":
        src, dst = s["source_id"], other
    else:
        src, dst = other, s["destination_id"]
    # Does either end point at a debt account? Firefly 422s a literal transfer into a liability
    # (the M2.0 wall) — so we translate to the shape it accepts, silently. To Hisham this is just
    # "transfer to flynas"; under the hood a paydown is withdrawal(asset → liability).
    def _is_liab(aid):
        try:
            return ff("GET", f"accounts/{aid}")["data"]["attributes"].get("type") in ("liability", "liabilities")
        except Exception:
            return False
    dst_liab = bool(dst) and _is_liab(dst)
    src_liab = bool(src) and _is_liab(src)
    base = {"date": (s.get("date") or "")[:10], "amount": s["amount"],
            "description": p.get("note") or s.get("description") or "Transfer",
            "currency_code": s.get("currency_code") or "SAR", "external_id": s.get("external_id"),
            "notes": p.get("note") or s.get("notes") or "",
            "tags": sorted(set((s.get("tags") or []) + (p.get("tags") or []) +
                               (["discharge", "bnpl"] if dst_liab else [])))}
    if dst_liab and not src_liab:          # paying DOWN a debt — the proven discharge shape
        body = {**base, "type": "withdrawal", "source_id": src, "destination_id": dst,
                "category_name": ""}
    elif src_liab and not dst_liab:        # drawing ON a debt (spending borrowed money)
        body = {**base, "type": "withdrawal", "source_id": src, "destination_id": dst,
                "category_name": ""}
    else:
        body = {**base, "type": "transfer", "source_id": src, "destination_id": dst}
    owed_before = abs(_acct_bal(dst)) if dst_liab else None
    new = ff("POST", "transactions", {"error_if_duplicate_hash": False, "transactions": [body]})
    # VERIFY-AFTER-WRITE (balance-proof law): a paydown MUST reduce the debt. If the ledger moved the
    # wrong way (a polarity/sign quirk on how the account was created), roll the write back and refuse
    # — a money-write may never silently INCREASE debt.
    if dst_liab and owed_before is not None:
        owed_after = abs(_acct_bal(dst))
        if owed_after > owed_before + 0.02:
            ff("DELETE", f"transactions/{new['data']['id']}")
            audit("transfer_polarity_rollback", dst=dst, owed_before=owed_before, owed_after=owed_after)
            return {"ok": False, "error": "That would have INCREASED the debt, not paid it down — so "
                    "it was rolled back and nothing changed. This account's balance sign looks off "
                    "(created with a positive balance). Open it → Correct balance to set the true amount "
                    "owed, then try again."}
    # count it against the plan's schedule so N-of-M / next-date / auto-retire all advance
    if dst_liab:
        sch = _schedules().get(str(dst))
        if sch:
            inst = next((i for i in sch["installments"] if not i.get("paid")), None)
            if inst:
                inst["paid"] = True
                _schedule_save(str(dst), sch)
        _maybe_retire(dst)
    audit("convert_transfer", old_txn=p["id"], new_txn=new["data"]["id"],
          dir=p["dir"], account=accts.get(other, {}).get("name"), before=s, after=body)
    # snapshot the ORIGINAL so undo can recreate it after deleting the transfer
    old_body = {"type": s["type"], "date": (s.get("date") or "")[:10], "amount": s["amount"],
                "description": s.get("description") or "", "currency_code": s.get("currency_code") or "SAR",
                "external_id": s.get("external_id"), "notes": s.get("notes") or "",
                "category_name": s.get("category_name") or "", "tags": s.get("tags") or []}
    if s["type"] == "withdrawal":
        old_body["source_id"] = s["source_id"]
        old_body["destination_name"] = s.get("destination_name") or "Unknown"
    elif s["type"] == "deposit":
        old_body["source_name"] = s.get("source_name") or "Unknown"
        old_body["destination_id"] = s["destination_id"]
    else:
        old_body["source_id"] = s["source_id"]
        old_body["destination_id"] = s["destination_id"]
    ff("DELETE", f"transactions/{p['id']}")
    record_undo("convert", f"Converted to transfer · {accts.get(other, {}).get('name', '')}",
                delete_ids=[new["data"]["id"]], recreate=old_body)
    return {"ok": True, "new_id": new["data"]["id"]}


@app.post("/api/quickadd")
async def quickadd(req: Request):
    p = await req.json()
    kind = p["kind"]  # expense|income|transfer
    note = p.get("note") or ""
    payee = (p.get("payee") or "").strip()
    ref = (p.get("reference") or "").strip()
    if ref:
        note = (note + " · ref: " + ref).strip(" ·")
    accts = {a["id"]: a for a in accounts()}
    cat = p.get("category")
    if cat and p.get("sub"):
        cat = f"{cat}: {p['sub']}"
    base = (p.get("persons") or []) + (p.get("contexts") or []) + ["manual"]
    foreign = bool(p.get("foreign_amount") and p.get("foreign_currency"))
    if foreign:
        ensure_currency(p["foreign_currency"])
    if kind == "transfer":
        fa, ta = accts[p["from_id"]], accts[p["to_id"]]
        body = {"type": "transfer", "date": p["date"], "amount": f"{float(p['amount']):.2f}",
                "description": note or "Transfer", "source_id": p["from_id"], "destination_id": p["to_id"],
                "currency_code": fa["currency"], "notes": note, "tags": base + ["trust:verified"]}
        if fa["currency"] != ta["currency"] and p.get("foreign_amount"):
            body["foreign_currency_code"] = ta["currency"]
            body["foreign_amount"] = f"{float(p['foreign_amount']):.2f}"
    else:
        acct = accts[p["account_id"]]
        tags = base + (["trust:proposed"] if foreign else ["trust:verified"])
        n = (note + " | pending bank confirmation").strip(" |") if foreign else note
        common = {"date": p["date"], "amount": f"{float(p['amount']):.2f}",
                  "description": payee or note or (cat or kind), "category_name": cat,
                  "currency_code": acct["currency"], "notes": n, "tags": tags}
        if foreign:
            common["foreign_currency_code"] = p["foreign_currency"]
            common["foreign_amount"] = f"{float(p['foreign_amount']):.2f}"
        if kind == "income":
            body = {**common, "type": "deposit", "source_name": payee or p.get("payer") or "Cash",
                    "destination_id": p["account_id"]}
        else:
            body = {**common, "type": "withdrawal", "source_id": p["account_id"],
                    "destination_name": payee or note or "Cash"}
    new = ff("POST", "transactions", {"error_if_duplicate_hash": False, "transactions": [body]})
    if cat:
        push_recent(cat)
    audit("quickadd", kind=kind, foreign=foreign, category=cat, new_txn=new["data"]["id"])
    record_undo("create", f"Added {kind} · SAR {float(p['amount']):.2f}",
                delete_ids=[new["data"]["id"]])
    return {"ok": True, "new_id": new["data"]["id"]}


@app.post("/api/split")
async def split(req: Request):
    p = await req.json()
    orig = ff("GET", f"transactions/{p['id']}")["data"]["attributes"]["transactions"][0]
    src = orig["source_id"]
    date = (orig.get("date") or "")[:10]
    payee = orig.get("destination_name") or "Split"
    splits = []
    for i, l in enumerate(p["lines"]):
        c = l.get("category")
        if c and l.get("sub"):
            c = f"{c}: {l['sub']}"
        splits.append({"type": "withdrawal", "date": date, "amount": f"{float(l['amount']):.2f}",
                       "description": (orig.get("description") or payee)[:120], "source_id": src,
                       "destination_name": l.get("payee") or payee, "category_name": c,
                       "notes": l.get("note") or "",
                       "tags": (l.get("persons") or []) + ["split", "manual", "trust:verified"],
                       **({"external_id": orig.get("external_id")} if i == 0 and orig.get("external_id") else {})})
    new = ff("POST", "transactions", {"error_if_duplicate_hash": False,
             "group_title": (orig.get("description") or "Split")[:120], "transactions": splits})
    ff("DELETE", f"transactions/{p['id']}")
    audit("split", old_txn=p["id"], new_txn=new["data"]["id"], lines=len(splits),
          total=round(sum(float(l["amount"]) for l in p["lines"]), 2))
    return {"ok": True, "new_id": new["data"]["id"]}


@app.post("/api/balance-correct")
async def balance_correct(req: Request):
    p = await req.json()
    accts = {a["id"]: a for a in accounts()}
    a = accts[p["account_id"]]
    diff = round(float(p["true_balance"]) - a["balance"], 2)
    if diff == 0:
        return {"ok": True, "diff": 0}
    date = datetime.now().strftime("%Y-%m-%d")
    note = f"Balance correction: {a['balance']} → {p['true_balance']}. {p.get('note','')}".strip()
    # A correction is the ledger meeting reality — it MOVES the balance (sign as needed) but has NO
    # spending meaning: tagged 'excluded' (invisible to every flow view — in/out/net, Categories,
    # heat, movers, committed, by-person, Reports, and the intelligence era's training data) and NO
    # category (it's not a real bank fee — mixing it into 'Bank & fees' also poisons the Riba lens).
    _CORR_TAGS = ["reconciliation", "correction", "excluded", "manual", "trust:verified"]
    if diff > 0:
        body = {"type": "deposit", "date": date, "amount": f"{diff:.2f}",
                "description": "⚖ Balance correction", "source_name": "Reconciliation",
                "destination_id": p["account_id"], "category_name": "",
                "notes": note, "tags": _CORR_TAGS}
    else:
        body = {"type": "withdrawal", "date": date, "amount": f"{abs(diff):.2f}",
                "description": "⚖ Balance correction", "source_id": p["account_id"],
                "destination_name": "Reconciliation", "category_name": "",
                "notes": note, "tags": _CORR_TAGS}
    new = ff("POST", "transactions", {"error_if_duplicate_hash": False, "transactions": [body]})
    audit("balance_correct", account=a["name"], old=a["balance"], new=p["true_balance"],
          diff=diff, txn=new["data"]["id"])
    return {"ok": True, "diff": diff}


def link_type_id(name="related"):
    for tid, t in _link_types().items():
        if (t.get("name") or "").lower() == name.lower():
            return tid
    return next(iter(_link_types()), "1")


@app.get("/api/link/types")
def api_link_types():
    """The relationships you can create — Related / Refund / Paid / Reimbursement, with the phrases
    Firefly renders. The Desk uses the OUTWARD phrase (this txn → the other)."""
    return {"types": [{"id": tid, "name": t["name"], "inward": t["inward"], "outward": t["outward"]}
                      for tid, t in _link_types().items()]}


@app.get("/api/link/search")
def api_link_search(q: str = "", exclude: str = ""):
    """Find recent transactions to link to (by description/merchant). Returns journal ids."""
    q = (q or "").strip().lower()
    out = []
    for t in all_txns():
        if str(t.get("jid")) == str(exclude):
            continue
        hay = f"{t.get('desc','')} {t.get('counterparty','')} {t.get('account','')}".lower()
        if q and q not in hay:
            continue
        out.append({"jid": t.get("jid"), "desc": merchant_display(t.get("desc") or ""),
                    "amount": t.get("signed"), "date": t.get("date"), "account": t.get("account"),
                    "currency": t.get("currency") or "SAR"})
        if len(out) >= 30:
            break
    return {"results": out}


@app.post("/api/link")
async def link(req: Request):
    """Create a link from THIS transaction (outward) to another (inward), so the outward phrase reads
    naturally ('(partially) refunds …'). type ∈ Related|Refund|Paid|Reimbursement."""
    p = await req.json()
    this_jid = p.get("jid") or p.get("outward_jid")
    other_jid = p.get("other_jid") or p.get("inward_jid")
    if not this_jid or not other_jid:
        return {"ok": False, "error": "both transactions required"}
    lt = link_type_id(p.get("type") or "related")
    ff("POST", "transaction-links", {"link_type_id": lt,
        "outward_id": str(this_jid), "inward_id": str(other_jid), "notes": p.get("note", "")})
    audit("link", this=this_jid, other=other_jid, type=p.get("type"))
    return {"ok": True}


@app.post("/api/link/delete")
async def link_delete(req: Request):
    p = await req.json()
    ff("DELETE", f"transaction-links/{p['id']}")
    audit("link_delete", id=p["id"])
    return {"ok": True}


@app.post("/api/attach")
async def attach(tid: str = Form(...), jid: str = Form(...), file: UploadFile = None):
    data = await file.read()
    a = ff("POST", "attachments", {"filename": file.filename,
           "attachable_type": "TransactionJournal", "attachable_id": jid})
    aid = a["data"]["id"]
    ff("POST", f"attachments/{aid}/upload", raw=data, ctype="application/octet-stream")
    audit("attach", txn=tid, filename=file.filename, bytes=len(data))
    return {"ok": True}


@app.post("/api/ai")
async def ai(req: Request):
    p = await req.json()
    msgs = []
    page = (p.get("page") or "").strip()   # which screen Ask Finance was opened from (context)
    if page and page not in ("/", ""):
        msgs.append({"role": "system",
                     "content": f"(Context: the user opened this question from the '{page}' "
                                f"screen of their HAKIM personal-finance app.)"})
    msgs.append({"role": "user", "content": p["q"]})
    try:
        with httpx.Client(timeout=90) as c:
            r = c.post(f"{AGENT_URL}/v1/chat/completions",
                       headers={"Authorization": f"Bearer {AGENT_KEY}"},
                       json={"model": "hakim-finance", "stream": False,
                             "messages": msgs})
            r.raise_for_status()
            return {"answer": r.json()["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"answer": f"⚠️ The Finance agent is unavailable right now ({e.__class__.__name__}). "
                          f"You can keep entering and reviewing — it'll be back."}


# ---------------------------------------------------------------- account mgmt
ACCOUNTS_LOG = os.environ.get("ACCOUNTS_LOG", "/app/logs/accounts.log")
PURGE_THRESHOLD = 25   # accounts with more txns than this may only be CLOSED (never purged)


def acct_log(event, **f):
    rec = {"ts": datetime.now(timezone.utc).isoformat(), "by": "Hisham", "event": event, **f}
    try:
        os.makedirs(os.path.dirname(ACCOUNTS_LOG), exist_ok=True)
        with _lock, open(ACCOUNTS_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    except Exception as e:
        print("acct_log fail", e, flush=True)


def account_txns(aid):
    """All transaction groups touching this account (as source or destination)."""
    return ff_all(f"accounts/{aid}/transactions")


def account_stats(aid):
    grps = account_txns(aid)
    total = 0.0
    uncleared = 0.0      # net delta of NOT-yet-reconciled activity (item I)
    rec_count = 0
    for g in grps:
        for s in g["attributes"]["transactions"]:
            if s.get("source_id") == aid or s.get("destination_id") == aid:
                amt = float(s["amount"])
                total += abs(amt)
                reconciled = "reconciled" in (s.get("tags") or [])
                if reconciled:
                    rec_count += 1
                else:
                    delta = amt if s.get("destination_id") == aid else -amt
                    uncleared += delta
    # cleared balance = current − everything still unreconciled; only meaningful once
    # some transactions are reconciled (Sarah's statements). Frontend gates on rec_count.
    return {"count": len(grps), "total": round(total, 2),
            "uncleared": round(uncleared, 2), "reconciled_count": rec_count}


@app.get("/api/accounts")
def api_accounts(closed: int = 0):
    return _vcache("api_accounts", closed, lambda: _api_accounts_impl(closed))


def _api_accounts_impl(closed: int = 0):
    import datetime as _dt
    hidden = _acct_hidden()
    kinds = _acct_kinds_map()
    counted = _counted()
    today = _dt.date.today()
    out = []
    for t in ("asset", "liability"):
        for a in ff_all("accounts", type=t):
            at = a["attributes"]
            if not closed and not at.get("active", True):
                continue
            nm = at["name"]
            is_card = at.get("account_role") == "ccAsset"
            last4 = nm.split("•")[-1].strip() if ("•" in nm and is_card) else ""
            bal = round(float(at.get("current_balance") or 0), 2)
            limit = _card_limits().get(last4) if (is_card and last4) else None
            # utilization: cards carry balance as negative (debt); util = |balance| / limit
            util = round(abs(bal) / limit * 100, 1) if (limit and limit > 0) else None
            kind = kinds.get(str(a["id"])) or kinds.get(a["id"]) or ""
            is_cash = _is_cash_account(nm, at.get("account_role"), kind)
            last_counted = counted.get(str(a["id"])) if is_cash else None
            counted_stale = None
            if last_counted:
                try:
                    y, m, d = (int(x) for x in last_counted[:10].split("-"))
                    counted_stale = (today - _dt.date(y, m, d)).days
                except Exception:
                    pass
            comp = _completed_plans().get(str(a["id"]))
            out.append({"id": a["id"], "name": nm, "active": at.get("active", True),
                        "hidden": a["id"] in hidden,
                        "balance": bal,
                        "currency": at.get("currency_code") or "SAR",
                        "role": at.get("account_role"), "notes": at.get("notes") or "",
                        "group": _group2(a["id"], nm, at.get("account_role"), t),
                        "type": t, "is_card": is_card, "last4": last4,
                        "is_cash": is_cash, "last_counted": last_counted, "counted_stale": counted_stale,
                        "completed": bool(comp), "completed_date": comp.get("date") if comp else None,
                        "limit": limit, "util": util, "kind": kind,
                        "card_due": _card_due(last4, bal) if (is_card and last4) else None,
                        "network": str(_card_networks().get(last4, "")).lower() if is_card else ""})
    out.sort(key=lambda x: _order_key(x["id"]))
    return {"accounts": out}


@app.post("/api/card/network")
async def card_network(req: Request):
    """Set a card's verified network (writes data/card_networks.yaml). A management
    write — deliberate, audited, flag-don't-guess."""
    p = await req.json()
    last4 = str(p.get("last4", "")).strip()
    net = str(p.get("network", "unknown")).strip().lower()
    if not last4:
        return {"ok": False, "error": "last4 required"}
    if net not in ("visa", "mastercard", "mada", "unknown"):
        net = "unknown"
    data = _card_networks()
    data[last4] = net
    path = os.path.join(DATA, "card_networks.yaml")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Card network — VERIFIED (flag-don't-guess). last-4 → visa|mastercard|mada|unknown\n")
        for k, v in data.items():
            fh.write(f'"{k}": {v}\n')
    audit("card_network", last4=last4, network=net)
    return {"ok": True, "last4": last4, "network": net}


@app.post("/api/card/limit")
async def card_limit(req: Request):
    """Set a card's verified credit limit (writes data/card_limits.yaml). Self-service —
    powers the utilization bar. Blank/0 clears it (bar hides — never faked)."""
    p = await req.json()
    last4 = str(p.get("last4", "")).strip()
    if not last4:
        return {"ok": False, "error": "last4 required"}
    data = _card_limits()
    raw = p.get("limit")
    if raw in (None, "", "0", 0):
        data.pop(last4, None)
        limit = None
    else:
        limit = round(float(raw), 2)
        data[last4] = limit
    with open(os.path.join(DATA, "card_limits.yaml"), "w", encoding="utf-8") as fh:
        fh.write("# Card credit limits — VERIFIED by Hisham (never guessed). last-4 → SAR limit.\n")
        fh.write("# Self-service editable from the card manager. Powers the utilization bar.\n")
        fh.write("limits:\n")
        for k, v in data.items():
            fh.write(f'  "{k}": {v}\n')
    audit("card_limit", last4=last4, limit=limit)
    return {"ok": True, "last4": last4, "limit": limit}


# ── Per-card payment contract (mode + due rule) — self-service, powers the "due {date}: SAR X" ──
def _card_registry():
    d = _yaml_load("card_registry.yaml")
    return d.get("cards", {}) if isinstance(d, dict) else {}


def _card_registry_save(cards):
    _yaml_save("card_registry.yaml", {"cards": cards})


def _card_store_sig():
    """Cache-invalidation signature for the registry read: mtimes of the two YAML stores.
    Registry/network edits are file writes (not ff() POSTs), so they don't move the ledger
    data-version — the cache key MUST fold in these mtimes or an edit would serve stale cards."""
    sig = []
    for fn in ("card_registry.yaml", "card_networks.yaml"):
        try:
            sig.append(str(os.path.getmtime(os.path.join(DATA, fn))))
        except OSError:
            sig.append("0")
    return "|".join(sig)


def _expiry_info(expiry):
    """expiry is 'MM/YY' → the card dies at the END of that month. Returns days-until + alert level
    (amber ≤60d, red ≤30d, expired past). NO full card numbers are ever stored — last-4 + expiry only."""
    if not expiry or "/" not in expiry:
        return None
    try:
        mm, yy = expiry.split("/")
        mm, yy = int(mm), int(yy)
        yr = 2000 + yy if yy < 100 else yy
        last = _calendar.monthrange(yr, mm)[1]
        exp = _date(yr, mm, last)
        days = (exp - _date.today()).days
        level = "expired" if days < 0 else ("red" if days <= 30 else ("amber" if days <= 60 else ""))
        return {"date": exp.isoformat(), "days": days, "level": level, "expiry": f"{mm:02d}/{yy:02d}"}
    except Exception:
        return None


@app.get("/api/card/registry")
def card_registry():
    """The card registry — every card (credit + mada debit) by last-4 · owner · network · tier · EXPIRY,
    with a 60d-amber / 30d-red alert so no card in the family expires unannounced. Privacy principle:
    last-4 + expiry + owner only — a full card number is never stored (zero benefit, pure risk).
    Cached on (ledger data-version × registry/network file mtimes) — an edit invalidates it at once."""
    return _vcache("card_registry", _card_store_sig(), _card_registry_impl)


def _card_registry_impl():
    reg = _card_registry()
    nets = _card_networks()
    # union of every last-4 the system knows: registered, networked, or a real card account
    known = set(reg) | set(nets)
    accts = accounts()                                   # one cached read (was two)
    id2name = {a["id"]: a.get("name") for a in accts}
    acct_cards = {}
    for a in accts:
        nm = a.get("name") or ""
        if "•" in nm and a.get("role") == "ccAsset":
            l4 = nm.split("•")[-1].strip()
            acct_cards[l4] = nm
            known.add(l4)
    out = []
    for l4 in sorted(known):
        r = reg.get(l4, {})
        einfo = _expiry_info(r.get("expiry"))
        linked = acct_cards.get(l4) or (id2name.get(r["link_account"]) if r.get("link_account") else None)
        out.append({"last4": l4, "owner": r.get("owner"), "tier": r.get("tier"),
                    "type": r.get("type") or ("credit" if l4 in acct_cards else None),
                    "network": (r.get("network") or nets.get(l4) or "unknown"),
                    "account": linked, "link_account": r.get("link_account"), "expiry": r.get("expiry"),
                    "expiry_date": einfo["date"] if einfo else None,
                    "days_to_expiry": einfo["days"] if einfo else None,
                    "alert": einfo["level"] if einfo else ""})
    out.sort(key=lambda c: (c["days_to_expiry"] is None, c["days_to_expiry"] if c["days_to_expiry"] is not None else 0))
    return {"cards": out, "count": len(out),
            "expiring": [c for c in out if c["alert"] in ("amber", "red", "expired")]}


@app.post("/api/card/registry/set")
async def card_registry_set(req: Request):
    """Register/update a card's expiry · owner · tier · network · type — never a full number."""
    p = await req.json()
    l4 = str(p.get("last4") or "").strip()
    if not l4:
        return {"ok": False, "error": "last-4 required"}
    reg = _card_registry()
    r = reg.get(l4, {})
    for f in ("owner", "tier", "type", "expiry", "network", "link_account"):
        if f in p:
            r[f] = (str(p[f]).strip() or None) if p[f] is not None else None
    if p.get("account"):                                   # mada/debit linked to its bank account
        r["link_account"] = str(p["account"]).strip()
    reg[l4] = {k: v for k, v in r.items() if v is not None}
    _card_registry_save(reg)
    if r.get("network"):                                   # keep the verified-network store in sync
        n = _card_networks()
        n[l4] = str(r["network"]).lower()
        _yaml_save("card_networks.yaml", n)
    audit("card_registry_set", last4=l4, expiry=r.get("expiry"))
    return {"ok": True, "last4": l4, "expiry_info": _expiry_info(r.get("expiry"))}


@app.post("/api/card/registry/delete")
async def card_registry_delete(req: Request):
    """Forget a card's registry metadata (owner · network · tier · expiry · account-link) + its
    verified-network entry. NEVER touches a real card ACCOUNT — a card that is a live Firefly account
    still appears in the registry (metadata blank); to remove that, archive the account itself.
    Used to drop stray/duplicate last-4 entries (e.g. a superseded •XXXX)."""
    p = await req.json()
    l4 = str(p.get("last4") or "").strip()
    if not l4:
        return {"ok": False, "error": "last-4 required"}
    reg = _card_registry()
    existed = l4 in reg
    reg.pop(l4, None)
    _card_registry_save(reg)
    n = _card_networks()
    if l4 in n:
        n.pop(l4, None)
        _yaml_save("card_networks.yaml", n)
    # honest signal: is this last-4 still a real card account? (then it re-appears, metadata-blank)
    still_account = any(("•" in (a.get("name") or "") and a.get("role") == "ccAsset"
                         and (a["name"].split("•")[-1].strip() == l4)) for a in accounts())
    audit("card_registry_delete", last4=l4, existed=existed, still_account=still_account)
    return {"ok": True, "last4": l4, "existed": existed, "still_account": still_account}


def _card_settings():
    d = _yaml_load("card_settings.yaml")
    return d.get("cards", {}) if isinstance(d, dict) else {}


def _card_due(last4, balance):
    """Given a card's settings + live balance, compute the next due date + expected payment. Plain
    fact: what the bank expects on that date. None if unset. balance is negative (debt)."""
    s = _card_settings().get(str(last4))
    if not s:
        return None
    import datetime as _dt
    today = _dt.date.today()
    rule = s.get("due_rule", "dayN")
    if rule == "monthend":
        last = _calendar.monthrange(today.year, today.month)[1]
        cand = _dt.date(today.year, today.month, last)
        if cand < today:
            ny, nm = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
            cand = _dt.date(ny, nm, _calendar.monthrange(ny, nm)[1])
    else:
        n = int(s.get("due_day") or 1)
        n = min(max(n, 1), 28)
        cand = _dt.date(today.year, today.month, n)
        if cand < today:
            ny, nm = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
            cand = _dt.date(ny, nm, n)
    outstanding = round(abs(float(balance or 0)), 2)
    mode = s.get("mode", "full")
    if mode == "minimum":
        pct = float(s.get("pct") or 5)
        floor = float(s.get("floor") or 0)
        due_amt = round(min(outstanding, max(outstanding * pct / 100.0, floor)), 2)
    else:
        due_amt = outstanding
    return {"due_date": cand.isoformat(), "due_amount": due_amt, "mode": mode,
            "outstanding": outstanding, "pct": s.get("pct", 5), "floor": s.get("floor", 0),
            "due_rule": rule, "due_day": s.get("due_day"),
            "days_left": (cand - today).days,
            "carries_forward": mode == "minimum" and due_amt < outstanding - 0.01}


@app.get("/api/card/settings")
def card_settings_get(last4: str):
    s = _card_settings().get(str(last4))
    return {"last4": last4, "settings": s}


@app.post("/api/card/settings")
async def card_settings_set(req: Request):
    """Set a card's payment contract: mode (full|minimum), pct + floor (minimum), due rule
    (dayN|monthend) + day. Self-service — the owner's facts from the bank app, never guessed."""
    p = await req.json()
    last4 = str(p.get("last4", "")).strip()
    if not last4:
        return {"ok": False, "error": "last4 required"}
    d = _yaml_load("card_settings.yaml")
    if not isinstance(d, dict):
        d = {}
    cards = d.setdefault("cards", {})
    if p.get("clear"):
        cards.pop(last4, None)
    else:
        mode = "minimum" if p.get("mode") == "minimum" else "full"
        rule = "monthend" if p.get("due_rule") == "monthend" else "dayN"
        cards[last4] = {"mode": mode, "due_rule": rule,
                        "due_day": int(p.get("due_day") or 1) if rule == "dayN" else None,
                        "pct": round(float(p.get("pct") or 5), 2),
                        "floor": round(float(p.get("floor") or 0), 2)}
    _yaml_save("card_settings.yaml", d)
    audit("card_settings", last4=last4, **(cards.get(last4) or {"cleared": True}))
    return {"ok": True, "last4": last4, "settings": cards.get(last4)}


@app.get("/api/account/stats")
def api_account_stats(id: str):
    return account_stats(id)


# ── Zakat / Hawl groundwork ────────────────────────────────────────────────
# The hawl is one lunar year of continuously holding wealth at/above the nisab
# threshold; zakat falls due on its hijri anniversary. Knowing that anniversary
# requires a DAILY record of whether wealth stayed above nisab — data that can
# only be built forward in time, never backfilled. So this layer records now and
# calculates nothing: no zakat is assessed, no fatwa is implied. It writes two
# files under data/: hawl_trail.json (append-only daily snapshots) and
# hawl_state.json (the derived current streak). Config: data/zakat.yaml.
_DEFAULT_ZAKAT = {
    "nisab_sar": None,              # your verified figure (85g gold on the day); None ⇒ estimate below
    "gold_nisab_grams": 85,         # common gold basis; silver basis (595g) yields a lower nisab
    "gold_price_sar_per_gram": 300, # ESTIMATE — surfaced as unverified until you set nisab_sar
    # asset kinds counted as zakatable (liquid + monetary); property/valuables excluded
    "zakatable_kinds": ["cash", "bank", "digital", "receivable", "gold"],
}


def _zakat_cfg():
    c = dict(_DEFAULT_ZAKAT)
    c.update({k: v for k, v in (_yaml_load("zakat.yaml") or {}).items() if v is not None or k == "nisab_sar"})
    est = round(float(c.get("gold_nisab_grams") or 0) * float(c.get("gold_price_sar_per_gram") or 0), 2)
    nis = c.get("nisab_sar")
    c["nisab"] = float(nis) if nis not in (None, "") else est
    c["nisab_estimated"] = nis in (None, "")
    c["nisab_estimate"] = est
    return c


def _zakatable_total():
    """Sum of liquid/monetary asset balances (SAR). Excludes credit cards (debt-
    carrying) and Other-assets (home/car/valuables — not zakatable). Unclassified
    default-asset accounts count as liquid. Flag-don't-guess: returns the parts so
    the caller can see exactly what was counted."""
    kinds = _acct_kinds_map()
    zk = set(_zakat_cfg()["zakatable_kinds"]) | _ZAKATABLE_EXTRA   # + certificates/funds/etf/silver
    total = 0.0
    parts = []
    for a in ff_all("accounts", type="asset"):
        at = a["attributes"]
        if not at.get("active", True):
            continue
        if at.get("account_role") == "ccAsset":       # credit cards are not assets here
            continue
        k = kinds.get(str(a["id"]))
        if k == "other_asset":                          # physical property — excluded
            continue
        if k and k not in zk:                           # explicitly non-zakatable kind
            continue
        bal = round(float(at.get("current_balance") or 0), 2)
        total += bal
        parts.append({"id": a["id"], "name": at["name"], "kind": k or "asset", "balance": bal})
    return round(total, 2), parts


def _hijri_anniv(iso, years=1):
    """Gregorian date of the `years`-later hijri anniversary of iso (the hawl due date)."""
    from hijri_converter import Gregorian, Hijri
    y, m, d = (int(x) for x in iso.split("-"))
    h = Gregorian(y, m, d).to_hijri()
    for dd in (d, 29, 1):
        try:
            g = Hijri(h.year + years, h.month, min(h.day, dd)).to_gregorian()
            return f"{g.year:04d}-{g.month:02d}-{g.day:02d}"
        except Exception:
            continue
    return None


def _hawl_recompute(trail):
    """Derive the current hawl streak from the append-only trail. hawl_start is the
    first day of the current unbroken above-nisab run; it resets whenever wealth
    dips below nisab. Groundwork only — the due date is meaningful once ≥1 lunar
    year of records exists."""
    trail = sorted(trail, key=lambda r: r["date"])
    st = {"tracking": bool(trail), "first_tracked": trail[0]["date"] if trail else None,
          "records": len(trail), "hawl_start": None, "above": False,
          "zakatable": None, "nisab": None, "min_since_start": None,
          "projected_due": None, "lunar_year_complete": False}
    if not trail:
        return st
    last = trail[-1]
    st.update({"above": last["above"], "zakatable": last["zakatable"], "nisab": last["nisab"]})
    if last["above"]:
        run = []
        for r in reversed(trail):
            if r["above"]:
                run.append(r)
            else:
                break
        run.reverse()
        st["hawl_start"] = run[0]["date"]
        st["min_since_start"] = round(min(r["zakatable"] for r in run), 2)
        due = _hijri_anniv(run[0]["date"], 1)
        st["projected_due"] = due
        st["lunar_year_complete"] = bool(due and last["date"] >= due)
    return st


def _hawl_snapshot(today_iso):
    """Record today's zakatable total + nisab crossing. Idempotent per day."""
    cfg = _zakat_cfg()
    total, parts = _zakatable_total()
    nisab = cfg["nisab"]
    rec = {"date": today_iso, "zakatable": total, "nisab": round(nisab, 2),
           "above": total >= nisab, "nisab_estimated": cfg["nisab_estimated"]}
    path = os.path.join(DATA, "hawl_trail.json")
    try:
        trail = json.load(open(path, encoding="utf-8"))
        if not isinstance(trail, list):
            trail = []
    except Exception:
        trail = []
    trail = [r for r in trail if r.get("date") != today_iso]   # replace same-day
    trail.append(rec)
    trail.sort(key=lambda r: r["date"])
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(trail, fh, ensure_ascii=False, indent=0)
    state = _hawl_recompute(trail)
    state["parts"] = parts
    state["nisab_estimated"] = cfg["nisab_estimated"]
    with open(os.path.join(DATA, "hawl_state.json"), "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)
    audit("hawl_snapshot", date=today_iso, zakatable=total, nisab=round(nisab, 2), above=rec["above"])
    return state


@app.get("/api/hawl")
def api_hawl():
    """Read the current hawl state (no side effects). Groundwork surface only."""
    cfg = _zakat_cfg()
    try:
        trail = json.load(open(os.path.join(DATA, "hawl_trail.json"), encoding="utf-8"))
    except Exception:
        trail = []
    state = _hawl_recompute(trail)
    state["nisab_config"] = {"nisab": round(cfg["nisab"], 2), "estimated": cfg["nisab_estimated"],
                             "estimate": cfg["nisab_estimate"], "set": not cfg["nisab_estimated"]}
    return state


@app.post("/api/hawl/snapshot")
async def api_hawl_snapshot(request: Request):
    """Record today's snapshot. Called nightly by scripts/hawl_track.py; safe to
    re-run (idempotent per day)."""
    p = {}
    try:
        p = await request.json()
    except Exception:
        pass
    today = (p.get("date") or datetime.now().strftime("%Y-%m-%d"))
    return _hawl_snapshot(today)


@app.post("/api/zakat/settings")
async def api_zakat_settings(request: Request):
    """Set your verified nisab (the one /settings write for this layer)."""
    p = await request.json()
    cfg = dict(_yaml_load("zakat.yaml") or {})
    if "nisab_sar" in p:
        v = p["nisab_sar"]
        cfg["nisab_sar"] = (None if v in (None, "", "null") else round(float(v), 2))
    if "gold_price_sar_per_gram" in p and p["gold_price_sar_per_gram"] not in (None, ""):
        cfg["gold_price_sar_per_gram"] = round(float(p["gold_price_sar_per_gram"]), 2)
    _yaml_save("zakat.yaml", cfg)
    audit("zakat_settings", **{k: cfg.get(k) for k in ("nisab_sar", "gold_price_sar_per_gram")})
    return api_hawl()


# ── Firefly-native Rules manager (WAVE R — the crown find) ─────────────────
# Firefly has a full server-side rule engine (rule-groups → rules → triggers →
# actions) that runs on store/update of any journal and can be triggered over
# existing transactions. Until now our only "rules" were import-time patterns in
# merchants.yaml (categorize on ingest only). This surfaces the native engine:
# list/create/delete/toggle, migrate the merchant map into it, preview matches,
# and apply a rule across the ledger. Writes are deliberate + audited.
_IMPORT_GROUP = "HAKIM (imported)"
_RULE_DATES = "start=2015-01-01&end=2035-12-31"   # wide but within Firefly's accepted bounds (2100 → 422)


def _rule_group_id(title=_IMPORT_GROUP, create=True):
    for g in ff_all("rule-groups"):
        if g["attributes"]["title"] == title:
            return g["id"]
    if not create:
        return None
    d = ff("POST", "rule-groups", {"title": title,
           "description": "Auto-migrated from the importer merchant map", "active": True})
    return d["data"]["id"]


def _rx_to_contains(pattern):
    """A regex merchant pattern → the literal description_contains fragments Firefly
    triggers use. Splits top-level | alternations and unescapes backslash escapes.
    Imperfect by nature (regex ⊃ substring) — honest best-effort, flagged in the UI."""
    out = []
    for part in re.split(r"\|", pattern or ""):
        s = re.sub(r"\\(.)", r"\1", part).strip()
        if s:
            out.append(s)
    return out


def _rule_view(r):
    a = r["attributes"]
    return {"id": r["id"], "title": a["title"], "active": a.get("active", True),
            "strict": a.get("strict", True), "stop": a.get("stop_processing", False),
            "group": a.get("rule_group_title") or "",
            "triggers": [{"type": t["type"], "value": t["value"]} for t in a.get("triggers", [])],
            "actions": [{"type": t["type"], "value": t["value"]} for t in a.get("actions", [])]}


def _rule_body(a, active=None):
    """Full PUT body from a rule's attributes (Firefly wants the whole object on update)."""
    return {"title": a["title"], "rule_group_id": a.get("rule_group_id"),
            "trigger": a.get("trigger", "store-journal"),
            "active": a.get("active", True) if active is None else active,
            "strict": a.get("strict", True), "stop_processing": a.get("stop_processing", False),
            "triggers": [{"type": t["type"], "value": t["value"]} for t in a.get("triggers", [])],
            "actions": [{"type": t["type"], "value": t["value"]} for t in a.get("actions", [])]}


@app.get("/api/rules")
def api_rules():
    rules = [_rule_view(r) for r in ff_all("rules")]
    merch = _merch_yaml().get("rules", [])
    titles = {r["title"] for r in rules}
    unmigrated = sum(1 for m in merch
                     if (m.get("merchant") or m.get("category") or m.get("pattern") or "")[:60] not in titles)
    return {"rules": rules, "count": len(rules),
            "importer_total": len(merch), "importer_unmigrated": unmigrated}


@app.get("/api/rules/impact")
def api_rules_impact():
    """Queue-impact estimate: of the current To-review transactions, how many match at
    least one importer rule (i.e. would auto-resolve once native rules run). Read-only."""
    pats = []
    for m in _merch_yaml().get("rules", []):
        try:
            pats.append(re.compile(m["pattern"], re.I))
        except Exception:
            continue
    q = [t for t in all_txns() if t["category"] == REVIEW_CATEGORY]   # full queue (matches Desk badge)
    # transfers/SADAD aren't merchant purchases — rules-by-description can't address them; count separately
    addressable = [t for t in q if not TRANSFERISH.search(t["desc"])]
    hit = sum(1 for t in addressable if any(rx.search(t["desc"] or "") for rx in pats))
    return {"queue": len(q), "addressable": len(addressable), "matched": hit,
            "transfers": len(q) - len(addressable),
            "pct": round(hit / len(addressable) * 100) if addressable else 0}


@app.post("/api/rules/migrate")
async def api_rules_migrate(request: Request):
    """Create a Firefly native rule per importer merchant entry (idempotent by title).
    category → set_category; tags → add_tag; | alternations → OR of description_contains."""
    grp = _rule_group_id()
    existing = {_rule_view(r)["title"] for r in ff_all("rules")}
    created, skipped = 0, 0
    for m in _merch_yaml().get("rules", []):
        title = (m.get("merchant") or m.get("category") or m.get("pattern") or "rule")[:60]
        contains = _rx_to_contains(m.get("pattern", ""))
        actions = []
        cat = m.get("category")
        if cat and cat != REVIEW_CATEGORY:
            actions.append({"type": "set_category", "value": cat})
        for tg in (m.get("tags") or []):
            actions.append({"type": "add_tag", "value": tg})
        if title in existing or not contains or not actions:
            skipped += 1
            continue
        ff("POST", "rules", {"title": title, "rule_group_id": grp, "trigger": "store-journal",
           "active": True, "strict": len(contains) == 1, "stop_processing": False,
           "triggers": [{"type": "description_contains", "value": c} for c in contains],
           "actions": actions})
        existing.add(title)
        created += 1
    audit("rules_migrate", created=created, skipped=skipped)
    return {"ok": True, "created": created, "skipped": skipped}


def _make_native_rule(sample, cat, tags):
    """R3: 'make this a rule' — mirror an importer merchant rule into Firefly's engine so
    it runs on existing + future transactions, not just at import. Idempotent by title."""
    frag = merchant_key(sample)[:40].strip()
    if not frag:
        return
    title = frag[:60]
    if any(r["attributes"]["title"] == title for r in ff_all("rules")):
        return
    actions = []
    if cat and cat != REVIEW_CATEGORY:
        actions.append({"type": "set_category", "value": cat})
    for tg in (tags or []):
        actions.append({"type": "add_tag", "value": tg})
    if not actions:
        return
    ff("POST", "rules", {"title": title, "rule_group_id": _rule_group_id(),
       "trigger": "store-journal", "active": True, "strict": True, "stop_processing": False,
       "triggers": [{"type": "description_contains", "value": frag}], "actions": actions})
    audit("rule_native_create", title=title)


@app.post("/api/rule/create")
async def api_rule_create(request: Request):
    p = await request.json()
    contains = [c.strip() for c in (p.get("contains") or []) if c.strip()]
    if not contains:
        return {"ok": False, "error": "at least one 'description contains' is required"}
    actions = []
    if p.get("category"):
        actions.append({"type": "set_category", "value": p["category"]})
    for tg in (p.get("tags") or []):
        actions.append({"type": "add_tag", "value": tg})
    if not actions:
        return {"ok": False, "error": "a rule needs at least one action (category or tag)"}
    grp = _rule_group_id(p.get("group") or _IMPORT_GROUP)
    d = ff("POST", "rules", {"title": (p.get("title") or contains[0])[:60], "rule_group_id": grp,
           "trigger": "store-journal", "active": True, "strict": len(contains) == 1,
           "stop_processing": False,
           "triggers": [{"type": "description_contains", "value": c} for c in contains],
           "actions": actions})
    audit("rule_create", title=p.get("title"), contains=contains)
    return {"ok": True, "id": d["data"]["id"]}


@app.post("/api/rule/toggle")
async def api_rule_toggle(request: Request):
    p = await request.json()
    rid = str(p["id"])
    a = ff("GET", f"rules/{rid}")["data"]["attributes"]
    newactive = not a.get("active", True)
    ff("PUT", f"rules/{rid}", _rule_body(a, active=newactive))
    audit("rule_toggle", id=rid, active=newactive)
    return {"ok": True, "active": newactive}


@app.post("/api/rule/delete")
async def api_rule_delete(request: Request):
    p = await request.json()
    ff("DELETE", f"rules/{p['id']}")
    audit("rule_delete", id=p["id"])
    return {"ok": True}


@app.get("/api/rule/{rid}/test")
def api_rule_test(rid: str):
    """Preview: transactions matching this rule's triggers (Firefly's own test endpoint).
    Read-only — changes nothing."""
    try:
        rows = ff("GET", f"rules/{rid}/test?{_RULE_DATES}").get("data", [])
        sample = []
        for g in rows[:8]:
            ga = g["attributes"]["transactions"][0]
            sample.append({"desc": ga.get("description"), "amount": ga.get("amount"),
                           "date": (ga.get("date") or "")[:10]})
        return {"ok": True, "matches": len(rows), "sample": sample}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


@app.post("/api/rule/{rid}/apply")
async def api_rule_apply(rid: str):
    """Run this rule over existing transactions (Firefly trigger endpoint). WRITES
    categories/tags on matched txns — deliberate, audited."""
    ff("POST", f"rules/{rid}/trigger?{_RULE_DATES}", {})
    audit("rule_apply", id=rid)
    return {"ok": True}


# ── Rule proposals — the page's living heart. The system surfaces recurring merchants that
# have NO rule yet and asks Hisham to teach it, ONE at a time, ranked by impact. His two answers
# become law: "Confident" builds the rule + applies it now; "Not sure yet" builds NOTHING and waits
# until the merchant recurs N more times before asking again — never a wrong lesson from thin evidence.
_PROPOSAL_STORE = "rule_proposals.yaml"      # {key: {status: snoozed|dismissed, count, ts}}
_PROPOSAL_RESURFACE = 2                       # a snoozed proposal returns after this many MORE sightings
# descriptions that are not merchants: review stamps, corrections, opening balances, bare wallet codes
_PROPOSAL_NOISE = re.compile(r"^\s*(reviewed by|balance correction|cash count|opening balance|"
                             r"⚖|adjustment)", re.I)


def _proposal_store():
    d = _yaml_load(_PROPOSAL_STORE)
    return d if isinstance(d, dict) else {}


def _proposal_frag(sample):
    """A literal description-substring that identifies this merchant (for description_contains).
    merchant_key strips card numbers + long digit runs; we cut at the CITY:/MCC- noise so the
    fragment is the clean merchant name (e.g. 'al akaber coffe') — case-insensitive substring match."""
    frag = merchant_key(sample)
    for cut in (" city:", " mcc-", " mcc ", "city:"):
        frag = frag.split(cut)[0]
    return frag.strip()[:40]


def _person_of_account(name):
    nl = (name or "").lower()
    if "sarah" in nl:
        return "Sarah"
    if "hisham" in nl or "hesham" in nl:
        return "Hisham"
    return None


@app.get("/api/rules/proposals")
def api_rule_proposals():
    """Recurring (≥2) merchants with no covering rule yet, ranked by impact (occurrences × recency).
    Transfers/SADAD are excluded (a description rule can't address them). Snoozed proposals stay hidden
    until they recur _PROPOSAL_RESURFACE more times; dismissed ones never return."""
    import datetime as _dt
    today = _dt.date.today()
    # fragments already covered by a live Firefly rule → those merchants are settled, skip them
    ruled = []
    for r in ff_all("rules"):
        a = r.get("attributes", {})
        if not a.get("active", True):
            continue
        for tr in a.get("triggers", []):
            if tr.get("type") == "description_contains" and (tr.get("value") or "").strip():
                ruled.append(tr["value"].lower())

    def is_ruled(desc):
        dl = (desc or "").lower()
        return any(frag in dl for frag in ruled)

    groups = {}
    for t in all_txns():                          # excluded rows already dropped
        if t.get("type") not in ("withdrawal", "deposit"):
            continue                              # transfers (incl. wallet top-ups) aren't merchant rules
        desc = t.get("desc") or ""
        if TRANSFERISH.search(desc) or _PROPOSAL_NOISE.search(desc):
            continue                              # transfers/SADAD + review-stamp/correction noise
        key = merchant_key(desc)
        if not key or len(key) < 3 or is_ruled(desc):
            continue
        g = groups.setdefault(key, {"key": key, "label": merchant_display(desc), "sample": desc,
                                    "count": 0, "total": 0.0, "accounts": set(), "dates": [],
                                    "cats": {}, "newest": ""})
        g["count"] += 1
        if t.get("type") == "withdrawal":
            g["total"] += t.get("amount") or 0
        g["accounts"].add(t.get("account") or "?")
        g["dates"].append(t.get("date") or "")
        c = t.get("category") or "To review"
        g["cats"][c] = g["cats"].get(c, 0) + 1
        if (t.get("date") or "") > g["newest"]:
            g["newest"] = t.get("date") or ""

    store = _proposal_store()
    props, snoozed_hidden = [], 0
    for key, g in groups.items():
        if g["count"] < 2:
            continue
        st = store.get(key) or {}
        resurfaced = None
        if st.get("status") == "dismissed":
            continue
        if st.get("status") == "snoozed":
            if g["count"] < (st.get("count", 0) + _PROPOSAL_RESURFACE):
                snoozed_hidden += 1
                continue
            resurfaced = st.get("count")          # "appeared N more times since you deferred"
        # recency: days since the newest sighting → impact = count × recency factor
        days = 999
        try:
            y, m, d = (int(x) for x in g["newest"].split("-"))
            days = (today - _dt.date(y, m, d)).days
        except Exception:
            pass
        recency = max(0.35, 1.0 - days / 180.0)
        persons = sorted({p for a in g["accounts"] if (p := _person_of_account(a))})
        cur_cat = max(g["cats"].items(), key=lambda kv: kv[1])[0] if g["cats"] else "To review"
        props.append({
            "key": key, "label": g["label"], "match_text": _proposal_frag(g["sample"]),
            "sample": g["sample"][:80], "count": g["count"], "total": round(g["total"], 2),
            "accounts": sorted(g["accounts"]), "persons": persons,
            "person_hint": (persons[0] if len(persons) == 1 else ("Both" if len(persons) > 1 else "")),
            "dates": sorted(g["dates"], reverse=True)[:3], "current_category": cur_cat,
            "resurfaced_from": resurfaced,
            "impact": round(g["count"] * recency, 2)})
    props.sort(key=lambda p: -p["impact"])
    return {"proposals": props, "count": len(props), "snoozed_hidden": snoozed_hidden}


@app.post("/api/rules/proposal/defer")
async def api_rule_proposal_defer(request: Request):
    """'Not sure yet' — build NO rule; remember the count now so the proposal returns only after it
    recurs _PROPOSAL_RESURFACE more times. Careful learning: never a rule from thin evidence."""
    p = await request.json()
    key = (p.get("key") or "").strip()
    if not key:
        return {"ok": False, "error": "key required"}
    store = _proposal_store()
    store[key] = {"status": "snoozed", "count": int(p.get("count") or 0),
                  "ts": _date.today().isoformat()}
    _yaml_save(_PROPOSAL_STORE, store)
    audit("proposal_defer", key=key, count=p.get("count"))
    return {"ok": True, "resurface_after": _PROPOSAL_RESURFACE}


@app.post("/api/rules/proposal/dismiss")
async def api_rule_proposal_dismiss(request: Request):
    """'Not a rule' — a genuine one-off that happens to repeat. Never propose this merchant again."""
    p = await request.json()
    key = (p.get("key") or "").strip()
    if not key:
        return {"ok": False, "error": "key required"}
    store = _proposal_store()
    store[key] = {"status": "dismissed", "ts": _date.today().isoformat()}
    _yaml_save(_PROPOSAL_STORE, store)
    audit("proposal_dismiss", key=key)
    return {"ok": True}


@app.post("/api/rules/proposal/confirm")
async def api_rule_proposal_confirm(request: Request):
    """'Confident' — build the Firefly rule now (description_contains → set_category + person/tag adds)
    AND apply it to existing matches, settling the merchant forever. Clears any prior snooze."""
    p = await request.json()
    contains = (p.get("match_text") or "").strip()
    category = (p.get("category") or "").strip()
    tags = [t for t in (p.get("tags") or []) if t]
    if not contains:
        return {"ok": False, "error": "match text required"}
    if not category and not tags:
        return {"ok": False, "error": "pick a category (or at least a person/tag)"}
    actions = []
    if category:
        actions.append({"type": "set_category", "value": category})
    for tg in tags:
        actions.append({"type": "add_tag", "value": tg})
    grp = _rule_group_id()
    title = (p.get("label") or contains)[:60]
    d = ff("POST", "rules", {"title": title, "rule_group_id": grp, "trigger": "store-journal",
           "active": True, "strict": True, "stop_processing": False,
           "triggers": [{"type": "description_contains", "value": contains}], "actions": actions})
    rid = d["data"]["id"]
    applied = True
    try:
        ff("POST", f"rules/{rid}/trigger?{_RULE_DATES}", {})   # apply to existing matches now
    except Exception as e:
        applied = False
        print("proposal confirm apply failed", e, flush=True)
    # a settled merchant leaves the snooze/dismiss store (it's now rule-covered)
    store = _proposal_store()
    if (p.get("key") or "") in store:
        store.pop(p["key"], None)
        _yaml_save(_PROPOSAL_STORE, store)
    audit("proposal_confirm", key=p.get("key"), title=title, category=category, tags=tags, applied=applied)
    return {"ok": True, "id": rid, "applied": applied}


TYPE_MAP = {"cash": ("asset", "defaultAsset"), "bank": ("asset", "defaultAsset"),
            "digital": ("asset", "defaultAsset"), "receivable": ("asset", "defaultAsset"),
            "gold": ("asset", "defaultAsset"),   # zakatable metal — counts toward nisab
            "card": ("asset", "ccAsset"),
            # Wave M — investment / metal / financing subtypes (foundation; entry-flows are part 2)
            "certificate": ("asset", "defaultAsset"),   # شهادات — principal restricted until maturity
            "fund": ("asset", "defaultAsset"),           # صناديق — units × NAV
            "etf": ("asset", "defaultAsset"),            # units × price
            "silver": ("asset", "defaultAsset"),         # zakatable metal (grams × price)
            "hissar": ("asset", "defaultAsset"),         # HISSAR blind capital (Farm / Position)
            "equity": ("asset", "defaultAsset"),         # equity in a company (book value, M12)
            "loan": ("liability", None),                 # Tawarruq / personal financing
            "bnpl": ("liability", None),                 # Tabby / Tamara
            "lease": ("liability", None),                # lease-to-own
            # F: operator-added Other assets (home/car/valuables) + Other liabilities (loans)
            "other_asset": ("asset", "defaultAsset"), "other_liability": ("liability", None)}

# kinds that carry a manual current value + as-of stamp (Holdings / staleness / update reminder)
_POSITION_KINDS = {"certificate", "fund", "etf", "gold", "silver", "hissar", "equity"}
# kinds that join the hawl zakatable base beyond plain liquid assets
_ZAKATABLE_EXTRA = {"gold", "silver", "certificate", "fund", "etf"}


@app.post("/api/account/add")
async def account_add(req: Request):
    p = await req.json()
    ensure_currency(p.get("currency", "SAR"))
    atype = p["type"]
    # A fund/ETF's opening balance IS its cost basis = units × purchase price per unit.
    if atype in ("fund", "etf") and not p.get("opening") and p.get("units") and p.get("purchase_price"):
        p["opening"] = round(float(p["units"]) * float(p["purchase_price"]), 2)
    t, role = TYPE_MAP.get(atype, ("asset", "defaultAsset"))
    body = {"name": p["name"], "type": t, "currency_code": p.get("currency", "SAR"),
            "notes": p.get("notes", "")}
    if role:
        body["account_role"] = role
    if role == "ccAsset":
        body["credit_card_type"] = "monthlyFull"
        body["monthly_payment_date"] = "2026-01-01"
    if t == "liability":
        body["liability_type"] = "debt"
        body["liability_direction"] = "credit"
        body["interest"] = "0"
        body["interest_period"] = "monthly"
    if p.get("opening"):
        ob = abs(float(p["opening"]))
        # CANONICAL SIGN: a debt you owe must be stored NEGATIVE, so paydowns (withdrawal→liability)
        # reduce it toward zero. A positive opening on a credit liability inverts the sign and makes
        # payments GROW the debt (the flynas polarity bug). Owner types "600 owed" → we store −600.
        if t == "liability":
            ob = -ob
        body["opening_balance"] = f"{ob:.2f}"
        body["opening_balance_date"] = p.get("opening_date") or datetime.now().strftime("%Y-%m-%d")
    new = ff("POST", "accounts", body)
    nid = new["data"]["id"]
    # remember the classification for grouping (F + Wave M) — everything but the plain defaults
    if atype not in ("cash", "bank", "digital", "receivable", "card"):
        d = _yaml_load("account_kinds.yaml")
        d.setdefault("kinds", {})[str(nid)] = atype
        _yaml_save("account_kinds.yaml", d)
    # position metadata (as-of, restricted-until, contract terms) for investment/metal subtypes
    if atype in _POSITION_KINDS:
        pos = {k: p[k] for k in ("as_of", "restricted_until", "rate", "maturity", "rate_type",
                                 "payout_freq", "units", "nav") if p.get(k) not in (None, "")}
        # A certificate's PRINCIPAL is locked at the opening amount and never moves — the profit is the
        # living part. Freeze it here so payout deposits arriving into the account don't inflate the
        # figure the profit is computed from (the 1583.33→1608.40 bug).
        if atype == "certificate" and p.get("opening"):
            pos["principal"] = round(abs(float(p["opening"])), 2)
        # A fund/ETF is unit-priced: cost basis + a monthly PRICE history feed the price-vs-total-return
        # story. cost_basis = purchases + reinvested dividends (→ avg price, realised gain); capital_in =
        # external money only (→ total-return base). Seed month one of the price history at purchase.
        if atype in ("fund", "etf"):
            pos["fund_type"] = p.get("fund_type") or "accumulating"
            u = float(p.get("units") or 0)
            pp = float(p.get("purchase_price") or 0)
            if u > 0 and pp > 0:
                cb = round(u * pp, 2)
                pos["cost_basis"], pos["capital_in"] = cb, cb
                pos["avg_price"] = round(pp, 6)
                pos["price_history"] = [{"date": (p.get("as_of") or datetime.now().strftime("%Y-%m-%d"))[:10],
                                         "price": round(pp, 6), "units": u}]
        pos.setdefault("as_of", datetime.now().strftime("%Y-%m-%d"))
        _positions_save(str(nid), pos)
    acct_log("created", id=nid, name=p["name"], type=atype,
             currency=p.get("currency"), opening=p.get("opening"))
    return {"ok": True, "id": nid}


@app.get("/api/positions")
def api_positions():
    """Holdings — investment / metal / HISSAR / equity positions: manual value + as-of + staleness
    (>60d dim) + restricted-until (certificates locked to maturity). Feeds the Accounts Holdings
    view + the monthly update reminder + the net-worth restricted-vs-available split."""
    kinds = _acct_kinds_map()
    pos = _positions()
    today = _date.today()
    out, restricted = [], 0.0
    for a in ff_all("accounts", type="asset"):
        at = a["attributes"]
        if not at.get("active", True) or kinds.get(a["id"]) not in _POSITION_KINDS:
            continue
        k = kinds.get(a["id"])
        p = pos.get(a["id"]) or {}
        bal = round(float(at.get("current_balance") or 0), 2)
        as_of = p.get("as_of")
        stale_days = None
        if as_of:
            try:
                stale_days = (today - _date.fromisoformat(as_of[:10])).days
            except Exception:
                stale_days = None
        ru = p.get("restricted_until")
        is_restricted = bool(ru and ru[:10] >= today.isoformat())
        cur = at.get("currency_code") or "SAR"
        val_sar = to_sar(bal, cur)                     # FX-correct: EGP/USD positions → SAR
        if is_restricted:
            restricted += val_sar
        out.append({"id": a["id"], "name": at["name"], "kind": k,
                    "group": _group2(a["id"], at["name"], at.get("account_role"), "asset"),
                    "value": bal, "value_sar": val_sar, "currency": cur,
                    "as_of": as_of, "stale_days": stale_days,
                    "stale": (stale_days is not None and stale_days > 60),
                    "restricted_until": ru, "restricted": is_restricted,
                    "rate": p.get("rate"), "maturity": p.get("maturity"),
                    "payout_freq": p.get("payout_freq"), "units": p.get("units"), "nav": p.get("nav")})
    out.sort(key=lambda x: -x["value_sar"])
    total = round(sum(x["value_sar"] for x in out), 2)   # SAR-converted (mixed-currency honest)
    restricted = round(restricted, 2)
    return {"positions": out, "total": total, "restricted": restricted,
            "available_of_total": round(total - restricted, 2), "currency": "SAR",
            "stale_count": sum(1 for x in out if x["stale"]), "count": len(out)}


@app.post("/api/position/update")
async def position_update(req: Request):
    """Monthly quick-update for a position: stamp as-of, set restricted-until / contract terms, and
    (optionally) update the current value. A value change posts a NON-CASH revaluation adjustment
    tagged 'excluded' — it moves the balance (net worth follows) but never pollutes income/spend."""
    p = await req.json()
    aid = str(p["id"])
    fields = {"as_of": (p.get("as_of") or datetime.now().strftime("%Y-%m-%d"))[:10]}
    for k in ("restricted_until", "rate", "maturity", "payout_freq", "units", "nav"):
        if p.get(k) not in (None, ""):
            fields[k] = p[k]
    _positions_save(aid, fields)
    if p.get("value") not in (None, ""):
        accs = {a["id"]: a for a in accounts()}
        a = accs.get(aid)
        if a:
            diff = round(float(p["value"]) - float(a["balance"]), 2)
            if abs(diff) >= 0.01:
                date = datetime.now().strftime("%Y-%m-%d")
                base = {"date": date, "description": "Position revaluation (non-cash)",
                        "notes": f"as-of {fields['as_of']}", "amount": f"{abs(diff):.2f}",
                        "tags": ["revaluation", "excluded", "manual", "trust:verified"]}
                if diff > 0:
                    ff("POST", "transactions", {"transactions": [dict(base, type="deposit",
                       source_name="Revaluation", destination_id=aid, category_name="")]})
                else:
                    ff("POST", "transactions", {"transactions": [dict(base, type="withdrawal",
                       source_id=aid, destination_name="Revaluation", category_name="")]})
    audit("position_update", id=aid, value=p.get("value"))
    return {"ok": True}


# ── Financing schedules (loans/BNPL/lease) — shared engine; loans are the first consumer ──
# The liability balance = principal outstanding (the honest economic position; fixed profit is a
# future cost that accrues as you pay, not a present debt). Each payment splits principal (pays
# down the liability, a transfer) + financing cost (an expense → "Bank & fees: financing cost",
# the Riba-lens feedstock). Every payment returns a before/after liability balance proof.
def _schedules():
    d = _yaml_load("schedules.yaml")
    return d.get("schedules", {}) if isinstance(d, dict) else {}


def _schedule_save(aid, sched):
    with _lock:
        d = _yaml_load("schedules.yaml")
        if not isinstance(d, dict):
            d = {}
        d.setdefault("schedules", {})[str(aid)] = sched
        _yaml_save("schedules.yaml", d)


def _gen_loan_schedule(principal, annual_rate, term, start, monthly=None):
    """Declining-balance amortization — the Saudi standard SAMA mandates. Each month's profit is
    computed on the REMAINING balance (rate ÷ 12), so early payments are profit-heavy and late ones
    principal-heavy. The last installment absorbs rounding so Σprincipal == financed amount exactly.
    Emits every SAMA-required column per row: payment · profit · principal · balance-after."""
    principal, term = float(principal), int(term)
    r = float(annual_rate or 0) / 100.0 / 12.0
    if not monthly or float(monthly) <= 0:
        monthly = round(principal * r / (1 - (1 + r) ** -term), 2) if r > 0 else round(principal / term, 2)
    monthly = float(monthly)
    inst, d, bal = [], _date.fromisoformat(start[:10]), principal
    crossover = None
    for n in range(1, term + 1):
        profit = round(bal * r, 2)
        if n < term:
            prin = round(monthly - profit, 2)
            pay = round(monthly, 2)
        else:                                   # final: clear the exact remaining balance
            prin = round(bal, 2)
            pay = round(prin + profit, 2)
        bal = round(bal - prin, 2)
        if crossover is None and prin >= profit:
            crossover = n
        inst.append({"n": n, "date": d.isoformat(), "amount": pay, "principal": prin,
                     "cost": profit, "balance_after": max(0.0, bal), "paid": False})
        d = _add_freq(d, "monthly")
    total_repayable = round(sum(i["amount"] for i in inst), 2)
    total_cost = round(sum(i["cost"] for i in inst), 2)
    return {"kind": "loan", "principal": round(principal, 2), "total_repayable": total_repayable,
            "term": term, "monthly": round(monthly, 2), "start": start[:10], "total_cost": total_cost,
            "annual_rate": round(float(annual_rate or 0), 3), "crossover": crossover,
            "cost_method": "declining-balance (SAMA)", "installments": inst}


@app.post("/api/loan/setup")
async def loan_setup(req: Request):
    """Set up a loan on declining-balance amortization. Asks financed amount · annual profit rate ·
    term · start (· monthly, computed by annuity but editable if the contract differs)."""
    p = await req.json()
    aid = str(p["account_id"])
    # accept annual_rate directly, or derive it from a stated total_repayable (legacy callers)
    rate = p.get("annual_rate")
    if rate in (None, "") and p.get("total_repayable"):
        rate = 0.0
    sched = _gen_loan_schedule(p["principal"], rate or 0, p["term"],
                               (p.get("start") or datetime.now().strftime("%Y-%m-%d")),
                               monthly=p.get("monthly"))
    _schedule_save(aid, sched)
    audit("loan_setup", id=aid, principal=p["principal"], rate=rate, term=p["term"])
    return {"ok": True, "schedule": sched, "monthly": sched["monthly"],
            "total_repayable": sched["total_repayable"], "total_cost": sched["total_cost"]}


def _real_discharges(aid):
    """Real paydown transactions against a liability (withdrawal → destination = this account).
    These are the ONLY proof that an installment was paid — a schedule 'paid' flag means nothing
    without one of these behind it. Opening balance is excluded."""
    out = []
    try:
        for g in account_txns(str(aid)):
            for s in g["attributes"]["transactions"]:
                if s.get("destination_id") == str(aid) and s.get("type") == "withdrawal":
                    out.append({"amount": round(float(s["amount"]), 2), "date": (s.get("date") or "")[:10],
                                "desc": s.get("description")})
    except Exception:
        pass
    return out


@app.get("/api/schedule")
def api_schedule(id: str):
    aid = str(id)
    s = _schedules().get(aid)
    if not s:
        return {"ok": False}
    paid = [i for i in s["installments"] if i["paid"]]
    nxt = next((i for i in s["installments"] if not i["paid"]), None)
    # INTEGRITY: a schedule 'paid' flag is only true if a real discharge transaction backs it.
    discharges = _real_discharges(aid)
    bal = abs(round(float({a["id"]: a for a in accounts()}.get(aid, {}).get("balance") or 0), 2))
    remaining = round(sum(i["amount"] for i in s["installments"] if not i["paid"]), 2)
    paid_marked = len(paid)
    proven = len(discharges)
    balance_ok = abs(remaining - bal) < 0.02
    paid_ok = paid_marked <= proven          # never claim more paid than are proven
    invariant_ok = balance_ok and paid_ok
    mismatch = None
    if not paid_ok:
        mismatch = (f"{paid_marked} installment(s) are marked paid, but only {proven} real payment(s) "
                    f"are linked to this debt. Link the paid charges so the ledger proves it.")
    elif not balance_ok:
        mismatch = (f"The remaining installments add up to SAR {remaining:.2f}, but the account owes "
                    f"SAR {bal:.2f}. Re-declare the plan so they agree.")
    out = {"ok": True, "schedule": s, "next": nxt, "paid_count": paid_marked,
           "cost_to_date": round(sum(i["cost"] for i in paid), 2),
           "principal_paid": round(sum(i["principal"] for i in paid), 2),
           "remaining": remaining, "balance": bal, "paid_before": s.get("paid_before", 0),
           "installments_total": s.get("installments_total"),
           "linked_discharges": proven, "discharges": sorted(discharges, key=lambda x: x["date"]),
           "invariant_ok": invariant_ok, "mismatch": mismatch}
    if s.get("kind") in ("loan", "lease"):
        unpaid = [i for i in s["installments"] if not i["paid"]]
        rem_profit = round(sum(i["cost"] for i in unpaid), 2)
        rem_principal = round(sum(i["principal"] for i in unpaid), 2)
        next3_profit = round(sum(i["cost"] for i in unpaid[:3]), 2)     # SAMA early-settlement rule
        principal_balance = bal          # the live account balance IS the outstanding principal
        out["loan"] = {
            "principal": s.get("principal"), "annual_rate": s.get("annual_rate"),
            "total_repayable": s.get("total_repayable"), "total_cost": s.get("total_cost"),
            "crossover": s.get("crossover"), "cost_method": s.get("cost_method"),
            "paid_principal": round(sum(i["principal"] for i in paid), 2),
            "paid_profit": round(sum(i["cost"] for i in paid), 2),
            "remaining_profit": rem_profit, "principal_balance": round(principal_balance, 2),
            "next_split": ({"amount": nxt["amount"], "profit": nxt["cost"], "principal": nxt["principal"]}
                           if nxt else None),
            "settle_estimate": round(principal_balance + next3_profit, 2),
            "settle_next3_profit": next3_profit}
    return out


@app.post("/api/financing/pay")
async def financing_pay(req: Request):
    """Record a financing payment: principal (transfer paying down the liability) + cost (expense).
    Returns a BEFORE/AFTER liability balance proof. Deliberate write — audited."""
    p = await req.json()
    aid, from_id = str(p["account_id"]), str(p["from_account"])
    s = _schedules().get(aid)
    inst = None
    if s:
        inst = next((i for i in s["installments"] if not i["paid"]), None)
        if not inst:
            return {"ok": False, "error": "schedule already fully paid"}
        principal = round(float(p.get("principal", inst["principal"])), 2)
        cost = round(float(p.get("cost", inst["cost"])), 2)
    else:
        principal = round(float(p.get("principal") or 0), 2)
        cost = round(float(p.get("cost") or 0), 2)
    accs = {a["id"]: a for a in accounts()}
    liab_before = accs.get(aid, {}).get("balance")
    # payment date = today (when the money actually moves). A future/scheduled date would post but
    # not affect current_balance yet — proven the correct shape is a withdrawal asset→liability.
    date = p.get("date") or datetime.now().strftime("%Y-%m-%d")
    if principal > 0:            # withdrawal asset → liability (Firefly's debt-paydown shape)
        ff("POST", "transactions", {"transactions": [{"type": "withdrawal", "date": date,
            "amount": f"{principal:.2f}", "description": "Financing payment — principal",
            "source_id": from_id, "destination_id": aid, "category_name": "",
            "tags": ["financing", "manual", "trust:verified"]}]})
    if cost > 0:                 # cost → expense (Riba-lens feedstock)
        ff("POST", "transactions", {"transactions": [{"type": "withdrawal", "date": date,
            "amount": f"{cost:.2f}", "description": "Financing payment — cost", "source_id": from_id,
            "destination_name": "Financing cost", "category_name": "Bank & fees: financing cost",
            "tags": ["financing", "riba", "manual", "trust:verified"]}]})
    if s and inst:
        inst["paid"] = True
        _schedule_save(aid, s)
    liab_after = {a["id"]: a for a in accounts()}.get(aid, {}).get("balance")
    discharged = round(abs(liab_before or 0) - abs(liab_after or 0), 2)
    retired = _maybe_retire(aid)
    audit("financing_pay", id=aid, principal=principal, cost=cost,
          liab_before=liab_before, liab_after=liab_after, discharged=discharged, retired=retired)
    return {"ok": True, "principal": principal, "cost": cost, "retired": retired,
            "liability_before": liab_before, "liability_after": liab_after,
            "principal_discharged": discharged, "proof_ok": abs(discharged - principal) < 0.02}


_SETTLE_REASONS = {
    "pre-ledger": "predates the ledger (no data for that month)",
    "paid-by-other": "someone else paid it",
    "outside": "paid outside tracked accounts",
    "other": "other",
}


@app.post("/api/schedule/settle-manual")
async def schedule_settle_manual(req: Request):
    """Settle an installment that can't be linked to a real transaction — it predates the ledger, was
    paid by someone else, or was paid outside tracked accounts. Reduces the liability via a NON-CASH,
    EXCLUDED adjustment (deposit from a 'BNPL/financing settlement' revenue account → the liability,
    toward zero) so the debt shrinks but HIS tracked cash NEVER moves (he didn't pay from tracked
    money) and it never counts as spending or income. Marks the installment SETTLED (manual) with its
    reason — the integrity law extended, not diluted: manual settlements stay visibly manual forever.
    Balance-proven on the liability."""
    p = await req.json()
    aid = str(p["account_id"])
    n = int(p["installment"])
    reason = p.get("reason") if p.get("reason") in _SETTLE_REASONS else "other"
    note = (p.get("note") or "").strip()
    s = _schedules().get(aid)
    if not s:
        return {"ok": False, "error": "no schedule on this account"}
    inst = next((i for i in s["installments"] if int(i["n"]) == n), None)
    if not inst:
        return {"ok": False, "error": f"installment {n} not found"}
    if inst.get("paid") or inst.get("settled_manual"):
        return {"ok": False, "error": "that installment is already settled"}
    amt = round(float(inst["amount"]), 2)
    date = (p.get("date") or inst.get("date") or datetime.now().strftime("%Y-%m-%d"))[:10]
    liab_before = {a["id"]: a for a in accounts()}.get(aid, {}).get("balance")
    desc = f"Manual settlement — {_SETTLE_REASONS[reason]}" + (f": {note}" if note else "")
    plan_person = s.get("person")
    # non-cash liability reduction (deposit revenue→liability moves a −owed balance toward 0), EXCLUDED
    # from spending/income; no tracked account is touched — proven shape (delta = +amt toward zero).
    # Carries the plan's category + person so the record reads meaningfully even while excluded.
    ff("POST", "transactions", {"transactions": [{"type": "deposit", "date": date,
        "amount": f"{amt:.2f}", "description": desc, "source_name": "Financing settlement (manual)",
        "destination_id": aid, "category_name": s.get("category") or "",
        "tags": ["bnpl", "settle-manual", f"reason:{reason}", f"plan:{aid}", "excluded", "manual",
                 "trust:verified"] + ([plan_person] if plan_person else [])}]})
    inst["paid"] = True
    inst["settled_manual"] = True
    inst["settle_reason"] = reason
    if note:
        inst["settle_note"] = note
    _schedule_save(aid, s)
    retired = _maybe_retire(aid)
    liab_after = {a["id"]: a for a in accounts()}.get(aid, {}).get("balance")
    reduced = round(abs(liab_before or 0) - abs(liab_after or 0), 2)
    audit("schedule_settle_manual", id=aid, installment=n, reason=reason, amount=amt,
          liab_before=liab_before, liab_after=liab_after)
    return {"ok": True, "installment": n, "reason": reason, "amount": amt, "retired": retired,
            "liability_before": liab_before, "liability_after": liab_after,
            "reduced": reduced, "proof_ok": abs(reduced - amt) < 0.02}


@app.post("/api/bnpl/meta")
async def bnpl_meta(req: Request):
    """Set/change a plan's MEANING — its category + person — and re-tag every payment that touched it
    so Categories and By-person stay true. Declare it once; every installment (past and future) files
    itself. Re-tagging skips the excluded 'financed' funding leg (not spending) and only relabels the
    real installment charges / discharges."""
    p = await req.json()
    aid = str(p["account_id"])
    s = _schedules().get(aid)
    if not s:
        return {"ok": False, "error": "no schedule on this account"}
    cat = p.get("category") or ""
    if cat and p.get("sub"):
        cat = f"{cat}: {p['sub']}"
    person = p.get("person") if p.get("person") in PERSON_TAGS else (None if p.get("person") in (None, "") else s.get("person"))
    s["category"] = cat or None
    s["person"] = person
    _schedule_save(aid, s)
    # re-tag the plan's real payments: installment charges (source), discharges/settlements (dest=aid)
    retagged = 0
    for t in all_txns(include_excluded=True):
        tags = t.get("tags") or []
        if "bnpl" not in tags:
            continue
        # a plan's payments are found by the plan:{aid} tag OR by touching the liability account —
        # the checkout/installment SPENDING legs are card→provider (they never touch the liability),
        # so the tag is what catches them.
        if not (f"plan:{aid}" in tags or str(t.get("source_id")) == aid
                or str(t.get("destination_id")) == aid):
            continue
        if "financed" in tags:                       # the excluded funding leg — not spending, leave it
            continue
        jid = t.get("jid") or t.get("id")
        new_tags = [x for x in tags if x not in PERSON_TAGS] + ([person] if person else [])
        body = {"transaction_journal_id": jid, "tags": sorted(set(new_tags))}
        # only real spending legs carry the category (not the excluded non-cash debt-reduction legs)
        if not ("excluded" in tags):
            body["category_name"] = cat
        try:
            ff("PUT", f"transactions/{t['id']}", {"transactions": [body]})
            retagged += 1
        except Exception:
            pass
    audit("bnpl_meta", id=aid, category=cat, person=person, retagged=retagged)
    return {"ok": True, "category": cat or None, "person": person, "retagged": retagged}


@app.post("/api/lease/setup")
async def lease_setup(req: Request):
    """Lease-to-own (تأجير منتهي بالتمليك). Creates the lease liability at the TOTAL remaining
    commitment (N×monthly + balloon), the car in Other-assets at value, books the down payment
    (transfer cash→car, no P&L pollution), and a schedule with the BALLOON as a named final item.
    Balance-proven. Forget-proofing (balloon dashboard alert) rides the schedule."""
    p = await req.json()
    value = round(float(p["value"]), 2)
    down = round(float(p.get("down") or 0), 2)
    balloon = round(float(p.get("balloon") or 0), 2)
    term = int(p["term"])
    monthly = round(float(p["monthly"]), 2)
    from_id = str(p["from_account"])
    name = (p.get("name") or "Lease").strip()
    cur = p.get("currency", "SAR")
    ensure_currency(cur)
    first = (p.get("first_due") or datetime.now().strftime("%Y-%m-%d"))[:10]
    sign = (p.get("signing") or datetime.now().strftime("%Y-%m-%d"))[:10]   # openings dated at signing, NOT first-due (future dates don't hit current_balance — banked lesson)
    commitment = round(term * monthly + balloon, 2)
    cash_before = {a["id"]: a for a in accounts()}.get(from_id, {}).get("balance")
    # 1) lease liability at −commitment (origination via opening balance — clean, no liability transfer)
    lid = ff("POST", "accounts", {"name": name, "type": "liability", "liability_type": "debt",
             "liability_direction": "credit", "currency_code": cur,
             "opening_balance": f"{-commitment:.2f}", "opening_balance_date": sign,
             "notes": p.get("notes", "")})["data"]["id"]
    # 2) car in Other-assets at (value − down); the down flows in next
    cid = ff("POST", "accounts", {"name": name + " — car", "type": "asset",
             "account_role": "defaultAsset", "currency_code": cur,
             "opening_balance": f"{value - down:.2f}", "opening_balance_date": sign})["data"]["id"]
    kd = _yaml_load("account_kinds.yaml")
    kd.setdefault("kinds", {})[str(lid)] = "lease"
    kd["kinds"][str(cid)] = "other_asset"
    _yaml_save("account_kinds.yaml", kd)
    # 3) down payment: transfer cash → car (car reaches full value; no expense pollution)
    date = datetime.now().strftime("%Y-%m-%d")
    if down > 0:
        ff("POST", "transactions", {"transactions": [{"type": "transfer", "date": date,
            "amount": f"{down:.2f}", "description": "Lease down payment", "source_id": from_id,
            "destination_id": cid, "tags": ["lease", "manual", "trust:verified"]}]})
    for fee in (p.get("fees") or []):                      # admin/insurance fees → expenses
        try:
            fa = round(float(fee.get("amount")), 2)
            if fa > 0:
                ff("POST", "transactions", {"transactions": [{"type": "withdrawal", "date": date,
                    "amount": f"{fa:.2f}", "description": "Lease fee — " + (fee.get("name") or ""),
                    "source_id": from_id, "destination_name": "Lease fees",
                    "category_name": fee.get("category") or "Bank & fees",
                    "tags": ["lease", "manual", "trust:verified"]}]})
        except Exception:
            pass
    # 4) schedule: N monthly + balloon as named final item
    inst, d = [], _date.fromisoformat(first)
    for i in range(1, term + 1):
        inst.append({"n": i, "date": d.isoformat(), "amount": monthly,
                     "principal": monthly, "cost": 0.0, "paid": False})
        d = _add_freq(d, "monthly")
    balloon_date = d.isoformat()
    if balloon > 0:
        inst.append({"n": term + 1, "date": balloon_date, "amount": balloon,
                     "principal": balloon, "cost": 0.0, "paid": False, "balloon": True,
                     "label": "Balloon — final payment"})
    _schedule_save(lid, {"kind": "lease", "principal": commitment, "total_repayable": commitment,
                         "term": term + (1 if balloon > 0 else 0), "monthly": monthly, "start": first,
                         "total_cost": round(down + commitment - value, 2), "car_id": cid,
                         "value": value, "down": down, "balloon": balloon,
                         "balloon_date": balloon_date if balloon > 0 else None, "installments": inst})
    accs2 = {a["id"]: a for a in accounts()}
    audit("lease_setup", id=lid, value=value, commitment=commitment, balloon=balloon)
    return {"ok": True, "lease_id": lid, "car_id": cid, "commitment": commitment,
            "car_value": accs2.get(cid, {}).get("balance"),
            "liability": accs2.get(lid, {}).get("balance"),
            "cash_before": cash_before, "cash_after": accs2.get(from_id, {}).get("balance"),
            "financing_cost": round(down + commitment - value, 2), "balloon_date": balloon_date,
            "proof_ok": abs(abs(accs2.get(lid, {}).get("balance") or 0) - commitment) < 0.02}


@app.post("/api/asset/trade")
async def asset_trade(req: Request):
    """Buy/sell an asset position (metals, funds, ETFs) — a transfer between cash and the asset
    account (partial sale supported). Non-P&L (it's a shape change, not income/expense); realised
    gain/loss on sale is left to the position's cost-basis note. Balance-proven."""
    p = await req.json()
    aid, cash_id = str(p["account_id"]), str(p["cash_account"])
    amount = round(float(p["amount"]), 2)
    side = p.get("side", "buy")
    date = p.get("date") or datetime.now().strftime("%Y-%m-%d")
    accs = {a["id"]: a for a in accounts()}
    a_before = accs.get(aid, {}).get("balance")
    src, dst = (cash_id, aid) if side == "buy" else (aid, cash_id)
    ff("POST", "transactions", {"transactions": [{"type": "transfer", "date": date,
        "amount": f"{amount:.2f}", "description": f"{'Buy' if side=='buy' else 'Sell'} {accs.get(aid,{}).get('name','asset')}",
        "source_id": src, "destination_id": dst, "tags": ["invest", side, "manual", "trust:verified"]}]})
    realized = None
    pos = _positions().get(aid) or {}
    is_fund = _acct_kinds_map().get(aid) in ("fund", "etf")
    if p.get("units") not in (None, ""):                   # keep units/cost-basis note on the position
        fields = {"units": p["units"], "as_of": date}
        if is_fund:
            old_units = float(pos.get("units") or 0)
            new_units = float(p["units"])
            cb = float(pos.get("cost_basis") or 0)
            cap = float(pos.get("capital_in") or cb)
            avg = (cb / old_units) if old_units else 0.0
            if side == "buy":                              # cost basis + external capital both grow
                fields["cost_basis"] = round(cb + amount, 2)
                fields["capital_in"] = round(cap + amount, 2)
                fields["avg_price"] = round((cb + amount) / new_units, 6) if new_units else 0.0
            else:                                          # sell: realised gain = proceeds − cost of units sold
                sold = round(old_units - new_units, 6)
                cost_of_sold = round(avg * sold, 2)
                realized = round(amount - cost_of_sold, 2)
                fields["cost_basis"] = round(max(0.0, cb - cost_of_sold), 2)
                fields["capital_in"] = round(cap * (new_units / old_units), 2) if old_units else 0.0
        _positions_save(aid, fields)
    a_after = {a["id"]: a for a in accounts()}.get(aid, {}).get("balance")
    audit("asset_trade", id=aid, side=side, amount=amount, realized=realized)
    return {"ok": True, "side": side, "amount": amount, "realized_gain": realized,
            "asset_before": a_before, "asset_after": a_after,
            "proof_ok": abs(abs((a_after or 0) - (a_before or 0)) - amount) < 0.02}


@app.post("/api/lease/terms")
async def lease_terms(req: Request):
    """Store a lease's contract EXIT facts (never assumed): early-termination clause (free text —
    Saudi has no automatic mid-term walk-away right; it's whatever your contract says), whether
    returning-instead-of-paying-the-balloon is allowed at contract end, any handback fee, and an
    optional current car-value estimate for the end-of-term arbitrage."""
    p = await req.json()
    aid = str(p["account_id"])
    s = _schedules().get(aid)
    if not s or s.get("kind") != "lease":
        return {"ok": False, "error": "not a lease"}
    s["exit"] = {"clause": (p.get("clause") or "").strip(),
                 "return_allowed": bool(p.get("return_allowed")),
                 "handback_fee": round(float(p.get("handback_fee") or 0), 2),
                 "car_value": round(float(p.get("car_value") or 0), 2) if p.get("car_value") else None,
                 "notes": (p.get("notes") or "").strip()}
    _schedule_save(aid, s)
    audit("lease_terms", id=aid, return_allowed=s["exit"]["return_allowed"])
    return {"ok": True, "exit": s["exit"]}


@app.get("/api/balloons")
def api_balloons():
    """Lease balloon payments — the one everyone forgets. Returns each unpaid balloon with months
    until due (forget-proofing: amber ≤6mo, alert ≤3mo). Pure dates + arithmetic, no advice."""
    today = _date.today()
    accs = {a["id"]: a for a in accounts()}
    out = []
    for aid, s in _schedules().items():
        if s.get("kind") != "lease" or not s.get("balloon"):
            continue
        b = next((i for i in s["installments"] if i.get("balloon") and not i.get("paid")), None)
        if not b:
            continue
        bd = b["date"]
        m2d = (int(bd[:4]) - today.year) * 12 + (int(bd[5:7]) - today.month)
        out.append({"account": aid, "name": accs.get(aid, {}).get("name", "Lease"),
                    "amount": b["amount"], "date": bd, "months_to_due": m2d})
    out.sort(key=lambda x: x["months_to_due"])
    return {"balloons": out, "count": len(out)}


@app.post("/api/loan/settle")
async def loan_settle(req: Request):
    """Early settlement — Hisham enters the bank's ACTUAL settlement figure (banks rebate part of
    the remaining profit; we never compute it). Discharges the principal to zero + books the profit
    portion as financing cost. Reuses the proven paydown shape. Balance-proven."""
    p = await req.json()
    aid, from_id = str(p["account_id"]), str(p["from_account"])
    settle = round(float(p["settlement_amount"]), 2)
    liab_before = {a["id"]: a for a in accounts()}.get(aid, {}).get("balance")
    principal = round(abs(liab_before or 0), 2)          # the outstanding principal → to zero
    cost = round(settle - principal, 2)                  # the (rebated) profit actually paid
    date = p.get("date") or datetime.now().strftime("%Y-%m-%d")
    if principal > 0:
        ff("POST", "transactions", {"transactions": [{"type": "withdrawal", "date": date,
            "amount": f"{principal:.2f}", "description": "Loan early settlement — principal",
            "source_id": from_id, "destination_id": aid, "category_name": "",
            "tags": ["financing", "settlement", "manual", "trust:verified"]}]})
    if cost > 0:                                          # settled for MORE than principal → extra cost
        ff("POST", "transactions", {"transactions": [{"type": "withdrawal", "date": date,
            "amount": f"{cost:.2f}", "description": "Loan early settlement — cost", "source_id": from_id,
            "destination_name": "Financing cost", "category_name": "Bank & fees: financing cost",
            "tags": ["financing", "riba", "settlement", "manual", "trust:verified"]}]})
    elif cost < 0:                                        # settled for LESS (bank rebated profit) → gain back to cash
        ff("POST", "transactions", {"transactions": [{"type": "deposit", "date": date,
            "amount": f"{abs(cost):.2f}", "description": "Loan early settlement — profit rebate",
            "source_name": "Financing rebate", "destination_id": from_id,
            "category_name": "Bank & fees: financing cost",
            "tags": ["financing", "settlement", "rebate", "manual", "trust:verified"]}]})
    s = _schedules().get(aid)                             # mark schedule settled
    if s:
        for i in s["installments"]:
            i["paid"] = True
        _schedule_save(aid, s)
    liab_after = {a["id"]: a for a in accounts()}.get(aid, {}).get("balance")
    audit("loan_settle", id=aid, settlement=settle, principal=principal, cost=cost)
    return {"ok": True, "settlement": settle, "principal": principal, "cost": cost,
            "liability_before": liab_before, "liability_after": liab_after,
            "proof_ok": abs(liab_after or 0) < 0.02}


_FREQ_PER_YEAR = {"monthly": 12, "quarterly": 4, "half-year": 2, "annual": 1, "yearly": 1}


@app.get("/api/certificates")
def api_certificates():
    """Certificate (شهادة) payout machinery — expected payouts from rate × principal ÷ frequency
    ('as contracted', arithmetic not forecast); next payout; expected income THIS month; matured
    payouts matched by tag; maturity countdown for the renew-or-collect alert. Read-only."""
    kinds = _acct_kinds_map()
    pos = _positions()
    today = _date.today()
    ym = today.strftime("%Y-%m")
    matched = [t for t in all_txns()
               if "cert-payout" in (t.get("tags") or []) or t.get("category") == "Investment income: certificates"]
    out, month_income = [], 0.0
    for a in ff_all("accounts", type="asset"):
        at = a["attributes"]
        if kinds.get(a["id"]) != "certificate" or not at.get("active", True):
            continue
        p = pos.get(a["id"]) or {}
        # PRINCIPAL is frozen at the opening amount (see certificate_detail) — using the live
        # current_balance would inflate the profit every time a payout deposit lands in the account.
        principal = round(float(p["principal"]), 2) if p.get("principal") not in (None, "") \
            else round(float(at.get("current_balance") or 0), 2)
        rate = float(p.get("rate") or 0)
        freq = p.get("payout_freq") or "monthly"
        ppy = _FREQ_PER_YEAR.get(freq, 12)
        per = round(principal * (rate / 100) / ppy, 2)
        maturity = (p.get("maturity") or p.get("restricted_until") or "")[:10]
        start = (p.get("as_of") or today.isoformat())[:10]
        # payout dates: step (12/ppy) months from start until maturity (cap 120)
        step = max(1, 12 // ppy)
        dates, d = [], _date.fromisoformat(start)
        for _ in range(120):
            d = _date(d.year + (d.month - 1 + step) // 12, (d.month - 1 + step) % 12 + 1,
                      min(d.day, _calendar.monthrange(d.year + (d.month - 1 + step) // 12,
                          (d.month - 1 + step) % 12 + 1)[1]))
            if maturity and d.isoformat() > maturity:
                break
            dates.append(d.isoformat())
        this_month = [x for x in dates if x[:7] == ym]
        nxt = next((x for x in dates if x >= today.isoformat()), None)
        m2m = None
        if maturity:
            m2m = (int(maturity[:4]) - today.year) * 12 + (int(maturity[5:7]) - today.month)
        month_income += per * len(this_month)
        out.append({"id": a["id"], "name": at["name"], "currency": at.get("currency_code") or "SAR",
                    "principal": principal, "rate": rate, "freq": freq, "per_payout": per,
                    "next_payout": nxt, "this_month": len(this_month), "maturity": maturity,
                    "months_to_maturity": m2m, "payout_dates": dates})
    return {"certificates": out, "expected_income_month": round(month_income, 2),
            "count": len(out), "matched_payouts": len(matched)}


@app.get("/api/certificate/detail")
def certificate_detail(id: str):
    """Profit-first certificate view: the payout STREAM (the living part), each payout matched to a
    real deposit → RECEIVED ✓, received-to-date, next payout, rate history, and the locked principal
    as calm context. Read-only, 'as contracted' arithmetic."""
    aid = str(id)
    accs = {a["id"]: a for a in accounts()}
    a = accs.get(aid)
    if not a or _acct_kinds_map().get(aid) != "certificate":
        return {"ok": False}
    p = _positions().get(aid) or {}
    today = _date.today().isoformat()
    # PRINCIPAL is the locked opening amount, not the live balance (which grows as payouts arrive).
    principal = round(float(p["principal"]), 2) if p.get("principal") not in (None, "") \
        else round(abs(float(a["balance"])), 2)
    rate = float(p.get("rate") or 0)
    freq = p.get("payout_freq") or "monthly"
    ppy = _FREQ_PER_YEAR.get(freq, 12)
    per = round(principal * (rate / 100) / ppy, 2)
    maturity = (p.get("maturity") or p.get("restricted_until") or "")[:10]
    start = (p.get("as_of") or today)[:10]
    step = max(1, 12 // ppy)
    # real deposits into this certificate (payout arrivals) — for RECEIVED matching
    deposits = [t for t in all_txns() if t["type"] == "deposit"
                and (str(t.get("destination_id")) == aid or "cert-payout" in (t.get("tags") or []))]
    used = set()
    dates, d = [], _date.fromisoformat(start)
    for _ in range(120):
        d = _date(d.year + (d.month - 1 + step) // 12, (d.month - 1 + step) % 12 + 1,
                  min(d.day, _calendar.monthrange(d.year + (d.month - 1 + step) // 12,
                      (d.month - 1 + step) % 12 + 1)[1]))
        if maturity and d.isoformat() > maturity:
            break
        dates.append(d.isoformat())
    timeline, received_total = [], 0.0
    for iso in dates:
        match = None
        for t in deposits:
            if t["id"] in used:
                continue
            td = t.get("date") or ""
            if abs((_date.fromisoformat(td) - _date.fromisoformat(iso)).days) <= 10 \
                    and abs(t["amount"] - per) < max(1.0, per * 0.08):
                match = t
                used.add(t["id"])
                break
        recv = match is not None
        if recv:
            received_total += match["amount"]
        overdue = (not recv) and iso < today
        timeline.append({"date": iso, "amount": per, "received": recv,
                         "received_amount": match["amount"] if match else None,
                         "overdue": overdue})
    nxt = next((r for r in timeline if not r["received"] and r["date"] >= today), None)
    expected_to_date = round(per * sum(1 for iso in dates if iso <= today), 2)
    m2m = None
    if maturity:
        y, mo = int(maturity[:4]), int(maturity[5:7])
        m2m = (y - _date.today().year) * 12 + (mo - _date.today().month)
    return {"ok": True, "id": aid, "name": a["name"], "currency": a.get("currency", "SAR"),
            "principal": principal, "rate": rate, "rate_type": p.get("rate_type") or "fixed",
            "rate_history": p.get("rate_history") or [], "freq": freq, "per_payout": per,
            "timeline": timeline, "next_payout": nxt, "maturity": maturity, "months_to_maturity": m2m,
            "received_to_date": round(received_total, 2), "expected_to_date": expected_to_date,
            "total_expected": round(per * len(dates), 2), "payouts_total": len(dates),
            "received_count": sum(1 for r in timeline if r["received"])}


@app.post("/api/certificate/rate")
async def certificate_rate(req: Request):
    """Update a variable-rate certificate's current rate, keeping the history (past payouts untouched;
    only future expectations recompute)."""
    p = await req.json()
    aid = str(p["id"])
    pos = _positions().get(aid) or {}
    old = pos.get("rate")
    hist = pos.get("rate_history") or []
    if old is not None:
        hist.append({"rate": float(old), "until": (p.get("from") or datetime.now().strftime("%Y-%m-%d"))[:10]})
    _positions_save(aid, {"rate": round(float(p["rate"]), 3),
                          "rate_type": "variable", "rate_history": hist,
                          "rate_from": (p.get("from") or datetime.now().strftime("%Y-%m-%d"))[:10]})
    audit("certificate_rate", id=aid, old=old, new=p["rate"])
    return {"ok": True, "rate": float(p["rate"]), "history": hist}


def _fund_dividends(aid):
    """Dividend transactions attributed to this fund/ETF — cash (paid to a cash account, tagged
    fund:{aid}) or reinvested (deposited into the fund account itself). Split by the 'reinvest' tag."""
    cash, reinv = 0.0, 0.0
    for t in all_txns():
        tags = t.get("tags") or []
        if "fund-dividend" not in tags:
            continue
        if not (str(t.get("destination_id")) == aid or str(t.get("source_id")) == aid
                or f"fund:{aid}" in tags):
            continue
        if "reinvest" in tags:
            reinv += t["amount"]
        else:
            cash += t["amount"]
    return round(cash, 2), round(reinv, 2)


@app.get("/api/fund/detail")
def fund_detail(id: str):
    """Fund/ETF performance — honest price-vs-total return per global fund mechanics. Price return is
    how the unit price moved (understates a DISTRIBUTING fund, whose price drops when it pays out);
    total return adds the dividends you received — the pro's true-performance number. Read-only
    arithmetic over the monthly prices Hisham enters + the dividends he records."""
    aid = str(id)
    a = {x["id"]: x for x in accounts()}.get(aid)
    if not a or _acct_kinds_map().get(aid) not in ("fund", "etf"):
        return {"ok": False}
    p = _positions().get(aid) or {}
    cur = a.get("currency", "SAR")
    units = round(float(p.get("units") or 0), 6)
    cost_basis = round(float(p.get("cost_basis") or 0), 2)
    capital_in = round(float(p.get("capital_in") or cost_basis), 2)
    hist = sorted((p.get("price_history") or []), key=lambda r: r["date"])
    avg_price = round(cost_basis / units, 6) if units else 0.0
    latest = hist[-1]["price"] if hist else avg_price
    first = hist[0]["price"] if hist else avg_price
    current_value = round(units * latest, 2)
    cash_div, reinv_div = _fund_dividends(aid)
    div_total = round(cash_div + reinv_div, 2)
    # price return: pure per-unit price movement vs blended cost. total return: price move + the
    # dividends — cash ones taken out, reinvested ones already grown inside current_value.
    price_return = round((latest / avg_price - 1) * 100, 2) if avg_price else 0.0
    total_return = round((current_value + cash_div - capital_in) / capital_in * 100, 2) if capital_in else 0.0
    rows, prev = [], None
    for h in hist:
        val = round(units * h["price"], 2) if h.get("units") is None else round(h["units"] * h["price"], 2)
        rows.append({"date": h["date"], "price": h["price"], "units": h.get("units", units), "value": val,
                     "vs_purchase": round((h["price"] / first - 1) * 100, 2) if first else 0.0,
                     "vs_prev": round((h["price"] / prev - 1) * 100, 2) if prev else None})
        prev = h["price"]
    return {"ok": True, "id": aid, "name": a["name"], "currency": cur,
            "fund_type": p.get("fund_type") or "accumulating", "units": units,
            "cost_basis": cost_basis, "capital_in": capital_in, "avg_price": avg_price,
            "latest_price": latest, "current_value": current_value, "current_value_sar": to_sar(current_value, cur),
            "price_return": price_return, "total_return": total_return,
            "cash_dividends": cash_div, "reinvested_dividends": reinv_div, "dividends_total": div_total,
            "history": rows, "as_of": p.get("as_of"),
            "distributing": (p.get("fund_type") or "accumulating") == "distributing"}


@app.post("/api/fund/price")
async def fund_price(req: Request):
    """The monthly price ritual: Hisham enters the unit price he sees; the system stamps it into the
    price history (editable per date for corrections) and revalues the account to units × price via a
    non-cash 'excluded' adjustment (net worth follows; income/spend never touched)."""
    p = await req.json()
    aid = str(p["id"])
    pos = _positions().get(aid) or {}
    if _acct_kinds_map().get(aid) not in ("fund", "etf"):
        return {"ok": False, "error": "not a fund"}
    price = round(float(p["price"]), 6)
    date = (p.get("date") or datetime.now().strftime("%Y-%m-%d"))[:10]
    units = round(float(pos.get("units") or 0), 6)
    hist = [h for h in (pos.get("price_history") or []) if h["date"] != date]  # replace same-date
    hist.append({"date": date, "price": price, "units": units})
    hist.sort(key=lambda r: r["date"])
    _positions_save(aid, {"price_history": hist, "as_of": date})
    # revalue the account balance to units × price (non-cash, excluded — the proven revaluation shape)
    accs = {a["id"]: a for a in accounts()}
    a = accs.get(aid)
    new_val = round(units * price, 2)
    diff = round(new_val - float(a["balance"]), 2) if a else 0.0
    if a and abs(diff) >= 0.01:
        base = {"date": date, "description": "Fund revaluation (non-cash)", "notes": f"unit price {price}",
                "amount": f"{abs(diff):.2f}", "tags": ["revaluation", "excluded", "manual", "trust:verified"]}
        if diff > 0:
            ff("POST", "transactions", {"transactions": [dict(base, type="deposit",
               source_name="Revaluation", destination_id=aid, category_name="")]})
        else:
            ff("POST", "transactions", {"transactions": [dict(base, type="withdrawal",
               source_id=aid, destination_name="Revaluation", category_name="")]})
    audit("fund_price", id=aid, price=price, date=date, value=new_val)
    return {"ok": True, "price": price, "value": new_val, "units": units}


@app.post("/api/fund/dividend")
async def fund_dividend(req: Request):
    """Record a distributing fund's dividend — cash (paid into a chosen cash account → 'Investment
    income: funds/ETFs') or REINVESTED (buys more units at that day's price; units + cost basis grow;
    booked into the fund account as income). Accumulating funds never call this — it's inside the price."""
    p = await req.json()
    aid = str(p["id"])
    pos = _positions().get(aid) or {}
    if _acct_kinds_map().get(aid) not in ("fund", "etf"):
        return {"ok": False, "error": "not a fund"}
    amount = round(float(p["amount"]), 2)
    date = (p.get("date") or datetime.now().strftime("%Y-%m-%d"))[:10]
    mode = p.get("mode", "cash")
    tags = ["fund-dividend", f"fund:{aid}", "invest", "manual", "trust:verified"]
    if mode == "reinvest":
        price = round(float(p["price"]), 6)
        bought = round(amount / price, 6) if price else 0.0
        units = round(float(pos.get("units") or 0) + bought, 6)
        cb = round(float(pos.get("cost_basis") or 0) + amount, 2)   # reinvested → cost basis grows
        _positions_save(aid, {"units": units, "cost_basis": cb, "as_of": date})
        # income deposited into the fund account itself (value rises by exactly units_bought × price)
        ff("POST", "transactions", {"transactions": [{"type": "deposit", "date": date,
            "amount": f"{amount:.2f}", "description": f"Dividend reinvested ({bought} units @ {price})",
            "source_name": "Investment income", "destination_id": aid,
            "category_name": "Investment income: funds/ETFs", "tags": tags + ["reinvest"]}]})
        audit("fund_dividend", id=aid, mode="reinvest", amount=amount, units_bought=bought)
        return {"ok": True, "mode": "reinvest", "amount": amount, "units_bought": bought, "units": units}
    cash_id = str(p["cash_account"])
    ff("POST", "transactions", {"transactions": [{"type": "deposit", "date": date,
        "amount": f"{amount:.2f}", "description": p.get("desc") or "Fund dividend",
        "source_name": "Investment income", "destination_id": cash_id,
        "category_name": "Investment income: funds/ETFs", "tags": tags}]})
    audit("fund_dividend", id=aid, mode="cash", amount=amount)
    return {"ok": True, "mode": "cash", "amount": amount}


@app.get("/api/bnpl/candidates")
def bnpl_candidates(amount: float = 0):
    """Given a charge amount, which BNPL plans have a matching next installment? Powers the Desk
    propose-link ('discharge installment 2 of 4 on Zara plan?'). Never auto-assumes — proposes."""
    accs = {a["id"]: a for a in accounts()}
    out = []
    for aid, s in _schedules().items():
        if s.get("kind") != "bnpl":
            continue
        nxt = next((i for i in s["installments"] if not i.get("paid")), None)
        if nxt and abs(nxt["amount"] - amount) < max(1.0, amount * 0.02):
            out.append({"account": aid, "name": accs.get(aid, {}).get("name"), "item": s.get("item"),
                        "installment": nxt["n"], "of": s["term"], "amount": nxt["amount"]})
    return {"candidates": out}


@app.post("/api/bnpl/match")
async def bnpl_match(req: Request):
    """Link an arriving card charge to a BNPL plan as an installment discharge: re-points the
    EXISTING charge to reduce the provider liability (never a second expense) + marks the
    installment paid. Balance-proven on the liability."""
    p = await req.json()
    tid, aid = str(p["txn_id"]), str(p["bnpl_account_id"])
    s = _schedules().get(aid)
    inst = next((i for i in s["installments"] if not i.get("paid")), None) if s else None
    liab_before = {a["id"]: a for a in accounts()}.get(aid, {}).get("balance")
    cur = ff("GET", f"transactions/{tid}")["data"]["attributes"]["transactions"][0]
    jid = cur["transaction_journal_id"]
    # inherit the plan's meaning: its category + person flow onto every installment for analysis
    plan_cat = (s or {}).get("category") or ""
    plan_person = (s or {}).get("person")
    tags = sorted(set((cur.get("tags") or []) + ["bnpl", "discharge", "bnpl-installment",
                      f"plan:{aid}", "trust:verified"] + ([plan_person] if plan_person else [])))
    ff("PUT", f"transactions/{tid}", {"transactions": [{"transaction_journal_id": jid,
       "destination_id": aid, "category_name": plan_cat, "tags": tags}]})
    if s and inst:
        inst["paid"] = True
        _schedule_save(aid, s)
    liab_after = {a["id"]: a for a in accounts()}.get(aid, {}).get("balance")
    retired = _maybe_retire(aid)
    audit("bnpl_match", txn=tid, id=aid, installment=inst["n"] if inst else None, retired=retired)
    return {"ok": True, "installment": inst["n"] if inst else None,
            "liability_before": liab_before, "liability_after": liab_after,
            "discharged": round(abs(liab_before or 0) - abs(liab_after or 0), 2), "retired": retired,
            "proof_ok": bool(inst) and abs((abs(liab_before or 0) - abs(liab_after or 0)) - inst["amount"]) < 0.02}


@app.post("/api/bnpl/purchase")
async def bnpl_purchase(req: Request):
    """A BNPL purchase (Tabby/Tamara): books the FULL expense today, funded by the provider
    liability (you now owe the total), and generates the installment schedule. Truthful double
    entry — the item lands in its real category at full price, the debt is visible, and the card
    charges that follow are matched as discharges (never a second expense). Balance-proven."""
    p = await req.json()
    aid = str(p["account_id"])
    total = round(float(p["total"]), 2)
    n = int(p.get("installments") or 4)
    cat = p.get("category") or ""
    if cat and p.get("sub"):
        cat = f"{cat}: {p['sub']}"
    liab_before = {a["id"]: a for a in accounts()}.get(aid, {}).get("balance")
    date = p.get("date") or datetime.now().strftime("%Y-%m-%d")
    desc = (p.get("item") or "BNPL purchase") + (f" ({p['merchant']})" if p.get("merchant") else "")
    ff("POST", "transactions", {"transactions": [{"type": "withdrawal", "date": date,
        "amount": f"{total:.2f}", "description": desc, "source_id": aid,
        "destination_name": p.get("merchant") or "BNPL", "category_name": cat,
        "tags": ["bnpl", "manual", "trust:verified"]}]})
    per, inst, rem = round(total / n, 2), [], total
    d = _date.fromisoformat((p.get("first_due") or date)[:10])
    for i in range(1, n + 1):
        amt = per if i < n else round(rem, 2)
        rem = round(rem - amt, 2)
        inst.append({"n": i, "date": d.isoformat(), "amount": amt,
                     "principal": amt, "cost": 0.0, "paid": False})
        d = _add_freq(d, "monthly")
    _schedule_save(aid, {"kind": "bnpl", "principal": total, "total_repayable": total, "term": n,
                         "monthly": per, "start": (p.get("first_due") or date)[:10], "total_cost": 0.0,
                         "item": p.get("item"), "merchant": p.get("merchant"), "installments": inst})
    liab_after = {a["id"]: a for a in accounts()}.get(aid, {}).get("balance")
    audit("bnpl_purchase", id=aid, total=total, installments=n)
    return {"ok": True, "total": total, "installments": n,
            "liability_before": liab_before, "liability_after": liab_after,
            "incurred": round(abs(liab_after or 0) - abs(liab_before or 0), 2),
            "proof_ok": abs((abs(liab_after or 0) - abs(liab_before or 0)) - total) < 0.02}


@app.post("/api/bnpl/declare")
async def bnpl_declare(req: Request):
    """Declare the REMAINING installments on a BNPL account that already carries its debt (the retro
    case). INTEGRITY LAW: this NEVER marks an installment 'paid' from a typed number — 'paid' is only
    ever true when a real discharge transaction exists (see /api/bnpl/match & /api/financing/pay). So
    this builds a schedule of the REMAINING installments only, all unpaid, summing EXACTLY to the
    current balance. It moves no money. `installments_total`/`paid_before` are stored as DISPLAY
    context ('installment 3 of 6') — never as a paid-claim. If the numbers don't add up to the
    balance it refuses rather than fudge a monster last installment."""
    p = await req.json()
    aid = str(p["account_id"])
    accs = {a["id"]: a for a in accounts()}
    bal = abs(round(float(accs.get(aid, {}).get("balance") or 0), 2))
    if bal < 0.01:
        return {"ok": False, "error": "This account has no balance yet — use “New BNPL purchase” to "
                "book the full plan."}
    remaining_n = int(p.get("remaining") or 0)
    total_n = int(p.get("installments_total") or 0)
    paid_before = int(p.get("paid_before") or 0)
    if remaining_n <= 0 and total_n > 0:
        remaining_n = total_n - paid_before
    if remaining_n <= 0:
        return {"ok": False, "error": "How many installments are still LEFT to pay? (a number ≥ 1)"}
    per = None
    if p.get("amount"):
        try:
            per = round(float(p["amount"]), 2)
        except Exception:
            per = None
    if per is None:
        per = round(bal / remaining_n, 2)
    # integrity guard: the remaining installments must add up to the balance. If per×n is off by more
    # than a couple of rounding cents, the inputs are inconsistent — refuse, don't fudge.
    projected = round(per * remaining_n, 2)
    if abs(projected - bal) > max(0.05, remaining_n * 0.01):
        return {"ok": False, "error": f"Those numbers don’t add up: {remaining_n} × SAR {per:.2f} = "
                f"SAR {projected:.2f}, but the account owes SAR {bal:.2f}. Check the installment amount "
                f"or how many are left — the remaining installments must equal what you still owe."}
    next_due = (p.get("next_due") or datetime.now().strftime("%Y-%m-%d"))[:10]

    def _mshift(iso, k):
        y, mm, dd = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
        z = (mm - 1) + k
        y2, m2 = y + z // 12, z % 12 + 1
        dd = min(dd, _calendar.monthrange(y2, m2)[1])
        return _date(y2, m2, dd).isoformat()
    inst, rem = [], bal
    for j in range(remaining_n):
        amt = per if j < remaining_n - 1 else round(rem, 2)
        rem = round(rem - amt, 2)
        inst.append({"n": paid_before + j + 1, "date": _mshift(next_due, j), "amount": amt,
                     "principal": amt, "cost": 0.0, "paid": False})
    _schedule_save(aid, {"kind": "bnpl", "principal": bal, "total_repayable": bal, "term": remaining_n,
                         "monthly": per, "start": next_due, "total_cost": 0.0, "declared": True,
                         "installments_total": total_n or (paid_before + remaining_n),
                         "paid_before": paid_before, "item": p.get("item"),
                         "merchant": p.get("merchant"), "installments": inst})
    audit("bnpl_declare", id=aid, remaining=remaining_n, paid_before=paid_before, remaining_total=bal)
    return {"ok": True, "declared": True, "remaining_count": remaining_n, "paid_before": paid_before,
            "installments_total": total_n or (paid_before + remaining_n), "remaining_total": bal,
            "account_balance": bal, "no_money_moved": True, "matches_balance": True,
            "note": "Only real linked charges ever count as ‘paid’ — declaring records the remaining plan, not a paid count."}


def _mshift_iso(iso, k):
    """Month-shift an ISO date by k months (k may be negative)."""
    y, mm, dd = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
    z = (mm - 1) + k
    y2, m2 = y + z // 12, z % 12 + 1
    dd = min(dd, _calendar.monthrange(y2, m2)[1])
    return _date(y2, m2, dd).isoformat()


@app.post("/api/bnpl/reschedule")
async def bnpl_reschedule(req: Request):
    """Set/change a plan's installment count, generating the schedule FROM THE PLAN START DATE (not
    'next due') — so payment 1 sits on the start month and past unpaid ones read overdue. Preserves
    already-linked payments (the first N installments, where N = real discharges). total = what's owed
    now + what's already been discharged."""
    p = await req.json()
    aid = str(p["account_id"])
    n = int(p.get("installments") or 0)
    if n <= 0:
        return {"ok": False, "error": "Number of installments must be at least 1."}
    old = _schedules().get(aid) or {}
    start = (p.get("start") or old.get("start") or datetime.now().strftime("%Y-%m-%d"))[:10]
    discharges = _real_discharges(aid)
    paid_ct = len(discharges)
    if paid_ct > n:
        return {"ok": False, "error": f"You've already linked {paid_ct} payment(s) — installments can't be fewer than that."}
    owed = abs(_acct_bal(aid))
    total = round(owed + sum(d["amount"] for d in discharges), 2)
    per = round(total / n, 2)
    inst, rem = [], total
    for k in range(1, n + 1):
        amt = per if k < n else round(rem, 2)
        rem = round(rem - amt, 2)
        inst.append({"n": k, "date": _mshift_iso(start, k - 1), "amount": amt,
                     "principal": amt, "cost": 0.0, "paid": k <= paid_ct})
    _schedule_save(aid, {"kind": "bnpl", "principal": total, "total_repayable": total, "term": n,
                         "monthly": per, "start": start, "total_cost": 0.0, "declared": True,
                         "installments_total": n, "paid_before": 0,
                         "item": p.get("item") or old.get("item"),
                         "merchant": old.get("merchant"), "installments": inst})
    audit("bnpl_reschedule", id=aid, installments=n, start=start, paid_linked=paid_ct)
    return {"ok": True, "installments": n, "start": start, "per": per, "total": total,
            "linked_paid": paid_ct, "owed": owed}


@app.post("/api/bnpl/create")
async def bnpl_create(req: Request):
    """THE one-shot BNPL wizard (spec §1): create the plan account + book the full purchase + build
    the auto-divided schedule, in a single call. total ÷ installments = per (last absorbs rounding).
    Already-paid charges are linked afterwards (spec §2) — this never fakes a paid count."""
    p = await req.json()
    provider = (p.get("provider") or "BNPL").strip()
    item = (p.get("item") or provider).strip()
    total = round(float(p.get("total") or 0), 2)
    n = int(p.get("installments") or 0)
    if total <= 0 or n <= 0:
        return {"ok": False, "error": "Enter the total amount and the number of installments."}
    cur = p.get("currency", "SAR")
    ensure_currency(cur)
    date = (p.get("date") or datetime.now().strftime("%Y-%m-%d"))[:10]
    first_due = (p.get("first_due") or date)[:10]
    cat = p.get("category") or ""
    if cat and p.get("sub"):
        cat = f"{cat}: {p['sub']}"
    person = p.get("person") if p.get("person") in PERSON_TAGS else None
    person_tags = [person] if person else []
    name = item if provider.lower() in item.lower() else f"{item} ({provider})"
    # 1) create the liability account
    aid = ff("POST", "accounts", {"name": name, "type": "liability", "liability_type": "debt",
             "liability_direction": "credit", "currency_code": cur, "interest": "0",
             "interest_period": "monthly", "notes": f"BNPL · {provider}"})["data"]["id"]
    kd = _yaml_load("account_kinds.yaml")
    kd.setdefault("kinds", {})[str(aid)] = "bnpl"
    _yaml_save("account_kinds.yaml", kd)
    # 2) create the DEBT (you now owe the provider the full plan), but NOT as spending — in the
    # cash/installment model each installment is the spending event WHEN it's charged, never a lump
    # at purchase. So this funding leg is tagged 'excluded': it makes the liability −total without
    # inflating the month's spending.
    ff("POST", "transactions", {"transactions": [{"type": "withdrawal", "date": date,
        "amount": f"{total:.2f}", "description": item + (f" ({provider})" if provider else "") + " — financed",
        "source_id": aid, "destination_name": provider or "BNPL", "category_name": "",
        "tags": ["bnpl", "financed", "excluded", "manual", "trust:verified"]}]})
    # 3) auto-divided schedule
    per, inst, rem = round(total / n, 2), [], total
    d = _date.fromisoformat(first_due)
    for i in range(1, n + 1):
        amt = per if i < n else round(rem, 2)
        rem = round(rem - amt, 2)
        inst.append({"n": i, "date": d.isoformat(), "amount": amt, "principal": amt,
                     "cost": 0.0, "paid": False})
        d = _add_freq(d, "monthly")
    # 4) Tabby/Tamara charge installment 1 AT CHECKOUT — model that reality (spec §4). If the caller
    # says the first installment was paid at checkout and names the paying card, book it as the real
    # spending (card → category, counts) + a non-cash liability reduction, and mark it paid. So a 468
    # plan puts 117 on the card on day one, owes 351 — not 468 of spending.
    prov_checkout = provider.lower() in ("tabby", "tamara")
    first_paid = p.get("first_paid")
    if first_paid is None:
        first_paid = prov_checkout
    pay_from = p.get("pay_from")
    checkout_done = False
    if first_paid and pay_from:
        first = inst[0]
        ff("POST", "transactions", {"transactions": [{"type": "withdrawal", "date": date,
            "amount": f"{first['amount']:.2f}", "description": f"{item} — installment 1 of {n} (checkout)",
            "source_id": str(pay_from), "destination_name": provider or "BNPL", "category_name": cat,
            "tags": ["bnpl", "bnpl-installment", f"plan:{aid}", "manual", "trust:verified"] + person_tags}]})
        ff("POST", "transactions", {"transactions": [{"type": "deposit", "date": date,
            "amount": f"{first['amount']:.2f}", "description": f"{item} — installment 1 reduces debt",
            "source_name": "Financing settlement (checkout)", "destination_id": aid, "category_name": "",
            "tags": ["bnpl", "settle-checkout", "excluded", "manual", "trust:verified"]}]})
        first["paid"] = True
        checkout_done = True
    _schedule_save(str(aid), {"kind": "bnpl", "principal": total, "total_repayable": total, "term": n,
                              "monthly": per, "start": first_due, "total_cost": 0.0,
                              "installments_total": n, "paid_before": 0, "item": item,
                              "merchant": provider, "category": cat or None, "person": person,
                              "installments": inst})
    bal = abs(round(float({a["id"]: a for a in accounts()}.get(str(aid), {}).get("balance") or 0), 2))
    expected = round(total - (per if checkout_done else 0), 2)
    audit("bnpl_create", id=aid, provider=provider, total=total, installments=n, checkout_paid=checkout_done)
    return {"ok": True, "account_id": aid, "name": name, "per": per, "installments": n,
            "total": total, "balance": bal, "checkout_paid": checkout_done, "owed_now": expected,
            "proof_ok": abs(bal - expected) < 0.02}


@app.get("/api/bnpl/plans")
def bnpl_plans():
    """Live BNPL plans (for the Desk 'this is an installment of…' picker)."""
    accs = {a["id"]: a for a in accounts()}
    scheds = _schedules()
    out = []
    for aid, a in accs.items():
        if a.get("kind") == "bnpl" and a.get("active", True):
            s = scheds.get(str(aid))
            nxt = next((i for i in s["installments"] if not i.get("paid")), None) if s else None
            out.append({"id": aid, "name": a["name"], "balance": round(abs(a["balance"]), 2),
                        "next_amount": nxt["amount"] if nxt else None})
    return {"plans": out}


@app.get("/api/bnpl/linkcandidates")
def bnpl_linkcandidates(account_id: str):
    """Expenses in the ledger that look like a payment toward this plan (near the next installment
    amount) — for 'Link a payment'. Never auto-links; proposes."""
    s = _schedules().get(str(account_id))
    nxt = next((i for i in s["installments"] if not i.get("paid")), None) if s else None
    target = nxt["amount"] if nxt else None
    out = []
    for t in all_txns():
        if t["type"] != "withdrawal":
            continue
        if str(t.get("destination_id")) == str(account_id):    # already a discharge on this plan
            continue
        near = (target is None) or abs(t["amount"] - target) < max(2.0, target * 0.05)
        if not near:
            continue
        out.append({"jid": t.get("jid"), "date": t.get("date"), "desc": merchant_display(t.get("desc") or ""),
                    "amount": t["amount"], "account": t.get("account")})
        if len(out) >= 40:
            break
    out.sort(key=lambda x: x["date"] or "", reverse=True)
    return {"candidates": out, "target": target}


def _completed_plans():
    d = _yaml_load("completed_plans.yaml")
    return d.get("completed", {}) if isinstance(d, dict) else {}


def _maybe_retire(aid):
    """Auto-retirement (spec §6): when a plan's balance hits 0 and every installment is discharged,
    fold it into history — archive the Firefly account + stamp the completion date. Reversible."""
    aid = str(aid)
    s = _schedules().get(aid)
    if not s:
        return False
    if any(not i.get("paid") for i in s["installments"]):
        return False
    bal = abs(round(float({a["id"]: a for a in accounts()}.get(aid, {}).get("balance") or 0), 2))
    if bal > 0.02:
        return False
    try:
        cur = ff("GET", f"accounts/{aid}")["data"]["attributes"]
        ff("PUT", f"accounts/{aid}", {"active": False, "name": cur.get("name"),
                                      "type": cur.get("type")})
    except Exception:
        pass
    comp = _completed_plans()
    comp[aid] = {"date": datetime.now().strftime("%Y-%m-%d"), "item": s.get("item"),
                 "provider": s.get("merchant"), "total": s.get("total_repayable"), "kind": s.get("kind")}
    _yaml_save("completed_plans.yaml", {"completed": comp})
    audit("plan_retired", id=aid, item=s.get("item"))
    return True


@app.post("/api/account/edit")
async def account_edit(req: Request):
    p = await req.json()
    fields = {}
    if p.get("name"):
        fields["name"] = p["name"]
    if p.get("notes") is not None:
        fields["notes"] = p["notes"]
    if p.get("currency"):
        if account_stats(p["id"])["count"] > 0:
            return JSONResponse({"ok": False, "error": "currency can only change while the account has no transactions"}, 400)
        fields["currency_code"] = p["currency"]
    ff("PUT", f"accounts/{p['id']}", fields)
    acct_log("edited", id=p["id"], fields=fields)
    return {"ok": True}


@app.post("/api/account/close")
async def account_close(req: Request):
    p = await req.json()
    accts = {a["id"]: a for a in accounts()}
    a = accts.get(p["id"])
    bal = a["balance"] if a else 0
    if abs(bal) > 0.001 and not p.get("final_transfer_to"):
        return JSONResponse({"ok": False, "need_transfer": True, "balance": bal}, 200)
    if abs(bal) > 0.001 and p.get("final_transfer_to"):
        ff("POST", "transactions", {"transactions": [{
            "type": "transfer", "date": datetime.now().strftime("%Y-%m-%d"),
            "amount": f"{abs(bal):.2f}", "description": "Closing balance transfer",
            "source_id": p["id"] if bal > 0 else p["final_transfer_to"],
            "destination_id": p["final_transfer_to"] if bal > 0 else p["id"],
            "currency_code": "SAR", "tags": ["manual", "trust:verified"]}]})
    ff("PUT", f"accounts/{p['id']}", {"active": False})
    acct_log("closed", id=p["id"], name=a["name"] if a else None,
             final_transfer_to=p.get("final_transfer_to"))
    return {"ok": True}


@app.post("/api/account/reopen")
async def account_reopen(req: Request):
    p = await req.json()
    ff("PUT", f"accounts/{p['id']}", {"active": True})
    acct_log("reopened", id=p["id"])
    return {"ok": True}


@app.post("/api/account/reorder")
async def account_reorder(req: Request):
    """Persist a custom account order (item 5). Applied in the sidebar, pickers, and
    All-accounts. Firefly owns the accounts; order is presentation metadata, ours."""
    p = await req.json()
    ids = [str(x) for x in (p.get("ids") or [])]
    if not ids:
        return {"ok": False, "error": "ids required"}
    _yaml_save("account_order.yaml", {"order": ids})
    audit("account_reorder", n=len(ids))
    return {"ok": True}


@app.post("/api/account/hide")
async def account_hide(req: Request):
    """Hide (≠ close) an account — gone from active views but NOT closed/final-transferred;
    faded in the manager, tap to unhide. Balance is untouched (Money Pro behaviour)."""
    p = await req.json()
    aid = str(p.get("id") or "")
    if not aid:
        return {"ok": False, "error": "id required"}
    d = _yaml_load("hidden_accounts.yaml")
    hid = set(d.get("hidden", []) if isinstance(d, dict) else [])
    if p.get("hidden"):
        hid.add(aid)
    else:
        hid.discard(aid)
    _yaml_save("hidden_accounts.yaml", {"hidden": sorted(hid)})
    acct_log("hidden" if p.get("hidden") else "unhidden", id=aid)
    return {"ok": True, "hidden": p.get("hidden", False)}


@app.post("/api/account/delete")
async def account_delete(req: Request):
    p = await req.json()
    aid = p["id"]
    accts = {a["id"]: a for a in api_accounts(closed=1)["accounts"]}
    a = accts.get(aid, {})
    st = account_stats(aid)
    if st["count"] == 0:
        ff("DELETE", f"accounts/{aid}")
        acct_log("deleted", id=aid, name=a.get("name"), disposition="empty")
        return {"ok": True}
    mode = p.get("mode")
    if mode == "move":
        tgt = p["target_id"]
        moved = 0
        for g in account_txns(aid):
            s = g["attributes"]["transactions"][0]
            fields = {"transaction_journal_id": s["transaction_journal_id"]}
            before = {"source_id": s.get("source_id"), "destination_id": s.get("destination_id")}
            if s.get("source_id") == aid:
                fields["source_id"] = tgt
            if s.get("destination_id") == aid:
                fields["destination_id"] = tgt
            ff("PUT", f"transactions/{g['id']}", {"transactions": [fields]})
            acct_log("reassign", txn=g["id"], before=before,
                     after={k: fields[k] for k in fields if k != "transaction_journal_id"})
            moved += 1
        ff("DELETE", f"accounts/{aid}")
        acct_log("deleted", id=aid, name=a.get("name"), disposition="moved", target=tgt, moved=moved)
        return {"ok": True, "moved": moved}
    if mode == "purge":
        if st["count"] > PURGE_THRESHOLD:
            return JSONResponse({"ok": False, "error": f"{st['count']} transactions — too many to purge; close it or move history."}, 400)
        if p.get("confirm_name") != a.get("name"):
            return JSONResponse({"ok": False, "error": "type the account name to confirm"}, 400)
        acct_log("tombstone", id=aid, name=a.get("name"), count=st["count"], total=st["total"],
                 note="account AND history + receipts deleted")
        ff("DELETE", f"accounts/{aid}")
        return {"ok": True, "purged": st["count"]}
    return JSONResponse({"ok": False, "error": "choose move or purge"}, 400)


INDEX_HTML = open(os.path.join(os.path.dirname(__file__), "index.html"),
                  encoding="utf-8").read()
