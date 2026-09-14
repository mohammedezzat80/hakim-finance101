# BLOCKED & ROADMAP REGISTER

The single complete source of what's not built yet and *why* — reconciled from build logs
+ the Hisham/Claude session history (9 Sep 2026). Per doctrine: blockers are logged and
skipped forward, never improvised around. Any later session should read this to see the
whole system's future, not fragments.

**How to read the gate:** most Finance intelligence is blocked on **the surplus gate = Gate
G0** — Sarah's statements imported · review queue ≈ 0 · cash & safes counted · 3–4 normal
weeks lived → a *true surplus number exists*. Intelligence built before that would be
inventing from data that doesn't exist yet.

**⚑ UPDATE 14 Sep 2026 — THE OPENING is complete: the gate is now a dimmer, not a lock.** All nine
formerly-gated tabs are BUILT and LIVE (Today · Family · Subscriptions · Forecast · Debt coach · Insights ·
Budget · Zakat · Wealth), each computing what its data supports and naming — from the real ledger, never
hardcoded — exactly what a stronger claim needs and the date it's met (the `_maturity()` / `matBanner`
system). The SOON board is retired. **Two lived unlocks remain, not code:** (1) the **papers evening** —
enter certificates/HISSAR/gold/funds so Zakat gets a true base vs nisab and Wealth shows real allocation +
performance; (2) **30 Sep** — the 3rd complete month flips every "provisional/after 30 September" banner to
a confident pattern. The machine is finished; the fuel is the last mile.

The COMING IN WAVES rail section + the `/soon` pages are generated from this file. Tab-worthy
surfaces are marked **[TAB]**.

---

## Dashboard charter (14 Sep 2026) — boundary for the gated surfaces

The **Dashboard answers "where do I stand" — position + the month's shape (slow-moving, retrospective
truth).** It deliberately does NOT claim what belongs to future surfaces, so the gated builds below must
**own these, not duplicate them on the dashboard**:
- **pace / urgency / "% of typical spent so far"** → **Insights** (and the live **Today** view). The old
  dashboard pace bar was removed.
- **safe-to-spend / "what's left"** → **Budget** (§A2).
- **upcoming / due-soon / committed-this-month** → **Today** (§A6) / **Recurring**. The dashboard's
  Upcoming-payments panel and Committed strip were removed; committed still lives on Categories + Recurring.
- **forecasts / balloon-due / certificate-income / maturity reminders** → **Forecast** (§A4) / **Today**.
  These alerts were removed from the dashboard; until Forecast/Today land they surface only on their
  **detail pages** (lease/certificate on Accounts). ⚠️ If a proactive balloon/maturity warning is wanted
  before Forecast ships, that's a deliberate dashboard exception to add back — not an oversight.
- The dashboard keeps: net-worth hero + chart, position tiles, **the month's shape** (in/out/net + last +
  3-mo typical, completed-period comparison only), **household split** (Hisham/Sarah/joint/unassigned),
  cards + utilization, top categories/merchants/person/day-of-week, recent activity — all position or
  retrospective. Operational-health alerts (backup/agent) stay; money chores collapse to one quiet line.

**⏳ TEMPORARY exception (added 14 Sep 2026) — the "Next 7 days" line.** Because Today/Forecast don't
exist yet, the forget-proofing (card due dates · installments · balloon · maturity · card expiry) would go
dark on the daily page for the weeks before Today opens. So the dashboard keeps **TWO compact lines:**
- **"Next 7 days"** — due dates only, ≤7 days (`next7` in `_dash_impl`; `next7line()` in dashboard.html).
- **"Ahead"** — long-lead heads-up BEYOND 7 days: **balloon ≤6/3mo · certificate maturity ≤1mo · card
  expiry ≤60/30d** (`heads` in `_dash_impl`; `headsline()`). A KNOWN dated obligation named ahead of time —
  no prediction, so it's forget-proofing, not forecasting.

No pace, no forecast, no safe-to-spend on either. **REMOVAL CONDITION: delete `next7` + `heads` (backend)
and `next7line()` + `headsline()` (frontend) the day the Today/Forecast surface ships** — Today owns this
permanently. A deliberate, dated exception, not charter drift.

**✅ RESOLVED 14 Sep 2026 — Today shipped.** The forward view was removed from the dashboard (both backend
keys + both frontend lines) and now lives on the **Today** tab (`_forward_due()` → `/api/today`). The
exception is closed; the dashboard is back to pure "where do I stand".

---

## Registered ideas — logged so nothing depends on memory (14 Sep 2026)

Not yet built; captured verbatim from Hisham so a future session picks them up:

1. **Wealth-tab position performance analytics** (extends §14 Wealth [TAB]) — time-weighted return,
   annualized return, allocation drift, contribution-to-growth — computed **entirely from Hisham's own
   entered prices + purchase records**. NO market data, NO benchmarks: the **tracking-not-monitoring**
   boundary stays intact. Benchmark comparison remains **HISSAR / BAHHATH** territory (other domains), never
   here.
2. **Long-horizon net-worth projection** — "at this savings rate, position in 5 years." Beyond **Forecast**'s
   90-day scope (§A4), so it's **currently unclaimed by any tab** — needs a home (likely Wealth or a new
   long-range surface). Still gated on lived surplus history like all projection.
3. **Merchant dossiers** — merchant as a **first-class entity** with its own history/trends, mirroring the
   category dossiers (Cat-6). Feeds the future **receipts wave**. (Merchant manage/normalization exists
   today — Z6; this is the analytics/entity layer on top.)

---

## A · Blocked on lived data (the surplus gate)
1. **Budget engine intelligence** [TAB: Budget] — AI-proposed targets from real spending +
   in-line coaching. Manual targets (periodic, income+expense, parent=Σchildren) are **LIVE**
   (Categories → Manage); only the *intelligence* is blocked. *Unlock:* a few normal months of
   budgets-in-use after G0. Blueprint §2.
2. **Safe-to-spend** [TAB: Budget] — the one number: "today you can spend X without touching
   anything promised." *Unlock:* surplus gate. Blueprint §3.
3. **Debt coach** [TAB] — avalanche/snowball payoff strategies + payoff dates + true cost of
   debt (incl. Tawarruq markup). Card balances already tracked. *Unlock:* a real surplus figure
   (the "extra to throw at debt") — post-G0. Blueprint §5.
4. **Forecast / scenarios** [TAB] — projected balances + what-ifs, incl. the **Projected
   Balance** report type deliberately omitted from Reports. *Unlock:* the plan→approve→actual
   system (Today) live + recurring history. Blueprint §4.
5. **Budget rollover + per-period taper** — unspent rolls forward (optional negative rollover);
   different limit per month ("2,000→1,700→1,500"). *Unlock:* lived surplus history to roll.
   Blueprint §13. (Ships inside the Budget tab.)
6. **Plan→approve→actual + Today view** [TAB: Today] — Money Pro's crown jewel: planned items
   live on the calendar WITHOUT touching balances; a Today view shows bills due + **predicted
   repeats** ("you usually buy groceries Thursdays — add it?") as one-tap entries; approving =
   the PAID moment; feeds the forecast. *Unlock:* G0 + enough recurring history for real
   predictions. Blueprint §13/§1.
7. **Subscription hunter intelligence** [TAB: Subscriptions] — auto-detect recurring charges,
   pre-renewal warnings (3 days), flag paid-but-unused subs. *Unlock:* a few months of history
   so recurrence is detectable (one charge isn't a subscription). Blueprint §6.
8. **Whisper layer beyond the morning brief** — Friday CFO wrap, anomaly whispers (double
   charge, bill 40% above norm, odd-hour card use), spending-spree notices. *Unlock:* baselines
   (a "norm") + the delivery rail (see C-human). Blueprint §7. (Surfaces partly in Insights.)
9. **AI budget proposals** — subset of #1, called out separately in roadmap appends. Same unlock.
10. **Report scheduling** — auto-run + push a saved report on a schedule. *Unlock:* the same
    delivery rail as the Morning Brief (NTFY unset — see C-human). Saved reports are LIVE.

## B · Deferred on write-discipline (one money-write micro-wave — ship together)
Both mint linked money-movement transactions; the Desk doctrine ships money-writing flows only
with exhaustive before/after balance-reconcile + undo tests — never rushed at a wave's tail.
11. **G — Liability-payment entry (interest/principal split)** — books a card/loan payment as
    principal (transfer) + interest (expense → `Bank & fees: Card fees & tawarruq`). *Present
    value low:* the importer already brings each Tawarruq markup in as its own categorisable
    line, so cost-of-debt is already visible. *To clear:* a 4th Quick-add type "Liability
    payment", linked pair, undo + balance-reconcile test.
12. **L — Asset buy/sell entry types (incl. partial sale)** feeding Other Assets. *Present value
    low:* Other-asset accounts (shipped) are already fundable via normal transfers (buy = cash→
    asset transfer; sell = reverse). Dedicated buy/sell is labelling sugar. *To clear:* buy/sell
    buttons on Other-asset accounts + a market-value-adjustment option, with G.

## C · Blocked on data completeness / human & device tasks
13. **Zakat engine** [TAB] — continuous nisab tracking across zakatable wealth + one-tap zakat
    report when due (amount, basis, audit trail, links to Zakat & charity). Local user-updated
    gold-price table, no external calls. *Unlock:* a complete asset picture (cash counted,
    gold/savings, asset accounts populated) + a full Hijri year so the clock actually runs.
    Blueprint §12.
14. **Wealth surface** [TAB] — whole-wealth net worth aggregated **at answer time** across
    personal + trading (HISSAR) + factory; SIMAH credit-report tracker (obligations vs ledger,
    score trend). *Unlock:* the Wealth/WAZIR agent era + a **SIMAH access decision** (external
    dependency — Hisham's call) + periodic manual SIMAH imports. Furthest out (Wave 4).
    Blueprint §9. ⚠️ *flagged: SIMAH integration depends on an access decision not yet made.*
15. **Family surface** [TAB] — per-person views (yours/mine/ours, Sarah's household view per
    family rules, kids) + **HAKIM Wrapped** (private year-in-money story). *Unlock:* Sarah
    imported + months of complete person-tagged family data (a full year for Wrapped). Wave 4.
    Blueprint §11.
— **Morning Brief on-phone delivery** — built (`/api/brief`, `scripts/morning_brief.py`, launchd
  07:00, now runs via the FDA venv python). *Blocked on:* `NTFY_URL` unset in
  `com.hakim.morningbrief.plist`. *To clear (you):* subscribe the ntfy app to your HAKIM topic →
  set `NTFY_URL` → `make brief-install && make brief`; screenshot the whisper. (Gates #8 + #10.)
— **Tailscale phone access** — responsive/390px pass done in code. *Blocked on:* Tailscale up +
  authed on this Mac and your iPhone; the tailnet MagicDNS URL can't be generated from here.
  *To clear (you):* bring Tailscale up on both, open the Desk over the tailnet URL; I'll record it.

## D · Blocked on maturity/scale of data
16. **Insights / behavioral surface** [TAB] — spending patterns, anomaly detection, **Sankey**
    money-flow diagrams (income → categories → savings/debt). *Unlock:* enough lived history to
    have a baseline (an anomaly is only meaningful against a norm). Wave 3–4. Blueprint §8/§1.
17. **Receipt-items layer** — line-item intelligence parsed from receipt photos. Photo
    attachment is **LIVE** (view/add on the Desk card); the parsing/intelligence is blocked.
    (Feature inside transaction detail — not a tab.)
18. **Tell-Finance conversational entry** — natural-language transaction entry via the agent,
    behind the existing Ask-Finance box. (Feature inside the Desk — not a tab.)

## E · Deferred by choice (not blocked — awaiting Hisham's go)
19. **Cross-month split ⑂ on the Desk** — mega-brief item 2; multi-transaction + link. (Desk
    feature — not a tab.)
20. **Custom category icons** — ✅ **SHIPPED** in the Money Pro Comfort Wave (curated line-icon
    library + custom photo upload). No longer blocked; retained here only to close the loop.
21. **Light theme** — shown in /settings as not-yet-on (honest), so nothing half-works.
22. **Full Arabic localization** (RTL + every string) — real project; shown in /settings, off.
23. **Customizable dashboard** — user-selectable/orderable widgets (Monarch pattern); after
    stabilization.
24. **Mac app wrap (Tauri) + native macOS notifications** — unlocks when Hisham declares the
    system satisfying.
25. **PWA packaging for iPhone/iPad via Tailscale** — at ~3–4 months maturity.
26. **hakim-ui shared theme package** — tokens + components importable by Factory/MENTCO/
    Regulatory surfaces; before the Factory build begins.

## F · Ecosystem-level (HAKIM roadmap — NOT Finance builds)
Kept here for completeness; these are other domains/agents, not Finance tabs.
27. **Factory ERPNext instance + HAKIM face** — next domain after Finance stabilizes; the
    factory's real name is required first (never the "NWF"/"Al Nabeel" placeholders).
28. **MENTCO ERPNext fix + Daftra migration** — mirror test incl. ZATCA; cutover before the
    subscription expiry (~end Jan/Feb).
29. **Regulatory domain surface.**
30. **Third-party guest access** (regulatory consultant view) — Shield agent design item.
31. **Break-glass recovery** (lost-all-devices) — Shield agent design item.
32. **Scout agent `SCOUT_FINANCE_WATCH.md`** — quarterly market scan (baseline: blueprint v1.2,
    last scanned 8 Sep 2026).
33. **Productization decision** — `IDEAS.md`, revisit Sep 2027.

---
### Reconciliation notes (9 Sep 2026)
- Merged the master register (A–F) with the prior build-logged blockers; nothing dropped.
- **#20 custom icons** was listed as pending in the register but is **shipped** — marked ✅.
- **#14 Wealth/SIMAH** flagged: SIMAH integration depends on an access decision Hisham hasn't
  made — surfaced rather than assumed.
- Morning Brief + Tailscale were already logged (device/human tasks); folded under C and linked
  to the whisper (#8) and report-scheduling (#10) gates they also block.
- Tab-worthy [TAB] surfaces → the rail's COMING IN WAVES map + `/soon` pages.

---
## G · Staged from the Final Sweep / Last Dig / Inward Dig (10 Sep 2026)
**Shipped & verified this era:** heatmap regression fix (→ Calendar spending-heat shading),
**Hawl tracking groundwork** (nightly zakatable snapshot — time-critical, now recording + agent
installed), **Calendar bills layer** (due-dots + day-panel bills w/ paid✓/amount-not-set +
"N due · rest of month" footer — activates fully on amounts), gold asset type, Sadaqah + 5 more
built-in report presets, dashboard pace indicator, Goals-ownership + Firefly-native audits.

**Reconciliation (10 Sep): honest correction.** The **Riba & fees lens did NOT ship** — only the
Sadaqah *preset* did; there is no per-card interest breakdown, no 6-mo cost-of-debt trend, no
Categories-drill framing. Staged at full spec below (WAVE H). **Trip tagging** (Last Dig 6c) was
dropped entirely — staged (WAVE Z).

### Sequenced execution plan — one wave per "go"
Rationale for the order: **Rules + bulk ops must land before Sarah's statements arrive**, so her
3 files meet a rules engine + batch tools (an afternoon of one-taps) instead of ~200 one-at-a-
time reviews (an evening). That is the single highest-leverage ordering decision left.

**WAVE R — Rules & bulk — ✅ SHIPPED (10 Sep 2026, pre-Sarah).**
- R1 ✅ **Firefly-native Rules manager** ("crown find") — `/rules` page + full backend
  (list/impact/migrate/create/toggle/delete/test/apply). **52 of 54 importer rules migrated**
  into Firefly (2 skipped: target category "To review" = no action). Queue-impact: 19 queue, all
  transfers/SADAD → 0 rule-addressable today; payoff on Sarah's merchant statements.
- R2 ✅ **Desk bulk operations** — batch Verify/Categorise existed; added batch **Person** + **Class**.
- R3 ✅ **"Make this a rule" → native** — the Desk always-apply path now also creates a Firefly
  rule (runs on existing + future txns). "Apply to N similar" already existed via merchant-key grouping.
- Z5 ✅ (pulled forward) **credit-utilization bar** — `data/card_limits.yaml` + self-service edit;
  amber/rose/red thresholds; **two cards over limit surfaced honestly** (•5158 106%, •5019 103%).

**WAVE M — FOUNDATION ✅ SHIPPED (10 Sep 2026); per-instrument write-flows = part 2.**
Shipped the layer everything attaches to: **new account subtypes** (certificate/fund/etf/gold/
silver/hissar/equity assets · loan/bnpl/lease liabilities) creatable self-service from Accounts,
grouped (Investments · Gold & metals · HISSAR · Company equity · Financing); **positions.yaml**
(as-of · restricted-until · rate/maturity/units/nav); **`/api/positions`** + **Holdings mini-view**
(cost/value, restricted-vs-available, staleness); **restricted-vs-available net-worth sub-line**
("of which restricted 🔒"); **monthly quick-update** (`/api/position/update` — value change posts a
NON-CASH revaluation tagged `excluded`, moves balance without polluting P&L) + **dashboard staleness
reminder** (>60d); **hawl zakatable base extended** (certificates/funds/etf/silver). Verified: cert
(restricted) + fund → holdings 150k = 100k restricted + 50k available; demo cleaned.
**Part 2 — progress (10 Sep):** ✅ **FX-correct mixed-currency totals** (Holdings/net-worth via
`to_sar()`; EGP/USD positions convert, e.g. EGP 10,000 × 0.075 = SAR 750). ✅ **Financing schedule
engine** (`data/schedules.yaml` + `/api/loan/setup` straight-line principal/cost split + `/api/
schedule` + committed-money **debt bucket wakes** from schedules). Proven arithmetic: 100k→112k/36
= cost 12,000, installment principal 2,777.78 + cost 333.33.
✅ **M2.0 paydown-WRITE — SOLVED (11 Sep).** The wall was a self-inflicted test bug: future-dated
payments don't affect `current_balance` (as-of today). Correct Firefly shape = **withdrawal ·
source=asset · destination=liability · current date** (transfers 422). `/api/financing/pay` fixed;
end-to-end proof through the app: liability −100k→−97,222.22, cash −2,777.78, cost 333.33 → "Bank &
fees: financing cost", `proof_ok:true`. Surfaced on the loan account detail (setup · amortization ·
Record payment with balance-proof). This unblocks every dependent payment flow below.

**Part 2 remaining (each a focused pass, retro-declare-ready as honest empty states):** G+L principal/interest
split · cross-month ⑂ · BNPL purchase-flow + installment matching (no double-count) · Tawarruq loan
schedule + payment matching · lease wizard (dual amount/% down + balloon + forget-proofing 6/3mo +
both endings) · depreciation · certificate payout schedules + matched payouts + maturity alerts ·
fund/ETF buy-sell + distributions · currency-correct holdings totals (positions currently sum raw
balances; FX conversion for mixed-currency totals). Doctrine held: HISSAR blind (balance+transfers
only); equity = book value (M12).

**WAVE M — Money-writes = the complete debt machinery (focused session, balance-proof + undo).**
Every way money is owed in Hisham's life, one double-entry-honest session. Each item ships with
reconciliation proofs, undo, typed confirms. **Retro-declare flows** for anything live today
(Hisham supplies the open plans/loans/leases to true-up the ledger).
- M1 **G+L liability-payment split** (task #14) — split a payment into principal / financing-cost legs.
- M2 **L asset buy/sell entry types** (task #19).
- M3 **Cross-month split ⑂** — multi-transaction split via native `transaction_links`.
  *Deferred three times on purpose — write-discipline immune system. Do NOT rush.*
- M4 **BNPL (Tabby/Tamara) as first-class debt.** Provider = liability account (self-service
  create). Purchase flow: item · merchant · total · provider · #installments (default 4) · first-due
  → books **full expense today (correct category, full amount, purchase date) + liability to
  provider**, generates the installment schedule as linked expected-payments. **Installment
  matching:** a card charge (SMS/statement, e.g. TABBY 500) proposes linking as discharge of the
  right installment → liability shrinks; the charge is a transfer/discharge, **never a second
  expense** (no double-count). Surfaces: BNPL card in /accounts (remaining · next due · schedule);
  "committed future payments" on the debt side of net worth; Calendar installment due-dots.
  Retro-declare open plans. *(Fixes the two lies of SMS-only capture: jacket-as-4-purchases +
  invisible debt.)* Optional down-payment field (dual amount/% input) for plans that take one.
- M5 **Personal loan (Tawarruq/financing).** Fields: principal received · total repayable (incl.
  fixed profit) · term · monthly · start. Posts cash-in + liability at **total repayable**;
  schedule splits each payment **principal + financing cost** (cost → "Bank & fees: financing
  cost", feeds the Riba lens H5). Early-settlement: Hisham enters the actual settlement figure
  (banks rebate part of remaining profit) — system posts discharge + adjustment, never computes it.
- M6 **Lease-to-own (تأجير منتهي بالتمليك) with balloon.** Wizard in contract order: car value ·
  **down payment (amount OR %, dual input, editable either way)** · **balloon/final (amount OR %,
  dual input)** · term + monthly (enter the real contract number, never compute; show implied
  "total financing cost over term" = (N×monthly + balloon + down) − car value) · first-due +
  optional admin/insurance fees (booked as expenses, not liability). Posting at signing: car →
  Other Assets at value · down → transfer out · **liability = (N×monthly) + balloon** · schedule
  with the **balloon as its own final scheduled item, labelled "Balloon — final payment"**.
  **Balloon forget-proofing (pure dates+arithmetic, no advice):** lease card always shows
  monthly · balloon amount+due-date · total remaining; Calendar gives the balloon a distinct
  due-dot; committed-payments always includes it; from 6mo before → quiet amber line on the card,
  from 3mo → joins the alerts strip. End-of-term: pay balloon (discharge + ownership note, car
  stays owned) OR return/trade-in (enter dealer settlement, close asset+liability, Δ booked as
  gain/loss). Retro-declare a live lease.
- M7 **Simple depreciation (estimate, flagged; OFF by default, per Other-Asset).** A % / year rule
  Hisham sets (editable), applied monthly as a non-cash value adjustment (never touches cash);
  asset detail shows original vs current estimated value, tagged "estimate" — never market truth.
- M8 **Loan/lease payment matching** — monthly payments arriving via SMS/statement propose linking
  to the schedule (same matcher as M4 BNPL). Surfaces: loan/lease card (remaining · next due ·
  cost-to-date · payoff progress bar); committed-payments line; Calendar due-dots; Riba lens gains
  "financing cost" rows per loan.
- M9 **Metals** — gold + silver holdings in **grams** (not just a SAR account); value = grams ×
  price/gram (manual, as-of stamped, flagged estimate). Zakatable. (Gold asset-type already ships;
  this adds grams + silver + the price-update handshake.)
- M10 **Investment trilogy** (three asset subtypes; tracking-not-monitoring — no live prices, no
  analytics, position truth with honest as-of dates; monthly price/NAV-update reminder + one-screen
  quick-update list; staleness-dim >60d; all in the hawl zakatable base with per-position override +
  a purification flag recorded for the future engine, no rulings):
    - M10a **Certificates (شهادات — Egyptian bank certificates, e.g. NBE 17–22%):** name/bank/
      currency · principal · rate ("as contracted", display-only) · **payout freq (monthly/
      quarterly/annual)** · start + **maturity** dates · early-redemption penalty note (free text).
      **Expected-payout schedule** = principal × rate ÷ freq → Calendar payout-dots + a
      committed-**income** line ("expected certificate income this month: EGP X — as contracted, not
      a forecast"). Actual payouts (statement/manual) **matched to schedule** → income category
      "Investment income: certificates"; unmatched/late flagged, never assumed. **Restricted:**
      principal counts in net worth but carries "locked until {maturity}"; a net-worth sub-line "of
      which restricted: X" so available-vs-total wealth are both honest; maturity → Calendar dot +
      alerts strip 1mo before (renew-or-collect).
    - M10b **Funds (صناديق):** name/manager/currency · **units + NAV** (manual, as-of) · buy/sell
      adjust units + cost basis · per-fund **distribution rule** (monthly/quarterly/annual/accumulating)
      · subscription/redemption terms note (notice days, fees, min hold). Distributions matched →
      "Investment income: funds". Value = units × NAV → SAR.
    - M10c **ETFs:** name/ticker/exchange/currency · units + last price (manual, as-of) · buy/sell w/
      cost basis · dividends matched → "Investment income: ETFs".
    - **Holdings mini-view:** the trilogy grouped, cost vs current value, simple gain/loss, currency
      exposure, restricted-vs-available split.
- M11 **HISSAR — two blind capital positions** (Finance sees only capital-in / capital-out /
  current balance — never trades, holdings or P&L):
    - **HISSAR — Farm:** permanent growth pot; withdrawals not expected; **flagged excluded from any
      future "available funds" concept** (intelligence-era boundary — logged here).
    - **HISSAR — Position:** position-trading capital; Finance is deliberately blind — tracks only
      current balance (manual, monthly reminder, as-of) + deposits/withdrawals as bank↔position
      transfers; any balance change beyond transfers is implicitly trading result, shown as a plain
      balance delta, never labelled or analysed.
    - Both zakatable in the hawl base. **Boundary doctrine (logged):** no HISSAR API, no trade data,
      ever — WAZIR-era cross-domain questions are the only future exception.
- M12 **Company equity injection** — personal→company money = an **equity asset at book value**
  (tracking-not-monitoring). **DECIDED (Hisham, 10 Sep): equity asset at book value** — a
  personal→company injection books an Other-asset "Equity in {company}" at the amount injected
  (not a plain expense); company→personal money crossing back reduces it. No market revaluation.
- **Retro-declare data needed from Hisham when M runs:** live BNPL plans (bought/total/installments-
  left) · live loan (principal/total/term/monthly) · live lease (value/down/balloon/term/monthly) ·
  each certificate (bank/principal/rate/freq/start/maturity) · each fund (units/NAV/distribution/
  redemption) · each ETF (ticker/units/price) · HISSAR Farm balance + Position balance · gold/silver
  grams. *(Hisham gathers the papers; retro-declare flows true-up the ledger.)*

### Go-order (Hisham's sequence — one wave per "go", report each)
① close add-category incident ✅ (10 Sep — stale-tab reload signal) · ② Guide wave ✅ (10 Sep) ·
③ **WAVE B** (budget arithmetic + irregular-bill-dates thin-schedule) — NEXT · ④ **WAVE M** (full
asset & debt anatomy incl. the trilogy + HISSAR + equity + metals) · ⑤ **WAVE H** (owed-to-me ·
cash-count · seasonal goals · goals math · Riba lens) · ⑥ **WAVE N+Z** (webhooks · links UI · native
paid-status · strictness · compare · merchant confirm · trip tag). Guide recipes updated same-commit.

**WAVE B — Budget arithmetic — B0/B1/B2/B5 ✅ SHIPPED (10 Sep); B3 partial; B4/B6/B7 staged.**
Shipped: **B1 committed-money** (`/api/committed` — bills due this month, real-month not smeared,
+ envelope contributions + debt-bucket=0 until M; dashboard line + Categories summary stat, honest
"set amounts to light up"); **B2 set-from-history** (`/api/category/averages` last/3-mo/6-mo, gated
on real months of ledger; ⟲ hist buttons in Manage); **B5 fixed/flexible** tag (per-category, Manage
toggle, fixed-vs-flexible summary split); **B0 envelopes** already live. **B3 sinking funds** — the
envelope engine computes required-monthly + feeds committed; remaining: due-month Calendar dot.
Still staged: **B4 Hijri periods** (per-target Gregorian|Hijri window — ripples through
categories_data; medium), **B6 budget history grid** (/budget History: months×categories
target-vs-actual ✓/✗, honest from first target), **B7 irregular bill dates** (school-fees thin
schedule — see below). These 1–6 are the intelligence era's designated data foundation (gate note).

(Original spec retained below for the staged pieces.)
**WAVE B — Budget arithmetic (smart-now, NO intelligence; read-mostly, run before/parallel to M).**
Arithmetic arranged to feel like advice — every item states what already is; nothing proposes or
warns. Advisor's suggested order: **B first (fast), then M.**
- B0 ✅ **Envelope budgets + recovery** — SHIPPED 10 Sep (see below). Foundation for the rest.
- B1 **Committed-money view** — Σ this month's bills + loan/lease/BNPL scheduled + envelope
  contributions = "committed"; breakdown by source; grows as Wave-M items land. Budget summary +
  dashboard line. Backward/forward facts only — no "available to spend" (that's safe-to-spend, gated).
- B2 **Set-from-history buttons** — on every target/envelope input: "3-mo avg" / "6-mo avg" /
  "last month" fills the field, Hisham saves. Hidden when history is too thin (honest).
- B3 **Sinking funds** — already in the envelope engine (goal + due → contribution = remaining ÷
  months-left); needs Calendar due-dot + committed-view feed. Shares machinery with Wave-H seasonal
  goals (build once).
- B4 **Hijri budget periods** — per-target/envelope "period: Gregorian | Hijri" using existing
  Umm-al-Qura math; Categories/Budget respect the boundary; Ramadan-to-Ramadan becomes native.
- B5 **Fixed/flexible tag** per category (Manage); month views show the fixed/flexible split line;
  filter chip on Categories. (Graduates the Monarch-Flex roadmap note into a build.)
- B6 **Budget history grid** — /budget "History": months × categories, target-vs-actual per cell,
  compact ✓/✗; honest from whenever targets began (no backfilled fake targets).

**WAVE G — Guide / in-place help / changelog (task-based, self-maintaining).**
Audiences: Sarah (how-do-I in 2 min), future-Hisham (why + what was decided), next session
(STATE/BLOCKED already are machine-readable). Deadline: Sarah's arrival.
- G-1 **/guide tab** (quiet, near Settings): ~20 task recipes grouped (Daily · Monthly · Fixing
  mistakes · Money concepts · Household) — numbered steps with real UI names, text-only (ages
  better). Seed list per the brief (add expense · split · make-a-rule · bulk · confirm · edit/
  exclude · accounts · envelope+recovery · sinking fund · manage bills · cash count · read net
  worth incl. negative axis + debt toggle · report+save · exports · grey SOON tabs · alerts).
- G-2 **"How HAKIM thinks"** page: doctrines in owner language (one door for writes; truth engine
  below / face above; flag-don't-guess; honest empty states; sums prove themselves; the surplus
  gate). Rarely drifts.
- G-3 **ⓘ in-place explainers** (~8, dismissible, one sentence, sourced from guide content — single
  source): net-worth axis · envelope formula · ⊙ direct row · cleared-vs-available · queue-badge
  vs confirm-badge · utilization bar · hawl line · committed-money line.
- G-4 **/changelog ("What's new")** rendered from STATE.md, newest-first, grouped by day — zero
  upkeep (if STATE is written, changelog exists).
- G-5 **Maintenance rule → CLAUDE.md:** any brief that changes a guide-listed flow must update that
  recipe in the same commit — the guide is code, not docs. *(Bank this when G ships.)*
- Arabic-ready structure (English-only now, per localization roadmap).

**Custom bill schedules (irregular dates — school-fees 3×/year).** Firefly bills express
weekly/monthly/quarterly/half-year/yearly natively (now editable in-app), but NOT an arbitrary set
of specific dates with per-date amounts (schools front-load). Stage: a thin `data/bill_schedules.yaml`
(bill_id → [{date, amount}]) over one Firefly bill; the *surface* stays one bill ("School fees —
Aser") with its N dates visible — never N fake bills. Downstream: Calendar due-dots on true dates ·
Upcoming shows next real occurrence+amount · committed-money counts each in its actual month (no
smearing) · morning brief uses true next-due · one-tap "create sinking fund →" (amount ÷ months to
due) linking to the envelope engine. Ships with the Manage-Bills follow-up / Wave B.

**WAVE H — Household & Islamic-finance. ✅ COMPLETE (11 Sep 2026).**
- H1 ✅ **Owed-to-me receivables ledger + aging** — shipped as its own `/owed` page. Lend/repay are
  real balance-proven transfers; invariant line ties per-person sum to the account. Migrate labels
  the pre-existing lump. Receivables stay zakatable (feed the hawl trail).
- H2 ✅ **Cash-count wizard** — Accounts → 🧮 Count cash; per-currency adjustments stamped "counted",
  per-account last-counted staleness (amber >45d). Unblocks the "Cash & safes counted" square.
- H3 ✅ **Seasonal goals** — Goals → By season (Ramadan/Eid al-Fitr/Eid al-Adha/school), Umm al-Qura
  next-occurrence, auto-rolls forward. `/api/seasons`.
- H4 ✅ **Goals required-per-month math + milestones** — (remaining ÷ months-left) + 25/50/75% ticks.
- H5 ✅ **Riba & fees lens** — Reports → 💸 Cost of debt preset (`riba` report type): total, avg/month,
  per-card/per-loan bars, 6-month trend. Renders the real Wave M financing-cost data; empty-and-honest
  until costs exist.
- *Optional H polish (STAGED):* depreciation on leased/other assets; per-person receivable person-tags
  wired into the Household-by-person report; a Categories-drill inline "cost of debt" mini-line
  (the Reports preset is the primary surface).

**WAVE N — Nervous system. ✅ COMPLETE (11 Sep 2026).**
- N1 ✅ **Webhooks live-refresh** — `/api/webhook/firefly` receiver + `/api/data-version` fingerprint
  + rail.js 20s poll → 🔄 refresh pill; pages expose `window.hakimReload`.
- N2 ✅ **Transaction-links UI** — Desk picker (relates/refund/paid/reimburse) + readable rows +
  unlink. **Fixed a live bug:** endpoints were `link_types`/`transaction_links` (underscore → 404 on
  this Firefly); corrected to `link-types`/`transaction-links`.
- N3 ✅ **Recurring paid-status** — `bill_marks.yaml` marks + heuristic; committed counts unpaid
  remainder; Calendar dots flip. (Native `paid_dates` unusable — SMS imports carry no `bill_id`.)

**WAVE Z — Small closers. ✅ COMPLETE (11 Sep 2026).**
- Z1 ✅ **Strictness dial (B)** — per-category carry/strict rollover (Categories → Manage).
- Z2 ✅ **Two-period compare (H)** — `/api/category/compare`, Categories → ⇄ Compare.
- Z3 ✅ **Merchant manage surface** — Settings → Merchant map (`/api/merchants` CRUD).
- Z4 ✅ **Trip tagging** — `trip:` tags on the Desk + Reports → Trips summary.
- Z5 ✅ **Credit-utilization % bar** — SHIPPED in WAVE R.
- Z6 **Reports → Desk deep-link** — remaining small polish (optional).

**WAVE B part 2 — ✅ COMPLETE (11 Sep 2026).** B8 Hijri budget periods · B9 budget history grid
(Categories → ▦ History) · B10 irregular bill dates (`bill_schedules.yaml`, school-fees, + sinking
handshake). Plus single-sourced ⓘ explainers (rail.js `data-tip` engine, 12 concepts).

**Optional polish still logged (not gaps):** G-split dedicated Desk surface (covered by Record-payment);
Reports→Desk deep-link (Z6); Categories-drill inline riba mini-line; depreciation on leased/other
assets; envelope coaching / safe-to-spend (gated on lived surplus data); Monarch 3-bucket Flex mode;
mirror pure-save goals into Firefly piggy banks for Firefly-side visibility.

### Audit findings (10 Sep 2026)
- **Goals ownership:** Goals are a **parallel store** (`data/goals.yaml`), **not** Firefly piggy
  banks — zero calls to `/api/v1/piggy_banks`. *Kept parallel deliberately:* piggy banks are
  rigid (one asset account, save-only — no "pay down card Y", no target dates/milestones). Our
  store does what they can't. **Honest cost:** these goals are invisible in Firefly's own UI and
  are only preserved via the restic snapshot of `data/` (not Firefly's DB). *Recommendation:*
  keep the parallel store; optionally mirror pure "save" goals into piggy banks later for
  Firefly-side visibility. No migration needed now.
- **Firefly-native usage:** Using native → bills (Recurring, read-only source of truth),
  `transaction_links`, attachments, categories/tags/accounts, reconciled flag. Reimplemented /
  parallel → rules (merchants.yaml vs native rule engine — #34), budgets (`category_targets.yaml`
  — deliberate, richer periodicity), piggy banks (goals.yaml — above), webhooks (poll vs push —
  #38), recurrences (we read bills but don't drive native recurrence creation).

### Roadmap note — Monarch "Flex budgeting" (3-bucket)
Monarch's Flex model splits spending into **Fixed / Flexible / Non-monthly** rather than dozens
of line-item category budgets — you budget one "Flexible" pool and spend freely within it.
Worth considering as an *alternative budget mode* once the current per-category targets have
lived history. Not a near-term build; recorded so it isn't lost. Pairs with #23 (customizable
dashboard) as "budgeting philosophy" options.

### Inward #6 — disposition of every remaining Firefly-native feature (the inward map, closed)
Verified against our actual API touchpoints (`ff_all`/`ff` calls): we hit **accounts, bills,
transactions, categories, currencies, attachments, transaction_links, link_types, about**. Every
other native surface, one line each — adopt / stage / exclude + why:

| Firefly-native feature | We do | Verdict |
|---|---|---|
| **Rule engine** (`/rules`, `/rule_groups`) | reimplemented at import (merchants.yaml) | **ADOPT → WAVE R1** (crown find) |
| **Webhooks** (`/webhooks`) | poll | **STAGE → WAVE N1** (push > poll) |
| **Transaction links** (`/transaction_links`) | backend only, no UI | **STAGE → WAVE N2** (UI) |
| **Recurrences** (`/recurrences`, auto-create) | read bills; don't auto-create | **STAGE → WAVE N3** (native paid-status first; auto-create later) |
| **Piggy banks** (`/piggy_banks`) | parallel goals.yaml | **EXCLUDE** — too rigid (audit above); optional later mirror |
| **Budgets + budget-limits** (`/budgets`, `/available_budgets`) | parallel category_targets.yaml | **EXCLUDE (deliberate)** — our periodicity/rollover is richer; Flex mode (roadmap) is the real alt |
| **Object groups** (`/object_groups`) | not used | **EXCLUDE** — our account grouping (`account_kinds.yaml` + `_group2`) already covers it |
| **Multi-currency** (`/currencies`, foreign-amount) | native — read + create, FX override live | **ADOPTED** (done) |
| **Reconciliation** (reconciled flag) | native per-txn flag | **ADOPTED** (done) |
| **Tags** (`/tags`) | write tags on txns (person/class); no tag-manager page | **STAGE (low)** — a tag-admin page only if the tag list grows unwieldy |
| **2FA / OAuth clients** (`/oauth`) | PAT only, single-user LAN | **EXCLUDE** — single operator on the tailnet; PAT + full-disk backups is the threat model. Revisit only for guest/consultant access (Shield agent, §F #30) |
| **Bills** (`/bills`) | read-only source of truth (Recurring + Calendar layer) | **ADOPTED** (done) |
| **Attachments** (`/attachments`) | view/add on Desk | **ADOPTED** (done) |

Net: the inward map is now as fully dispositioned as the outward one — every native feature is
live, waved, or excluded-on-the-record. Nothing left unexamined.

### Decisions on record (10 Sep 2026)
- **Goals stay parallel (not piggy banks): ACCEPTED** by Hisham — reasoning shown (pay-down-card
  + target-date goals don't fit piggy banks), honest cost logged (invisible in Firefly UI, restic-
  protected). No migration.
- **Nisab value: PENDING Hisham.** The hawl trail is recording against the **85g-gold estimate
  (SAR 25,500)**, flagged as unverified in /settings + every log line. Awaiting his figure or an
  explicit "use the estimate."
- **Card limits: PENDING Hisham** (4331 / 5158 / 5019 / 6510 / 8381). Credit-utilization bar
  (Z5) unlocks on receipt; will not be faked before then. *(Resolved 10 Sep — limits received, Z5 shipped.)*

### Envelope coaching — the gate line (10 Sep 2026)
Envelope **arithmetic** shipped (Part A + recovery countdown): a pot accumulates, spending draws it
down, negative is shown honestly with a pure-math recovery date. What stays **gated behind lived
surplus data** (Budget engine + Debt coach): proposing envelope sizes, "you should stop buying",
purchase-time warnings, safe-to-spend / "what's left to spend" as a forward number, any unprompted
suggestion. The recovery arithmetic is their **foundation and future training ground** — when the
gate opens, Hisham's envelopes / BNPL flows / recovery patterns become the coach's first real
scenario, and its advice will fit because it learned from his actual life. The countdown does the
job meanwhile: it makes the consequence *unmissable* (a rose "−3,000 · recovering until Dec" is a
stop sign stated as fact, not command) without guessing with authority.

### Qattah (قطة) — staged follow-ups (11 Sep 2026)
Headline SHIPPED: you-paid shared order → your share stays expense + per-person receivables
(origin:qattah), balance-proven; inner-circle picker; قطة lens + origin breakdown on Owed-to-me.
Staged (need the asset↔liability offset shape — the M2.0 wall — resolved first):
- **I-owe direction:** someone else paid the order; you owe your share → book your consumption as an
  expense funded by the per-person "I owe" liability (withdrawal source=I-owe→expense, origin qattah).
- **⚖️ Settle action** on a person's card: show both directions ("owes you 300 · you owe her 200 →
  net 100"), one tap books an explicit settlement discharging both sides to the net (never implicit),
  with a plain history line. Real repayment of the net = a normal transfer, closing it.

## Points-optimization strategy (everything-on-card-for-miles) — debt-free-era unlock
**Blocked on:** Hisham's own gate — "depends on having no credit card debt." Routing all spend through
the Alfursan cards to farm miles only makes sense once there's no revolving balance (utilization risk +
interest would dwarf miles value). **Foundation shipped 12 Sep:** the Alfursan miles tracker (balance ·
batch-expiry · earn-context from card spend) is the data layer this analysis will read. **Unlock when:**
card debt reaches ~0 → Debt-coach/intelligence can model spend-routing (which card per merchant category),
points value vs utilization/interest, and a "safe to farm" signal. Intelligence territory, not arithmetic.
