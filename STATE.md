# HAKIM — build state
_Last updated: 14 Sep 2026._

## 📊 One shared chart tooltip — every chart gives values on hover (one-owner) (14 Sep 2026)
**Problem:** dashboard cash-flow bars showed no values — no labels, no hover. Charts you can't read a
number off are decoration. **Fix:** ONE shared tooltip behaviour (`window.hkTip` + `window.hkMoney` +
`window.hkTipFlow` in `face.js`, `.hktip`/`.barval` in `face.css`) — a delegated `[data-tip]` listener
on `document` renders the same dark, face-language popup (tabular-nums, green in / red out, edge-clamped,
follows the cursor) for **every** chart on **every** page. No per-chart tooltip code except where a chart
needs a nearest-point crosshair (dashboard net-worth curve), which now renders its label **through** the
same `hkTip` — the one remaining bespoke `#ttip` was deleted.

**Cash-flow (the reported bug):** each month is a `.cfm` carrying `data-tip="${hkTipFlow(lbl,in,out)}"` →
period · in · out · net; value labels sit on the bars (`abbr()`, suppressed under 26% height so they never
crowd); axis label "peak SAR …" top-right; helper line "hover a month for in · out · net".

**Sweep — which had readable values vs. which needed hover added:**
- *Already readable in-place (values printed on the chart):* Reports category bars (`.bv`), Sankey nodes
  (`skv` tspans + trunk total), Debt/Wealth/Budget allocation bars. Sankey also **gained** a hover tip
  (value + % of flow) for parity.
- *Had a hover already:* dashboard net-worth curve (bespoke crosshair) — **migrated** to `hkTip`.
- *Needed hover added (were silent):* dashboard **cash-flow** bars; **Forecast** 90-day curve; **Wealth**
  net-worth trajectory; **Family** per-person spark; Reports **line** (`drawLine`) and **donut**
  (`drawPie`). All now carry per-point transparent `data-tip` hit-bands → the shared popup.
- *Listed in the brief but don't exist yet:* miles sparkline, fund price lines — no such page (noted, not
  faked).

**Native `title=` → `data-tip=`:** converted the 5 remaining native-tooltip charts (dashboard spending-share
/ household / day-of-week, today committed-source, categories sparkline) so they speak the same language.

**Verified Hisham's way** — real hover driven over CDP (not just a static render) on both widths, tip text
+ screenshot captured: cash-flow @2400 & @1440 ("Jul 26 · in +SAR178,671 · out −SAR163,241 · net
+SAR15,430"), net-worth curve, forecast, wealth, family, sankey ("Other income · SAR298,102 · 74% of
flow"), reports donut ("Sarah shopping · SAR51,708 · 7%"), reports line ("2026-07 · SAR15,430"). Zero
console errors. `smoke_pages.sh` PASS (24/24); transfer / net-worth / review-parity / config-cache / perf
/ today guards all PASS.

## 🐛 Dashboard dead on load — `mrange is not defined` (root cause + why the guards missed it) (14 Sep 2026)
Every other page fine; only `/dashboard` failed. **Not a 500** — `/dashboard` and `/api/dash` both served
200 with valid data. The break was **frontend**: the browser console threw `Uncaught (in promise)
ReferenceError: mrange is not defined` at render, so `#body` never populated.
- **Root cause:** `mrange()` (carries the active month into deep-link hrefs) is called in `render()` and
  `household()`, but its **definition was collaterally deleted** during the Today turn's forward-view
  removal — the `del lines[...]` bulk edit that stripped `next7line()`/`headsline()` took `mrange` with it.
  Fix: restored the one-line function above `render()`. (`aacd5d1` shipped the dashboard broken.)
- **Why the fixtures didn't catch it — the honest gap:** `node --check` PASSES on a page that *calls a
  deleted function* — an undefined call is a runtime `ReferenceError`, not a parse error. The 5-point bar
  (parse · door-count · `${}`-leak · raw-markup · geometry) is all **static text analysis** — none of it
  executes the JS. And I verified Today/Family that turn but **never re-loaded the dashboard** after the
  shared-code refactor. Fixtures green + live path dead = exactly the class the brief predicted.
- **Guard extended (so it can't recur):** `review-ui/smoke_pages.sh` headless-loads **all 24 pages** and
  fails on any JS console error; wired into the CLAUDE.md ritual for any page-script change. Sweep now green
  across all 24. Dashboard re-verified at 2400px (hero · month's shape · household · cash flow · cards ·
  recent · completeness · chore line — all alive).

## 🌅 THE OPENING COMPLETE — Zakat + Wealth (tabs 8 & 9 of 9) LIVE · all nine open (14 Sep 2026)
The last two — full machinery, honest-empty until the papers evening.
- **Zakat (`/zakat` + `/api/zakat`):** the **zakatable base** (24 liquid/monetary parts, property excluded)
  checked against the **nisab**, over the existing hawl tracker + `_zakatable_total`. Live: base SAR 20,084 <
  nisab SAR 25,500 (an **estimate** until the verified 85g-gold figure is set) → below the line → hawl not
  started; the daily tracker (4 records) watches for the crossing. **Honest-empty:** cash-only base until
  certificates/HISSAR/gold are entered. 2.5% computes only above the line, after a full lunar year.
- **Wealth (`/wealth` + `/api/wealth`):** **whole** net worth (−128,170), **allocation** by class
  (Bank 52% · Digital 46% · Cash 2% — cash-only until positions load), **currency exposure** (SAR 100%),
  restricted-vs-available, net-worth trajectory (reused from dash). **Performance** honest-empty — computed
  **only from own entered prices, no market data/benchmarks** (the registered charter; benchmarks stay
  HISSAR/BAHHATH). Opens when positions carry a cost basis + current value.
- **The SOON board is retired** — all nine gated tabs are live rail entries; rail.js drops the "Coming in
  waves" section when the board is empty. **9 of 9 open.**
- **Proof:** fixtures `check_zakat.py` (base=Σparts · nisab check · 2.5% only above · hawl honest) +
  `check_wealth.py` (allocation & currency reconcile to assets · net worth canonical) — green; guide
  recipes for both; verified 2400px; perf/net-worth green; pushed.
- **The last mile is the papers evening:** entering certificates (bank·principal·rate·payout·start/maturity),
  HISSAR Farm + Position balances, gold grams, funds — then net worth becomes whole, Zakat gets a real base
  vs nisab, and Wealth shows the true allocation. Every door is built and waiting.

## ◐ THE OPENING · Budget (tab 7 of 9) — LIVE · the last openable-now tab (14 Sep 2026)
Manual targets (already live) + the AI-**proposed** layer, evidence-backed and gated.
- **`/budget` + `/api/budget`:** **Your targets** — the 5 manual budgets with a progress bar vs this
  month's spend + a clear button. **Proposed targets** — for every untargeted spending category, the
  **average of its spend across complete months**, shown WITH its evidence (the monthly figures as bars)
  and this-month actual. One tap **"set SAR X/mo"** accepts it — writing through the **single** existing
  door (`/api/category/target`), so Budget/Categories/committed-money never fork.
- **Honesty:** proposals wear the maturity banner (*needs 3 · have 2 · ready after 30 Sep*) — "a two-month
  average is a starting point, not a verdict." The villa proposal (avg 62,783/mo) shows its two big months
  as evidence, so a project reads as a project, not a habit.
- **Sequence:** Budget migrated SOON → live rail entry. **The openable-now six are all open (7 of 9);
  only Zakat + Wealth remain** — both wait on the papers evening (positions/prices).
- **Proof:** fixture `check_budget.py` (proposal == avg of its evidence · targeted/proposals disjoint ·
  total-target sound · accepting a proposal writes a real target through the one door, then restored ·
  maturity real); guide recipe; verified 2400px; perf green; pushed.

## 💡 THE OPENING · Insights (tab 6 of 9) — LIVE (14 Sep 2026)
The pattern finder — surfaces only what the sample supports, and reuses the deeper views instead of
rebuilding them.
- **`/insights` + `/api/insights`:** **Early reads** = observations the data already supports, each with
  its sample shown — villa concentration (41% of this month) and heaviest weekday (Monday, across 10
  weeks). **Coming into focus** = the 3-month patterns (rising/falling categories, 2× anomalies, seasonal),
  each naming its unlock date (*after 30 September*). No estimate is ever dressed as a pattern; the weekday
  read only appears because ≥6 weeks exist.
- **Reuse, not rebuild (the audit rule):** "Go deeper" LINKS to the **Reports Sankey** and **Subscriptions**
  recurring detection — Insights never duplicates the flow-Sankey that lives in Reports (BLOCKED §16 fixed).
- **Sequence:** Insights migrated SOON → live rail entry; **3 tabs remain** — Budget · Zakat · Wealth (the
  last two wait on the papers evening).
- **Proof:** fixture `check_insights.py` (early reads carry a sample · 3-month patterns stay pending ·
  weekday gated on ≥6 weeks · links reuse Reports/Subs · maturity real); guide recipe; verified 2400px;
  perf green; pushed.

## 💳 THE OPENING · Debt coach (tab 5 of 9) — LIVE (14 Sep 2026)
Payoff strategy on real cards + financing, SIMAH-floor aware, recommendation gated behind a real surplus.
- **`/debt` + `/api/debt`:** every card (balance · limit · utilization · minimum) and financing (balance ·
  rate · kind) — total **−148,254**, minimums **−4,413/mo**. **Avalanche** (highest-rate first) / **Snowball**
  (smallest-balance first) toggle. Interest-free BNPL always sorts LAST in avalanche; snowball is strict
  balance-ascending (both fixture-proven). Card APRs aren't stored → cards sort to the top of avalanche with
  an honest flag ("Saudi cards carry the highest rates — enter each to rank exactly").
- **The floor (SIMAH-aware):** always pay every minimum — a missed one damages the credit record for years;
  extra goes to the #1 target. Stated plainly, prominently.
- **Recommendation GATED:** the months-to-debt-free timeline needs a **validated monthly surplus** — and
  there isn't one (2 complete months averaged net **−21,929/mo**). "A plan built on a surplus that isn't
  there would be a guess — so the order is shown, the timeline waits." The doctrine holding exactly where
  it's tempting to look clever.
- **Real signal surfaced:** SABB Mastercard •5158 shows **106% utilization** (over limit) — honest, not hidden.
- **Sequence:** Debt coach migrated SOON → live rail entry; **4 tabs remain** (Insights · Budget · Zakat · Wealth).
- **Proof:** fixture `check_debt.py` (total==Σbalances · snowball ordering · avalanche keeps 0%% last ·
  minimums total · recommendation gated); guide recipe; verified 2400px; perf green; pushed.

## 📈 THE OPENING · Forecast (tab 4 of 9) — LIVE (14 Sep 2026)
The most honesty-sensitive build: a 90-day cash curve on 2 months of history — so it separates what it
KNOWS from what it INFERS, hard.
- **`/forecast` + `/api/forecast`:** the **known** daily curve is dated obligations only — installments
  (schedules), priced bills (monthly ones projected across the window, irregular by their schedule), card
  minimum payments (projected), certificate payouts. The **provisional** overlay adds a modelled daily
  discretionary burn from complete months — **off by default** (an explicit opt-in), because on 2 villa-
  heavy months it's ~SAR 5,900/day and would swamp the confident line. Leads with what's known.
- **The real insight it surfaces:** cash goes **negative on 25 Sep** on dated obligations alone (School
  fees 54,750 > 19,834 cash) — a red crunch banner names the date and says *plan the cover*, not a
  prediction. Lowest point −53,794 · 1 Dec.
- **Honesty everywhere:** the pattern line wears the maturity banner (*ready after 30 Sep*); an
  understated-note flags that 15 unpriced bills mean even the solid line is incomplete.
- **Sequence:** Forecast migrated SOON → live rail entry; **5 tabs remain**. (Note: an early build failed
  silently because the Dockerfile COPY'd forecast.html before it existed — the image quietly reused the old
  app.py; caught it and wrote the page first.)
- **Proof:** fixture `check_forecast.py` (known curve sound: start=cash, end=cash+Σevents · lowest &
  negative-date truthful · burn ≥ 0 · maturity real); guide recipe; verified 2400px; perf green; pushed.

## 🔁 THE OPENING · Subscriptions (tab 3 of 9) — LIVE (14 Sep 2026)
Detected + declared recurring inventory, the honest monthly commitment, and undeclared-charge proposals.
- **`/subscriptions` + `/api/subscriptions`:** the **declared inventory** (your recurring bills, amount when
  set), a **next-charge calendar**, and **detection** of recurring merchants from the ledger. A detected
  charge only surfaces as a proposal if it's **subscription-like**: stable amount (≤15% spread),
  subscription-sized (≤3000), roughly one-per-month, and NOT a transfer/fee/ATM/installment — the noise a
  naive "recurs in 2 months" otherwise catches (villa spend, family transfers, POS runs). Live: 20 declared
  · 0 clean-undeclared · **monthly total SAR 2,174** (declared priced only).
- **Honest-but-incomplete banner:** names the 15 unpriced bills — the monthly total firms up the moment
  Hisham prices them (this is the tab his 10-minute bill sitting most directly improves).
- **Price-creep / unused watch:** honest **"watching since Sep 2026"** with the maturity banner — flags
  creep/unused only once 3 months complete (*ready after 30 September*).
- **Sequence:** Subscriptions migrated SOON → live rail entry; **6 tabs remain**.
- **Proof:** fixture `check_subscriptions.py` (total == declared+detected · detection clean of
  transfers/fees · unpriced count truthful · maturity real); fixed a date-render bug ("next Invalid Date");
  guide recipe "Track your subscriptions"; verified 2400px; perf green; pushed.

## 👪 THE OPENING · Family (tab 2 of 9) — LIVE (14 Sep 2026)
Per-person truth on real person-tags + the qattah/owed ledger — openable now on the household's data.
- **`/family` + `/api/family`:** a card per person (from `PERSON_TAGS`) with this-month **spend/income/net**
  (real tag attribution — a person's spend == the sum of THEIR tagged withdrawals), their **pocket**
  (spendable balances they own — asset accounts only; card/loan debt is **excluded** so a person's own
  Mastercard can't drag their pocket negative), **qattah/owed** balances (reused from the Owed-to-me
  per-person roll-up), and a **monthly-spend sparkline** across complete + current months.
- **Honest maturity:** the per-person trend wears the shared banner — *needs 3 complete months · have 2 ·
  ready after 30 September* (computed, not hardcoded). Qattah/lending shows an honest empty state until a
  tab or family loan is recorded.
- **Sequence:** Family migrated SOON → live rail entry (joins the reorderable set); **7 tabs remain**.
- **Proof:** fixture `check_family.py` (real attribution · pockets exclude debt · trend + maturity sound);
  guide recipe "See the family per person"; verified at 2400px; perf/net-worth guards green; pushed.

## 🌅 THE OPENING begins — honest-maturity foundation + Today (tab 1 of 9) (14 Sep 2026)
The surplus gate becomes a **dimmer, not a lock**: every gated tab will open and be honest about its own
youth. This session lays the foundation and opens the first tab. Sequence chosen (openable-now first):
**Today → Family → Subscriptions → Forecast → Debt coach → Insights → Budget → Zakat → Wealth** (the last
two wait on the papers evening).
- **Honest-maturity foundation (shared by all nine):** `_complete_months()` counts months fully in the
  past that carry data (current month is in-progress, never "complete"); `_maturity(need)` → how many you
  have, whether met, and the **date it's met — computed from the real ledger, never hardcoded** (today:
  have 2 · need 3 · *ready after 30 September*). Exposed at `/api/maturity`; `window.matBanner()` /
  `window.matTag()` render the banner in the Face language (face.js + face.css). No estimate is ever
  printed as a pattern.
- **Today (tab 1) — LIVE.** `/today` + `/api/today`: **safe-to-spend** (honest arithmetic `cash −
  committed-remaining`, carried **provisional** — 14 unpriced bills understate committed money, named
  inline), **the day's shape** (in/out/entries today), **due soon** (next 7 days + long-lead heads), 
  **committed this month** (bills·envelopes·cards·debt bar), **landed today**. Face-language, Grotesk hero.
- **Charter removal-condition honored:** the dashboard's temporary `next7`/`heads` + `next7line()`/
  `headsline()` were **deleted**; the forward view moved to `_forward_due()` → Today, which owns it
  permanently. Dashboard is back to pure "where do I stand". BLOCKED.md exception marked RESOLVED.
- **SOON board:** Today migrated from "coming in waves" to a **live rail entry** (joins the reorderable
  set); 8 tabs remain on the board.
- **Proof:** new fixture `check_today.py` (safe-to-spend arithmetic · maturity-from-real-ledger · dashboard
  retired forward view · Today owns it) + wired into the ritual (CLAUDE.md); guide recipe "Read your Today
  page" added; verified at 2400px; perf/net-worth guards green; pushed to the remote.

## ⠿ Sidebar reordering + long-lead warnings + tag/remote housekeeping (14 Sep 2026)
- **D · Sidebar reordering (own nav order).** The shared rail is now drag-reorderable and tabs are
  hide/show-able — persisted server-side (`/api/nav/prefs` → `data/nav_prefs.yaml`) so **every page**
  renders Hisham's order. Tap **⠿ Arrange sidebar** → grips + eye toggles appear, rows become draggable
  (mirrors the Accounts row DnD); **✓ Done** saves, **reset order** restores default. **Hiding is
  display-only** — a hidden tab stays reachable by URL (`/rules → 200`) and ⌘K search; nothing is deleted.
  New tabs (The Opening) auto-join the orderable set in their default slot. Proof: POST order → reload →
  rail shows it (Reports-first, Rules hidden, verified); round-trip GET matches; parse clean.
- **A · Long-lead warnings restored (closing the gap I flagged).** The 7-day line didn't reach the
  months-ahead forget-proofing, so added a SECOND quiet line **"Ahead"**: balloon ≤6/3mo · certificate
  maturity ≤1mo · card expiry ≤60/30d (`heads` in `_dash_impl`; `headsline()`). A KNOWN dated obligation
  named ahead — no prediction, so forget-proofing not forecasting. Hidden when the horizon is clear
  (currently empty — no leases/certs, nearest card expiry 321d). Same temporary-exception removal
  condition as `next7` (both go when Today/Forecast ship — updated in BLOCKED.md).
- **B · design-finale tag moved** to `2d896e6` (the polish trio — the true last design act; the circle
  fixes `434478b` are its ancestor).
- **C · off-machine code backup:** private GitHub remote created + pushed (code only — `data/` and `logs/`
  stay gitignored and local). [see the commit / remote report]
- Perf + config-cache guards green (dash warm still 0ms despite the added read loops).

## ⏳ Dashboard "Next 7 days" line — temporary charter exception (14 Sep 2026)
The dashboard charter removed all forward warnings (upcoming · committed · balloon · maturity), but their
permanent home — Today/Forecast — doesn't exist yet, so for the weeks before Today opens the daily page
would go dark on the forget-proofing we deliberately built. Fix: **ONE compact "Next 7 days" line, due
dates only.**
- **Backend `next7` (`_dash_impl`):** merges what's DUE in the next 0–7 days from the same sources the old
  alerts used — bills/card-payments (`bills_view`), BNPL/lease **installments + balloons** (`_schedules`),
  and **certificate maturities** (`api_certificates`) — date-sorted, amount when known (honest "—" when a
  bill amount is still a placeholder). Cached in `_vcache`; dashboard warm render still 0ms.
- **Frontend `next7line()`:** a single teal line — 📅 Next 7 days · `name` `date` · … · calendar → —
  placed below the money summary (household) and above the chore line. **Hidden when nothing's due.** No
  pace, no forecast, no safe-to-spend — just what's due and when. Verified live (flynas installment
  · 20 Sept · SAR 191).
- **Logged in BLOCKED.md as a deliberate, dated exception with a REMOVAL CONDITION:** delete `next7`
  (backend) + `next7line()` (frontend) the day the Today surface ships — Today owns this permanently. Not
  charter drift; a two-week bridge so the forget-proofing doesn't go dark.

## 🌊 Sankey flow chart in Reports + registered ideas (14 Sep 2026)
- **Sankey (the one thing competitors do better) — built.** New Reports type **Flow (Sankey)**: a single
  ribbon diagram **income sources → the pool → expense categories → (Saved | drawn from reserves)** for any
  period, in the face language + directional palette. **Honest by construction — it conserves flow:** left
  column and right column each sum to `max(in, out)`. When spending exceeds income a **"Drawn from reserves"**
  source band shows exactly where the gap came from (no fake "savings"); when income exceeds spending a
  **"Saved"** band appears. Top-11 expense categories + an **"Other (N categories)"** roll-up keep it
  legible; empty-period → honest "No flows in this period." Backend: `sankey` type in `compute_report`
  (`income_src`/`expense_cat` via `_report_filter` + `_main_cat` — same filters as every other report).
  Proof: script parses, labels fully legible (viewBox widened for the side labels), trunk labeled
  **"Money flow"** when it includes reserves (not mislabeled "Income"); verified at 2400px + 1440px;
  conservation checked against the totals strip (348,640 income + 52,879 reserves = 401,519 = expense).
  Guide recipe "Build & save a report" updated in the same commit.
- **Registered ideas (BLOCKED.md, so nothing rides on memory):** ① Wealth-tab position performance
  analytics (TWR · annualized · allocation drift · contribution-to-growth) from **own entered prices only** —
  no market data/benchmarks (tracking-not-monitoring; benchmarks stay HISSAR/BAHHATH). ② Long-horizon
  net-worth projection ("position in 5 years") — beyond Forecast's 90-day scope, **unclaimed, needs a home**.
  ③ Merchant dossiers — merchant as a first-class entity mirroring category dossiers, feeds the receipts wave.
- **Note:** the polish trio's first three legs (Space Grotesk hero · hero-zone spacing · numeric polish)
  already shipped earlier this session (`design`-era commit) — this brief re-sent them; only the Sankey was new.

## 📊 Dashboard charter — "where do I stand" (money-first reorder + month's shape + household) (14 Sep 2026)
The dashboard now answers **position & the month's shape** — slow-moving truth — and deliberately cedes
pace/safe-to-spend/upcoming/forecast to the gated surfaces (Today · Insights · Forecast). Charter logged
in BLOCKED.md so the gated builds don't duplicate it.
- **Money opens the page (reorder):** net-worth hero + chart → position tiles (card debt · available cash)
  → the month's shape → household split → *then* the one quiet chore line → cash flow → where money went.
  The system-chore strips (queue · confirm · bills-unset) **collapsed into ONE quiet "N things to tidy"
  line** placed below the money, expandable; only **critical** health (backup/agent) stays prominent up
  top. The **pace bar was removed** (pace ≠ position — it's Insights/Today's job).
- **The month's shape (new):** in · out · net for the month, with **last month** and the **3-month
  typical** shown inline — a *completed-period comparison, explicitly labeled "not a pace or forecast."*
  Plus the **fixed-vs-flexible** split rendered here from the **one** definition (`_cat_meta` flex, same as
  Categories — no fork). Honest when history is thin ("comparison appears once prior months complete").
- **Household split (new — unique since Sarah's import):** this month's spending + net split
  **Hisham · Sarah · joint · unassigned** (person tags first, then unambiguous account-owner, else honestly
  *unassigned* — flag-don't-guess), a three-way bar + rows tappable through to each person's filtered Desk.
- **Removed by charter (relocated, not lost):** Upcoming-payments panel + Committed strip + the forward
  alerts (balloon-due / certificate-income / maturity) — they belong to Today/Forecast; until those land
  they surface on their detail pages. ⚠️ Flagged in BLOCKED.md: re-add a balloon warning as a deliberate
  exception if wanted before Forecast ships.
- **Backend:** `_dash_impl` gains `shape` (this/last/typical + fixed/flex) and `household` — read-only
  aggregation over `all_txns()`; net worth still reads canonical `_networth()`.
- **Guide kept in sync (same commit):** recipes "Read committed this month", "Set up a car lease", and
  "When an alert appears" updated to match the new dashboard story.
- **Proof:** verified at **2400px and 1440px** (money-first order, month's-shape comparison, household
  three-way bar, collapsed chore line, no Upcoming panel, grotesk hero); guards green — net-worth
  consistency, **perf within budget** (the added aggregation didn't blow it), config-cache. No `${}`/leaks.

## ✒️ The polish trio — the last design act (13 Sep 2026)
The closing flourish, then all effort turns to data + living. Three moves, hero-only, density preserved.
1. **Display typeface for hero numbers only.** Proposed 3 self-hostable (SIL OFL, license-clean) candidates
   — a grotesk, a serif-with-edge, a mono-display — each rendering the REAL net worth (−128,045.38) with
   identical numeric-polish styling; Hisham picked **A · Space Grotesk 600**. Self-hosted at
   `/hakim-grotesk.woff2` (13 KB, immutable 1yr cache) via a new app.py route + Dockerfile COPY — **no CDN,
   local-first intact**. face.css: `@font-face` (font-display:swap so the fallback serif paints first, no
   blank hero) + `--face-display` var. Wired to every genuine hero slot: dashboard net-worth (`.hero .n`),
   accounts net-worth + holdings (`.nw .n`), Desk composer amount (`.amtdisp`), session-complete count.
   **Body, mono, and UI type untouched** — the mono ledger grammar (category/stat tiles) is deliberate and
   stays.
2. **Hero-zone spacing pass** — the top ~400px only, where the "expensive" feeling lives; density below the
   fold is untouched by design. Dashboard hero card `28/26/24` padding + bigger number-to-stats gap;
   Accounts `.nwcard` roomier; Categories `.sumcard` + taller stat tiles; the BNPL/loan **plan card**
   (`.finbox`/`.fingrid`) more air in its schedule header/summary.
3. **Numeric polish** — one rule set in the face layer: `.amt`/`.tnum` tabular-figure utilities +
   decimal (`.d`) and currency (`.c`) muting, and the hero decimals firmed to a quiet-but-legible fraction
   (opacity .5, clear gap before the ± delta — fixed a crowding the wider grotesk exposed). Mono amounts
   are already fixed-width; this brings the sans heroes to the same typeset alignment. **Honest boundary:**
   the reusable ruleset + all heroes are done; I did NOT rewrite every render fn app-wide to wrap each
   decimal (a large, risky sweep for a closing act) — offered as a follow-up if wanted.
- **Not copied from Money Pro/Copilot (deliberately):** their below-the-fold whitespace (you'd scroll for
  data you need at a glance) and their count-up/spring animation budget (friction on a system opened 15×/day).
- **Proof:** font route serves `200 · font/woff2`; face.css carries the `@font-face`; verified at **2400px
  and 1440px** on Dashboard · Accounts · Categories (+ hero-crop for the decimal/delta fix) — grotesk hero
  paints, spacing reads roomy, no leaks. All **seven ritual guards green** (transfer · net-worth · date-edit
  · perf · corrections · config-cache · review-parity). **The face era is now truly closed.**

## ⚡ Multi-select Select-all / Clear / group shortcuts (Reports + Desk bulk) (13 Sep 2026)
With 34 accounts and 33 categories, ticking a filter by hand is absurd. Fixed the class, not one page.
- **Reports · Accounts filter:** a compact control row — **Select all · Clear** + **data-driven group
  chips** generated only for groups present in the ledger: Wallets & cash · Bank accounts · Cards ·
  Digital · Financing · Receivables, plus owner shortcuts **Hisham’s · Sarah’s**. Owner isn't a stored
  field — it's derived transparently from the account name (`ownerOf`), and since the selection is always
  visible and hand-adjustable it's a convenience, never an invented fact (flag-don't-guess honored).
- **Reports · Categories filter:** **Select all · Clear · Expenses · Income · With-targets** (the last
  reads the live `target_monthly` set). Each chip shows its count.
- **Honest header + default (brief item 3):** the header reads **“All accounts” / “All categories”** when
  nothing is checked, **“N of M selected”** when partial. Empty selection = **all** (no filter) — the
  backend already omits the param when the set is empty; a hint line states it so an untouched filter can't
  silently exclude everything. Select-all and Clear both run across everything; the labels tell the truth.
- **Desk bulk-confirm (item 4 — same gap elsewhere):** select-mode let you tap rows one by one with no
  select-all. Added **Select all (N) / Select none** to the batch bar, reachable the moment you enter
  select mode (bar now shows at 0 selected; action buttons appear once ≥1 is picked). Count stays live as
  rows stream in.
- **Audit (item 4):** Rules “Apply to existing” is a single-button action (no picker) and Compare is a
  two-period pick — neither is a many-item multi-select, so nothing to change there. Only Reports + Desk
  bulk had the gap; both fixed.
- **Quote-trap avoided (the lesson):** group chips call `acctNames('Cards')` / `catNames('exp')` which
  **recompute** the member names on click — no JSON array of names is inlined into the onclick, so
  `"Sarah's wallet"` (apostrophe) can never break the attribute.
- **Proof:** the *real* reports.html functions run against **live data** (indirect-eval harness): Select
  all → 34; Cards → 6; Hisham’s → 6; Clear → “All accounts”; Expenses 30 / Income 7 / targets 6; empty
  filters omit from the query string. A **Cards-group report runs end-to-end** — 162 rows, every one
  touches a card (the 22 non-card rows are card-payment *transfers*, i.e. correct two-sided visibility,
  not a filter leak). Verified at **2400px and 1440px**; ritual guards (transfer/perf/review-parity/
  config-cache) green. Guide recipe “Build & save a report” updated in the same commit.

## 🐛 Two one-truth bugs killed: budget targets not saving + the review-count fork (13 Sep 2026)
Two reports, one root family — a value computed twice, or served stale, so a surface lied.

**(A) Budget targets "didn't take."** Root cause **measured, not guessed:** the write persisted fine
(`category_targets.yaml` got `Car: {amount:1500}`), but `/api/categories` still returned `target=None`
because the `_vcache` layer is keyed on the *ledger* data-version — and a YAML **config** write doesn't
bump `_DATA_EPOCH`, so the cached view served the pre-write config. This is the **stale-config class**,
now hit twice (card registry in the past, budget targets today).
- **Generalized fix (kills the class for every YAML store):** `_config_sig()` sums the mtime of every
  `*.yaml` in `data/` and is folded into the `_vcache` key alongside `_data_version()`. Any config write
  — targets, envelopes, tree, meta, merchants, registry, schedules — now invalidates cached views on the
  next read. Scoped to `*.yaml` only (volatile JSON like `hawl_trail`/`undo` must not thrash the cache).
- **Proof:** set 1500 → read 1500; change 2000 → read 2000; clear → read None — all immediate. Perf guard
  still 0ms (the sig is a cheap mtime sum). No orphaned target configs from the earlier orphan-merge.

**(B) "To review · 7 items · SAR 14,021" opened an empty Desk.** The net-worth one-truth lesson,
re-learned. **Two definitions:** Categories counted every category-**less** row (`_main_cat in ("","To
review")`) — 7 phantom transfers/ATM-withdrawals/card-payments — while the Desk queue counted only the
genuinely undecided (`category == "To review"`) and honestly showed **0**. A door onto an empty room.
- **Fix:** Categories now uses the **one canonical definition** (`_main_cat(t["category"]) == "To
  review"`, app.py:3812) — the Desk's. The 7 were all by-design category-less (transfers, excluded
  corrections, funding legs), so the count reads **0** and the strip **hides** (frontend already did
  `if(!DATA.review) return`) — no-dead-doors law satisfied. When >0 the strip's door lands on the Desk's
  review queue = exactly those rows.

**Two fixtures added to the ritual so neither class can drift back:**
- `check_config_cache.py` — a YAML-config write is reflected by the *very next* cached read (set a real
  category target through the endpoint → read `/api/categories` → restore). One fixture protects every
  YAML-backed store permanently.
- `check_review_parity.py` — Desk queue count == canonical all-time, Categories strip == canonical
  month-scoped; a category-less transfer must never count as "review" on either surface.
- Both **PASS**; full existing ritual (transfer/net-worth/date-edit/perf/corrections) still green;
  Categories verified clean at **2400px and 1440px** (strip absent, no `${}`/raw-svg leaks).

## 🔧 Circles icon-anchoring fixed (all ring paths) + component-path parity (13 Sep 2026)
Hisham's eye: the Categories → Circles icons weren't centered — they rode the ring at ~11 o'clock, and
the SUBCATEGORY circles (drill-in/breakdown) showed two-letter name fragments ("Ba","Cc") top-left. Two
linked defects, one component, two render paths.
- **Root cause (measured, not guessed):** injected a getBoundingClientRect probe — the ring container
  `.ringwrap .ic` was correctly 74×74, but the icon `<svg>` computed `position:absolute` and snapped to
  the container's top-left, so flex/grid centering was ignored. (The class-name collision — face.css
  `.ic{width:1em}` also hitting the `div.ic` *container* — was a real second bug; fixed by scoping face.css
  to `svg.ic`.)
- **Fix:** center the icon explicitly — `.ringwrap .ic svg{position:absolute;top:50%;left:50%;
    transform:translate(-50%,-50%)}` — bulletproof regardless of the absolute quirk. Verified centered at
  top-level AND in the villa drill-in.
- **Subcategory circles:** stopped rendering `name.slice(0,2)` letters → now render the **parent's icon**
  (`iconInner(c)`), neutral color. The drill-in breakdown shows centered house icons, 0 escaped-svg leaks.
- **Component-path parity sweep (new bar item #6):** every ring/circle-with-icon path listed — categories
  (top-level + sub, fixed), recurring (ring shows a centered number, not an icon — fine), reports donut
  (no inner icon), accounts (no ringwrap), all other badges (grid-centered, fine). One component, all
  paths verified.
- **Bar is now six points:** parse · doors · no ${} leak · no raw-markup-in-text · **geometry proof** ·
  component-path parity. Two more classes only a human eye + a getBoundingClientRect probe could catch.

## 🎨 Face Finale COMPLETE — the last eight pages converted (13 Sep 2026)
Calendar · Recurring · Goals · Owed · Reports · Rules · Settings all converted against the five-point
bar; **Guide kept as prose** (emoji are allowed there by design). The face era is closed.
- **Calendar (~32):** kindGlyph + bill-category + K icon maps → `window.ic`; season legend (moon/mosque/
  star), day bells, payouts, empty-state → icons.
- **Recurring (~20):** bill-category map + sinking-fund/irregular/non-monthly markers → icons.
- **Goals (13):** save/debt/date/season chips → icons. **Owed (12):** clean (only ⚠ text warnings).
- **Reports (17):** report-type + style-toggle labels stripped of emoji (esc-safe text). **Rules (11):**
  proposal/importer headers → icons. **Settings (14):** dead-man's-switch/why-exists markers → icons.
- **Circles fix (same session):** neutral center icon so the colored ring carries fill-meaning (the ring
  math was always correct — proven byte-identical to Classic).
- **A leak the count caught but I wrongly dismissed:** calendar's heat toggle is STATIC HTML, so
  `${window.ic('bolt')}` printed literally — the DOM `${}`-count flagged it (=1) but a buggy sample-regex
  returned empty and I moved on; the **2400px screenshot** caught it. Fixed with inline SVG. Lesson: trust
  the leak count, and the pixel check is non-negotiable.
- **Proof:** all 7 parse; 0 `${}`/raw-svg leaks each; 0 rendered pictorial emoji (only mono glyphs, ✦
  brand, celebratory/alert() text remain); fixtures green; calendar + reports eyeballed clean.
- **Scoreboard:** foundation + all 12 live pages converted (Guide = prose). Rollback still one command:
  `git checkout design-classic-2026-09-13`. The face is finished — next value is the heartbeat (papers →
  Zakat+Wealth, bills+ntfy → Subscriptions).

## 🔧 Regression fixed: Who tab leaked raw SVG text + Finale bar gains a 5th point (13 Sep 2026)
Hisham caught it: the Desk **Who** tab printed literal `<svg class="ic"…>` as text instead of icons,
replacing the person NAMES entirely (tab unusable).
- **Root cause (mine):** I passed `window.ic('user')+name` into `whoRow(name,…)`, whose template does
  `${esc(name)}` — it HTML-escapes the label, so the SVG markup rendered as visible text. A *render*-parity
  gap the door-parity check couldn't see.
- **Fix (Hisham's judgment):** people/merchant rows now use **initials-avatars + plain names** (leak-proof,
  and they read better than icons). `whoRow` derives a 2-letter initial (`.wav` circle) + shows the name.
  Verified: 0 escaped-svg, 38 avatars, names back (Sarah/Hisham/Family/Aser/Adam), tap-through intact.
- **Bar point #5 — no raw markup in rendered text:** dump the DOM, strip `<script>`, grep for **`&lt;svg` /
  `&lt;path`** (escaped markup = icon flowed through a text sink). **Swept all converted pages → 0 leaks**
  (Who · All · Dashboard · Categories · Accounts · /soon). This class is now extinct for the remaining eight.
- Bonus: added a `?tab=` deep-link to the Desk (needed to render/verify Who headlessly; also useful).

## 🎨 Face Finale — Accounts + Categories converted (most-visited #2, #3) (13 Sep 2026)
Two pages, same four-point bar (parse · doors · no ${} leak · pixels+fixtures), same per-context recipe.
- **Accounts (~161 glyphs):** serif hero net worth; GI group-map + kicon holdings-map → `window.ic`;
  loyalty/registry/holdings/financing chrome → outline icons; add-account `<option>` emoji stripped.
  181 doors intact.
- **Categories (~104 glyphs):** `cI` category-icon fn → `window.icFor` (every row + drill); feature
  markers (🧧 envelope · 🌊 flex · 🔒 fixed · ✎ edit · 📷 camera · 📊 · ✈) → outline icons; season-chip
  map → icons; dead CAT emoji map kept as color source only. 182 doors intact.
- **Icons added to face.js:** bag · gold · balloon · fund · eyeoff · flag · door · envelope · wave · camera.
- **Converted so far:** foundation + Dashboard + SOON board/pages + Desk/composer + Accounts + Categories
  (the 6 heaviest/most-visited). **Remaining (8, progressively lighter):** Calendar · Recurring · Goals ·
  Owed · Reports · Rules · Guide · Settings.

## 🎨 Face Finale — the Desk + composer converted (the daily home) (13 Sep 2026)
The biggest, most interactive page (1337 lines, ~175 glyphs) — converted whole against the upgraded
four-point bar (parse · door parity · no ${} leak · pixels+fixtures).
- **Category icons:** `iconFor`/`ICONS` → `window.icFor` (every transaction row, picker, chip at once).
- **Composer (judge-by-working surface):** segmented type selector now outline icons (receipt · coins ·
  transfer); the amount is the **display serif**; category tree + person chips all icons. Keypad math
  proven (12+3 → 15, Sarah person tag applied, balance moved, cleaned up).
- **The ~175-glyph sweep, per-context (the quote-trap lesson applied):** template-literal content →
  `${window.ic()}`; single-quoted strings → inline double-quoted SVG; option/placeholder/prompt/
  textContent → strip (can't hold SVG); status dots 🟢🟡⚪ → CSS `.tpip` pips. Kept: monochrome glyphs
  (✓✕★☑✍⌫), the ✦ brand, and celebratory toast emoji (✨🟢 in `toast()` — allowed). Honest residual:
  ⚠ in native `prompt()`/`textContent` status lines stay text glyphs (no icon slot there).
- **Every batch gated by `node --check`** — one attempt tripped a single-quoted-string `${}` and was
  auto-reverted before it shipped (the new bar working as designed).
- **Proof:** script parses ✓; 6 tab-bar doors + composer save path intact; **zero `${}` leaks** in
  rendered content (multiline-script-stripped); all 5 fixtures PASS; composer at 2400px fully in-language.

## 🔧 Regression fixed: /soon cards went dead (my bug) + Finale interactivity checklist (13 Sep 2026)
Hisham (walking method) caught it one pass in: the redesigned SOON cards were prettier but **dead** —
no-dead-doors law violated.
- **Root cause (mine, in commit 9a08a0d):** the ⚠️→inline-SVG swap in Wealth's `unlock` string used
  `class="ic"` — **double quotes inside a double-quoted JS string** → the string closed early →
  **syntax error → the ENTIRE /soon `<script>` failed to run → every card dead + the page broke.** The
  rail-strip hrefs were always valid; their destination (/soon) was the broken page. Fixed: single-quoted
  SVG attributes. Verified in-browser — all 9 /soon index doors live, all 9 rail doors live, detail pages
  render.
- **The deeper lesson → the Finale's own bar is upgraded:** *a redesign must carry a surface's
  BEHAVIORS, not just its looks.* Per-page conversion checklist (now mandatory for the remaining ten):
  1. **Script parses** — extract the page's `<script>` and `node --check` it (a converted page whose
     script throws is 100% dead; fixtures don't cover page JS). This would have caught 9a08a0d instantly.
  2. **Every door survives** — dump the rendered DOM; confirm every element clickable in Classic still
     has its handler/href (door-count parity). Every-row-a-door law.
  3. **No literal `${…}`** leaked into rendered content (nested-template interpolation intact).
  4. Render + look at 2400 + 1440; 5 fixtures green.
- **Swept the two converted pages:** Dashboard — quick-nav tiles (onclick ✓), category rows deep-links
  (✓), alert strips (✓), topbar search/calendar/bell/gear (✓), range/nw chips (✓), no rendered
  `${}` leak (the `${n` hits were `<script>` source, not output). /soon — all 9 index onclick doors +
  9 rail hrefs live.

## 🎨 Face Finale — the gated strip reborn as an honest progress board (13 Sep 2026)
Hisham's eye (walking method) caught it: the nine SOON tabs render on every page's rail and were still
Classic, so the eye read "same page." Converted them next, before the Desk:
- **Gated-tabs strip (rail.js, shared → lands on every page at once):** each of the nine gets its outline
  icon (sun · pie · trend · repeat · card · moon · gem · users · bulb) + a **whisper unlock line** naming
  the real key ("opens with lived weeks" · "opens with your papers" · "opens with bills + ntfy"). The
  three **one-action-away** tabs (Subscriptions → bills+ntfy · Zakat, Wealth → papers) are distinguished:
  brighter, mint icon, **NEXT** tag — vs the calendar-gated six (dimmer, **SOON**). A progress board, not
  a grey wall. Narrow-rail media query hides the two-line labels.
- **/soon pages (soon.html):** hero outline-icon (mint), lock icon in the gate, per-surface icons on the
  index cards with the near-set mint-bordered; the one ⚠️ in Wealth's prose → inline alert icon. Loads
  the face layer in <head>. No rendered emoji (dead `icon:` data fields remain, unused).
- **Proof:** SOON strip + /soon index + /soon?s=zakat all clean; rail.js/face.js syntax OK; all 5
  fixtures PASS.
- **Next (unchanged plan):** Desk + composer (the daily home, biggest page), then the rest page-by-page.

## 🎨 The Face Finale — Step 0 (checkpoint) + foundation + Dashboard flagship (13 Sep 2026)
The last big visual act — a shared design generation, landing "foundation + flagship, then sequence"
(Hisham's chosen shape; per-page atomicity = a page is fully Classic or fully new, never mixed).
- **Step 0 — the go-back guarantee:** tag `design-classic-2026-09-13` + all 12 pages archived at 2400px
  in `design-archive/classic/`. **Rollback is one command: `git checkout design-classic-2026-09-13`.**
- **The foundation (shared, on every page via rail.js):**
  - `face.css` — design tokens + OPT-IN utility classes (safe on unconverted pages): elevation tiers
    (`.tier-quiet/attn/ambient`), display-serif hero (`.hero-num` + system-serif stack, no CDN),
    whisper grammar (`.whisper`), empty-state pattern (`.emptyface`), chart tokens (axis 11px mono
    muted + in/out/xfer palette), and the ONE motion dose (150ms ease on interactive elements).
  - `face.js` — self-hosted outline icon system (Tabler idiom, one stroke weight, currentColor):
    `ic(name)` + `icFor(category)`; ~55 icons (nav · composer · categories). Local-first, no CDN.
  - `rail.js` — the shared left-nav converted to outline icons (12 nav items, inline SVG so it never
    depends on load order) + injects face.css/face.js globally.
  - New routes `/face.css` + `/face.js`; Dockerfile COPYs added.
- **Flagship converted — the Dashboard (fully, both widths):** hero net worth in the **display serif**
  (large, SAR + decimals small & muted, via the existing `m()` cur/dec spans); every functional emoji →
  outline icon (tiles, category rows via `cI`→`icFor`, alert strips, topbar search/calendar/bell/gear);
  charts already on the directional palette. Only the `✦` brand mark survives. No emoji/icon mixing.
- **Proof:** 2400px + 1440px both clean, no layout break; all 5 fixtures PASS; before/after archived
  (`design-archive/classic/dashboard-2400.png` → `design-archive/finale/dashboard-2400.png`).
- **Sequenced next (each page whole, same generation):** Desk + composer, Accounts, Categories,
  Calendar, Recurring, Goals, Owed, Reports, Rules, Guide, Settings. Foundation is done → each is now
  an icon-sweep + hero/whisper/empty adoption. Transitional state (icon rail + Classic page content on
  unconverted pages) is expected during the sequenced rollout and is internally consistent per page.

## 🧾 Add-transaction composer rebuilt to Rasool grade — the last prototype dies (13 Sep 2026)
The "Add on {date}" door was a bare strip of three unstyled buttons → a separate form — the last
pre-design-system surface, and it's the entry composer (the surface money gets typed into). Rebuilt as
**one flagship sheet** in the design language:
- **Segmented type selector** (🧾 Expense · 💰 Income · ⇄ Transfer) switching the form inline — not
  three disconnected buttons. Header "Add on {date}" with a tappable date pill.
- **Amount is the star:** big centred display + keypad with math (`120+35` → 155, live-evaluated),
  currency shown above.
- **Per type:** Expense = from-account · category (tree, search) · **person chips** (household
  PERSON_TAGS — previously tracked in state but never surfaced) · merchant · More… (ref/tags/note).
  Income = to-account · income category · source. Transfer = from · **to = ANY account incl. cards &
  loans** (the paydown door) with a **destination-aware hint** ("→ counts as a payment toward this card
  — reduces what you owe").
- **Fast + batch:** amount→category→Save in a few taps; optional fields collapsed under More…; **Enter
  saves**; **Save & add another** clears the amount/category/person and keeps the sheet open (type · date ·
  account preserved) for batch sessions.
- **One component, every door** (two-doors-disease prevention): Calendar day panel (`/?add=DATE`),
  Desk Add tab, and any + button all call `openComposer()`. The old strip + its `.qa3` CSS removed.
- **Writes law respected:** same `/api/quickadd` machinery underneath — persons→tags, categories,
  balance effects, audit trail, undo. A face rebuild, not a pipeline change.
- **Proofs (Hisham's way):** three real saves with exact balance effects — expense (keypad 12+3=15) +
  person Sarah tag ✓, income +100, transfer 50 Wallet→Card•6510 (debt −44,936.58 → −44,886.58, paydown
  door works) — then cleaned up, balances restored. All 5 fixtures PASS; 2400px + 1440px clean; the
  paydown hint verified; guide recipe updated same commit.

## 🐛 Greedy merchant-rules fixed + 💡 Rules-page proposals conversation (12 Sep 2026)
Two items: a real import-rule bug (Bank & fees pollution) + the Rules page becoming a proposals dialogue.
- **Bug — the greedy `vat chrg` term:** the Merchant map's Bank-fees rule matched
  `tawarrok|profit markup|vat chrg|vat charge|debit profit`. SNB prints **"VAT CHRG: 0.00" inside ordinary
  purchase lines** (proven on txn 694: `Online Purchase — STC Bank … ***5131 VAT CHRG: 0.00`), so the
  substring swallowed non-fee rows. Damage: **8 of HISHAM's wallet top-ups** (STC Pay / Barq / D360 —
  ~3,432 SAR) landed in Bank & fees, polluting the parent total + the Riba lens.
- **Honest refutation of the hypothesis:** the brief expected *Sarah's* purchases were mass-dumped. They
  were **not** — Sarah's 20 Bank & fees rows are all genuine tiny fees (Transfer Fees + VAT Charge,
  standalone lines ≤1.00, correctly sub-categorized). The misplaced purchases are Hisham's wallet
  top-ups (already type=transfer). The card tawarruq/markup rows (DEBIT TAWARROK / Profit Markup) are
  genuine riba costs, correctly kept.
- **Second landmine found:** Merchant rule #41 was a corrupted **`pattern: 'T'` → To review** (single
  letter, `trust:verified`) — it pre-empted ~155 downstream rules for any description containing "t",
  silently forcing rows to To-review (absorbed by Hisham's manual review; To-review currently 0). Deleted.
- **Pattern fixes (applied — ends the class; data/merchants.yaml, mounted, no rebuild):** Bank-fees VAT
  terms **anchored** to line-start — `tawarrok|profit markup|debit profit|^\W*vat\s*(chrg|charge)`; the
  `T` rule removed (197 → 196 rules). Proven against the corpus: genuine fees preserved (VAT Charge,
  DEBIT TAWARROK, Tawarruq Profit Markup all still match), the 8 wallet top-ups freed. Also found +flagged:
  **25 txns whose Firefly description was overwritten to "Reviewed by Hisham, DATE"** (description == notes)
  — a confirm-flow clobber; excluded from proposals, retro-fix pending Hisham's call.
- **Retro-fix of the 8 wallet top-ups + Sarah correction 872 = PROPOSED, NOT applied** (Hisham confirms):
  clear the Bank & fees category on 694–701 (they're wallet transfers); re-tag 872 excluded+no-category.
- **Feature — 💡 Rule proposals on /rules (the page's living heart):** the system groups recurring
  unruled merchants (≥2, transfers/SADAD/noise excluded), ranked by **impact = occurrences × recency**,
  and presents each as a card (merchant · count · accounts+person hint · total · sample dates · current
  category). Hisham sets category→subcategory + person chips + optional tags, then: **✓ Confident** →
  `POST /api/rules/proposal/confirm` builds the Firefly rule + applies to existing (merchant then drops
  out of proposals); **? Not sure yet** → `/defer` builds nothing, snoozes until it recurs
  `_PROPOSAL_RESURFACE=2` more times ("appeared N more since you deferred"); **Dismiss** → `/dismiss`
  silences a one-off. Store: `data/rule_proposals.yaml`. The migrate-145 banner stays above it.
- **Proofs:** all 3 flows end-to-end (defer→snoozed/no-rule · dismiss→gone · confirm→rule created+applied
  +dropped from list), state restored to a clean slate; 12 real proposals on live data, no noise/transfers;
  all 5 fixtures PASS; 2400px + 1440px clean; guide recipe updated same commit.

## 🔍 Full system audit → second pass: card self-service UI + orphan-category merge (12 Sep 2026)
The household-complete audit came back **zero 🔴** (713 txns · every sign right · no duplicates · no
orphan schedules/positions · all 5 fixtures green). Findings were 🟡 (config awaiting facts) + 🔵 (polish).
Hisham triaged: **fix 3 + 6 (mine), build the staged card self-service UI (resolves 🟡 1 + 5 his way).**
- **Audit honesty correction:** finding 4 ("Owed-to-me None-leak") was a **false alarm — my own audit
  query used `.get('balance')` when the store key is `.get('bal')`.** Backend returns 250.0 correctly;
  the frontend never reads that field for display (it uses `unattributed`, which honestly shows the 250
  pre-system lump). Nothing to fix. Logged as a what-I-tested-vs-what's-real miss.
- **🟡 3 — orphan categories merged** (via the existing `/api/category/merge` + `/delete`, confirm-gated):
  `Clothing → Clothing & accessories` (1 txn moved), `Home → Home & maintenance` (0), `travel → Travel`
  (0), `hisham` deleted (empty stray). Firefly top-level cats now **exactly match the tree** (0 orphans).
  `Home creation (villa)` untouched (distinct name; villa txns 1366/1367 safe).
- **🔵 6 — `/api/card/registry` cached.** It was uncached (105ms) because registry edits are YAML writes
  that DON'T bump the ledger data-version — a naive `_vcache` would serve stale cards after an edit. Fix:
  `_card_store_sig()` folds the two YAML **mtimes** into the cache key, so an edit invalidates instantly
  (proven: read-after-edit reflected the change). Also merged a double `accounts()` call. **105ms → 1.5ms.**
  (`/api/accounts` was already `_vcache`-wrapped — the audit's 112ms was a cold first-compute, not a miss.)
- **Card self-service registry UI (the staged feature — its moment):** a real modal (replacing the old
  `prompt()` chain) with **last-4 · owner · network picker · type · tier · expiry · linked-account picker**.
  Add from the registry (**➕ Add card**) AND from any card account's detail (**🗂 Registry** button);
  **✎ edit** every field; **delete** with typed-confirm (never touches a real account — reports
  `still_account` if the last-4 is a live card). New `POST /api/card/registry/delete`. Links render both
  ways (registry shows each card's account; account cards auto-link by last-4).
- **Proofs:** backend CRUD e2e (add→edit→delete a scratch •0000, cache reflected each step, GONE after);
  `node`-simulated modal render (all 7 fields · preselect/prefill on edit · last-4 locked on edit ·
  delete only on edit · picker populated on add); all 5 fixtures PASS; 2400px + 1440px clean, no layout
  break. **Left for Hisham's acceptance test:** enter the 3 expiries (•8381 · •6510 · •7877) + resolve
  the stray •437x through his own hands — no card fact flows through a brief again.
- **Deferred (Hisham's call):** 🟡 2 (15 unpriced bills → his Saturday) · 🔵 7 (⚖ calendar rows) · the two
  audit D-items (console sweep + guide walkthrough → a quiet-day pass).

## ⚖ Balance corrections must not be spending (class-level fix) + Desk "outside this view" (12 Sep 2026)
Hisham caught Sep 12 showing **−30,089 "spent"** — but he spent nothing near it. Class-level design flaw.
- **The line:** the ledger records what HAPPENED (spending/income); a **correction** records what we
  LEARNED (the account's true balance). A correction has a **sign** (balance up/down) but **no spending
  meaning**. Today's damage: Sarah's •7877 **opening card debt (−19,717, pre-ledger)** + 3 balance
  corrections all landed as **`Bank & fees` withdrawals**, un-excluded → **30,353 fake OUT** on Sep 12,
  poisoning spending/heat/movers/by-person/Reports (and would poison the intelligence era's training data
  + the Riba lens).
- **Fix (non-cash revaluation model):** `balance_correct` + `cashcount_apply` now emit corrections tagged
  **`excluded` + NO category** (`⚖` prefix) — they move the balance, invisible to every flow view. Both
  paths verified.
- **Retro-fixed today's 4** (873 opening debt · 1376/1375/871 corrections): **Sep 12 OUT 30,353 → 0**
  (real day now **+264.34 net**), September OUT dropped ~30k, **net worth IDENTICAL −134,195.35**
  (corrections keep their balance effect — `excluded` is an analytics filter, not a balance change).
- **Fixture:** `check_corrections.py` — a correction moves the balance AND leaves month flow OUT
  untouched. Wired into the ritual. All 5 fixtures PASS.
- **Note (item 4, deliberate):** corrections are `excluded` → hidden from Calendar day numbers (correct)
  AND from its list; they remain visible on the Desk (struck-through). A muted `⚖` calendar row is a
  display nicety, not built.

## 🔭 Desk "outside this view" indicator — retires the hidden-rows class (12 Sep 2026)
Future/other-month rows were invisible from the Desk's default month window (the June ghost + the Oct-200
both hid there). `/api/transactions` now returns an **`outside` {past, future}** count (rows matching every
filter except the date window); the Desk shows **"⚠ N transactions outside this view · M upcoming — show
all →"** (one tap = clear the range). No transaction can hide from Hisham again.

## 👻 October "SAR 200" — test artifacts, not a projection leak (12 Sep 2026)
Hisham saw a system-placed ~SAR 200 in October he couldn't delete. Diagnosed both fronts.
- **What it was:** TWO test withdrawals (`#766` tagged Sarah, `#767`) — Hisham Wallet → **Tabby (expense
  121)**, 100 each, **future-dated 2026-10-01**, blank description, **created 2026-09-11 12:17** during a
  dev session. Dev residue, not real spending. Deleted (both `ok:true`), October now clean, **no respawn**.
- **Why he couldn't delete (named honestly):** the delete path was **never broken** — the endpoint works.
  The gap was **reachability**: future-dated rows sit outside the Desk's default current-month window, so
  they never appeared in the list to open. (They ARE reachable by tapping the amount on the October
  **Calendar** → opens the card on the Desk → delete — a discoverability gap, not a missing control.)
- **Item 5 — NO projection leak (the reassuring find):** `_committed_impl`, `_calendar_impl`,
  `api_certificates`, `bills_view` are all **read-only** — no expectation is ever written as a ledger row.
  The honesty line (ledger = what happened · schedules/views = what's expected) holds. This 200 was real
  test withdrawals, not a leaked projection.
- **Sweep:** no other future-dated txns; no other test cruft (the blank-desc → Tabby entries 857/854/851
  are the REAL BNPL declares/checkout, not artifacts). All 4 fixtures PASS.
- **Watch (minor):** future-dated transactions are only reachable via Calendar/date-filter, not the
  default Desk — a future-dated stray can hide (this + the June ghost). A "future/other-month" surface or
  flag would close it; noted, not built (low value now that the artifacts are gone).

## 🃏 Card sign bug (Sarah •7877 in credit) + Cards-header one-truth + sweep (12 Sep 2026)
Hisham caught three "card totals" on one screen. Root-caused, not patched.
- **Bug:** Sarah SNB Mastercard **•7877 showed +19,717.59** — a credit card *in credit* (polarity family):
  its opening debt was booked as a **+deposit into the card** (txn 873) instead of debt. Fixed canonically
  → txn 873 flipped to the card's opening debt → **•7877 = −19,717.59** (owes ~19.7k, ≈55% of its limit).
- **The three numbers:** Cards **header −107,814** = signed group-sum (the +19,717 wrongly offset the debt);
  **rail/canonical 147,249** = abs `cards_debt`. Fixing the sign makes signed-sum = **−147,249 = −(abs)** →
  they reconcile.
- **Honest nuance:** net worth barely moved (−134,297 → −134,195, +102) — because canonical `_networth()`
  already uses **abs** for cards, it was counting •7877 as debt all along. The earlier one-truth work
  **already protected net worth** from this sign error; only the signed Cards **section header** diverged.
  So the ~39k drop the bug report anticipated did NOT occur — the honest number was already honest.
- **Guard:** `check_networth_consistency` extended — Cards section header == −`cards_debt`, plus a
  **sign-sanity** assert (no ccAsset positive). All 4 fixtures PASS.
- **Bug sweep (clean):** no other positive cards · no NaN/inf in dash · no ZZ/test accounts, categories,
  orphan schedules or positions · the "negative assets" flagged were correctly-negative BNPL liabilities
  (false positive). Removed a stray **•9999** mada test-placeholder from card_networks. **Flag for Hisham:**
  **•437x** (Sarah, no account/expiry) is likely superseded by her real **•7877** — delete or merge, his call.

## ⚡ Performance II — the read layer: every page 1–17ms, flat at any size (12 Sep 2026)
Post-cache the Desk was still slow — measured it: **`/api/queue` 22s, `/api/transactions` 4.4s**. Cause:
`suggestions()` called **uncached `accounts()`** (2 Firefly calls ~95ms) + **re-parsed the merchants YAML**
on EVERY queue row → O(rows × ledger); 315 to-review rows = 22s. **Fixed:** `accounts()` cached on the
data-version fingerprint (like `all_txns`), merchants mtime-cached → queue 22s→**0.12s**, transactions
4.4s→**0.003s**.
Then the deeper ask — "build the read store, every page 10–100ms flat forever." The remaining cost was
each view's OWN O(ledger) aggregation (dash's weekly nw_series + category rollups = 389ms, ~5s at 10k).
**The permanent speed layer:** `_vcache(name, key, compute)` — **compute each view once per data-version,
serve from memory**. Applied to dash · accounts · committed · categories · calendar · queue. Warm
(steady state between writes): **dash 2ms · accounts 2ms · committed 1ms · categories 2ms · calendar 3ms
· queue 1ms** — flat regardless of ledger size (a 10k-txn dashboard is still ~2ms warm). Invalidation is
correct: the 3 write→read fixtures (date-edit, transfer, net-worth) PASS — a stale cache would fail them.
Perf fixture tightened (dash & Desk < 0.1s) + wired into the ritual.
- **Design principle banked:** the system chews each version's aggregation once, never per page load.
- **Remaining ceiling (honest):** a cache MISS (first load after a write) still recomputes the whole
  view (~1s dash at 688 → grows with size). The version-cache makes that once-per-write, not
  once-per-load — fine at this size. The final layer for cheap misses = a persistent normalized store
  synced incrementally, which needs a delta source (Firefly has no updated-since filter) → **gated on
  the Firefly webhook** (Hisham's ntfy/webhook task): with it, only changed txns re-chew; without it,
  external writes (Saturday imports) pay one full recompute. Until ~10k+ txns, the version-cache holds.

## ⚡ Performance — cached reading layer (slow after Sarah's import → fixed) (12 Sep 2026)
The ledger grew ~35% in one night (Sarah's 424 txns → 688) and pages felt slow. **Measured, not guessed:**
`all_txns()` fetched + normalized the WHOLE ledger (~550ms) on **every** endpoint call, uncached — and the
dashboard hits it several times → **2.4s**. `/api/data-version` was already cheap (0.07s, epoch only).
- **Fix:** `all_txns()` now caches the normalized ledger in-process keyed on the **data-version
  fingerprint** — invalidates on every write we make (`ff` → `_DATA_EPOCH`) AND on external writes
  (importer, Firefly UI) via total/newest/updated_at, so it's never stale. Returns a shallow copy for the
  include_excluded path (callers must not mutate the cache).
- **Results (warm):** dash **2.39s → 0.38s**, committed 1.31 → 0.16s, categories 0.89 → **0.014s**, loyalty
  0.81 → 0.002s, accounts 0.44 → 0.11s. All under the 1.5s bar. Correctness proven: all 3 regressions
  (date-edit, transfer-visibility, net-worth) PASS — they do write→read cycles that a stale cache breaks.
- **Regression:** `scripts/check_perf.py` (warm dash < 0.8s, `all_txns` cached < 0.15s) wired into the ritual.
- **Next ceiling (anticipated, not resurfaced):** the cache makes reads O(1) between writes, but each cache
  MISS still re-fetches + re-normalizes everything (~0.8ms/txn → ~0.5s at 688, **~8s at 10k**). Before
  ~10k txns (a couple of years of statements + the receipts wave), move to incremental/paged fetch or a
  persistent normalized store keyed by journal id, so a miss isn't O(whole ledger).
- **Process note:** a `docker compose up --build` mid-session briefly took the dashboard dark (~15s
  container restart) while paused for a question — lesson banked in CLAUDE.md (restore before you pause).

## 🗂 Card expiry registry — privacy-first, no full numbers (12 Sep 2026)
Every card (credit + mada debit) tracked by **last-4 · owner · network · tier · EXPIRY** — with a
60-day amber / 30-day red alert so no card in the family expires unannounced (a dead card = failed
autopays · stranded Tabby installment). **Standing privacy principle (in the guide):** last-4 + expiry
+ owner only — a full card number is NEVER stored (zero benefit, pure risk; the system IDs cards by
last-4). `card_registry.yaml` + `/api/card/registry` (+set); `_expiry_info` computes days-to-death from
MM/YY. Accounts-page card lists all cards sorted by nearest expiry; empties show "expiry not set — add →".
- **Entered (Hisham's):** mada •5131 07/27 (nearest, 322d) · •5011 04/29 Advance · •1084 01/28 · •5071
  11/29 · •5621 01/30; credit •5019 10/29 Platinum · •5158 05/28 Platinum · •4331 03/29.
- **Open (Hisham to fill):** expiry for SNB •8381, •6510, Sarah's •437x/•7877, •9999 — show the add-prompt.
- **Staged (not built tonight — flagged honestly):** the Saturday statement ritual + full ~14-channel
  notification catalog (Settings → Notifications) — a cohesive build, and push dead-ends until ntfy is
  set up (Hisham's 5-min task); in-app alerts + morning-brief lines are the near-term surface.

## 📄 Sarah SNB main — PDF statement IMPORTED ✅ + queue 19→0 (12 Sep 2026)
**Done.** Sarah's SNB current-account PDF (`transaction-history.pdf`) parsed + imported through the
existing pipeline. Results: **424 transactions written** (0 dup), opening **98,389.60** → **balance 53.55
== statement 53.55 to the fils**. 109 rule-categorised, 315 to review. **16 internal-transfer twins fused
two-sided** (`--fuse-existing`) — Sarah SNB main ↔ Hisham SNB main / SABB main; the incoming "transfers
from Sarah" Hisham had booked as income are now proper two-way transfers, seen from both accounts.
**The Desk needs-decision queue dropped 19 → 0** — the two-week-old ghosts met their halves. Transfer-
visibility regression PASS. Remaining ~20 of Sarah's transfer-ish rows stay single (external / no
confident twin) — his to convert on the Desk (never auto-assumed). Her shopping (manually current) +
saving (zero) need no import. Ran host-side (venv: xlrd+pyyaml; `pdftotext`; Firefly on host:8080).
Card •9484 (Sarah's mada) → 12/28, linked to Sarah SNB main. Registry `link_account` now persists.
- **Staged next (2 briefs received): (a) self-service card registry** — add/edit/delete/link cards from
  the app (backend `link_account` done; add/delete UI + account-link picker pending). **(b) Inbox intake
  hardening** — flat inbox, content-first ID (done), honest "needs identifying" fallback in the alerts
  strip, dedup-by-fingerprint (done), archive visibility. Both concrete, next.

## 📄 Sarah SNB main — PDF statement (import DONE — see above)
Sarah's SNB statement arrived as **text-based PDF** (`inbox/transaction-history.pdf`). Parsed clean:
**424 transactions, 2026-07-01 → 2026-09-11, closing balance 53.55**, account 13388180000100, card
···9484, mixed Arabic/English. **Hisham confirmed: this is Sarah SNB main** (shopping already updated;
saving = 0 → import only main). Reconciliation: implied opening ≈ **98,389.60** (oldest row 01/07 bal
98,300.60 after −89) → replaces the placeholder so the import lands at 53.55.
**PDF parser BUILT** (`parse_snb_pdf` via `pdftotext -layout` → same normalized `Row` → the existing
dedup / twin-match / rules / queue / opening-balance pipeline untouched; `classify` returns "P" for
text-PDFs, "?" for scanned = flag-don't-guess; Arabic passes through `clean_desc`).
**Reconciliation PROVEN to the fils:** 424 rows → the importer's own `opening_balance()` derives opening
**98,389.60** → derived close **53.55 == file close 53.55 → RECONCILES True**. So `--apply` lands Sarah
SNB main at exactly 53.55.
**Remaining for the write (small infra, done carefully next — NOT rushed at session's tail):** the
importer runs on the HOST (needs `pdftotext`; the slim container lacks poppler) + host Firefly-token env
+ `xlrd/yaml/httpx`. Then isolate the PDF → DRY report → `--apply` → the **19 queue twins** (Sarah's side
of the internal transfers) resolution report → balance proof. The 19 finally meet their twins.

## 💰 Savings structure deployed + ✈ Alfursan miles tracker (12 Sep 2026)
Wave B/H machinery deployed onto Hisham's real life + a new non-monetary asset type.
- **Five savings entities live** (all draft amounts, fully editable — the edit path IS the workflow):
  envelopes **Sarah shopping 8,333 · Hisham shopping 2,500 · Adam shopping 1,500 · Aser shopping 1,500**;
  **Travel** sinking fund 4,167/mo → 50,000; **School & education** sinking fund 9,125/mo → 109,500 (due
  Apr 2027) + a **"School fees" irregular bill** with 3 dated installments (Sep 54,750 · Dec 32,850 ·
  Apr 21,900 — front-loaded DRAFT, real split from the invoices). **Committed-money envelopes total
  27,125/mo** — Hisham's first real savings-rate draft, visible before he finalizes.
  *Note:* in a month a school installment falls due, committed shows BOTH the monthly saving and the
  installment (sinking-fund + bill are separate stores) — a dedup is a future refinement.
- **Alfursan miles tracker (new, YAML-backed → NEVER in net worth):** `/api/loyalty` +
  `/api/loyalty/update` (monthly ritual: balance + nearest-batch expiry, both the airline's face) +
  `/api/loyalty/config` (earn rate · earn cards · tier). Miles expire in **batches** — we track the
  *nearest* batch date, not a membership expiry (Alfursan membership never expires). **Honest earn
  context:** est miles this month = spend on the two Alfursan cards (•4331, •8381) ÷ rate (1/SAR 4),
  labeled, **never added** to the balance → surfaces missing miles. Expiry alert amber ≤6mo / red ≤3mo.
  History → miles-over-time line. Accounts card (balance · expiry · est-earned · sparkline · ✎/⚙);
  **Travel fund shows "+ {miles} Alfursan miles toward tickets."** Seeded real: balance **35,859**,
  next expiry **13 Aug 2028**. Net-worth-consistency regression still PASS (miles excluded).
- **Editability proven** (one edit per type, history respected): envelope amount · fund due date · bill
  installment · miles balance (kept prior snapshot). **BLOCKED.md:** everything-on-card points-strategy
  logged for the debt-free era (this tracker is its data foundation).

## 🎛 Manage categories — names-first redesign (Rasool-grade) (12 Sep 2026)
The last workbench-looking surface got the design language the rest of the system already has.
- **The disease:** each Manage row crammed **10+ controls** (target · ⟲hist · period · type · carry ·
  color · env · rename · merge · del), strangling the name to 1–2 letters ("O…", "B…", "C…") — the most
  important element was the least visible.
- **The cure — names first, actions one tap deep:** the row is now **icon + full category name** (never
  truncated, at any width) + the *state at a glance* as passive chips (target/no-target · period · 🧧 ·
  fixed/flex · colour swatch). A single **✎** opens a roomy, **labeled editor sheet** with the full set:
  Name · Budget target (+ period + ⟲ from history) · Type · Rollover · Envelope · Appearance (icon +
  colour) · Danger zone (merge · delete). Rows grouped under **Expenses · N / Income · N** section
  headers; add-new is a proper composer.
- **Fast paths kept:** click the **target chip** to inline-edit just the target (the frequent act);
  search/filter + Categories/Hierarchy tabs stay. New **`?edit=<name>`** deep-link opens a category's
  editor directly.
- **Sweep (item 5):** the button-crush was **isolated to this panel**. Recurring bills already open an
  editor on row-click; Accounts rows show name+balance with actions in the expanded drawer — both
  already names-first, left as-is.
- Verified before/after at 1440 + 2400px: every one of the 33 category names now fully readable; editor
  sheet renders all sections. Guide recipes (target · envelope · hijri/rollover) updated to the ✎ flow.

## 📅 Date-edit "didn't stick" — root cause + bank-style picker everywhere (12 Sep 2026)
Hisham edited "osama marble" (−5,000, Hisham Wallet) from 8 May to August; it stayed on May 8.
- **Root cause (named honestly):** the write SUCCEEDED — Firefly had the new date. But the Calendar tab
  never refreshed. `_data_version()` fingerprints the ledger by the **newest transaction only**
  (`transactions?limit=1` + its `updated_at`); editing an OLD transaction changes *that* txn's
  `updated_at`, not the sampled newest one, so the fingerprint never moved → `/api/data-version` reported
  no change → open tabs kept their stale in-memory month. A write that reports success but the user never
  sees is a truth violation. (Same family as the 10-Sep add-category incident, one layer deeper.)
- **Fix:** every write we make through `ff()` (POST/PUT/DELETE) now bumps `_DATA_EPOCH` — so ANY change,
  including an edit to an ancient transaction, moves the data-version and open tabs get the reload pill.
  *Proven:* editing an old txn's date bumped the version (epoch 0→1→2); osama marble now sits on
  **2026-08-08** (mirror of its day-of-month — confirm the exact August day with Hisham).
- **System-wide UX (the guardrail that prevents the error class):** one shared **bank-style date picker**
  in `rail.js` — auto-enhances EVERY `input[type=date]` (18 across accounts·index·owed·recurring·goals·
  reports) and `input[type=month]` (calendar·categories) on every page, incl. modal-created ones (via
  MutationObserver). Themed calendar grid · month/year arrows · Today · **Hijri (Umm al-Qura) subtitle of
  the selected day** via `Intl('en-u-ca-islamic-umalqura')`. Inputs are `readonly` — **no raw date typing
  anywhere**, killing the error at its source. (Card due-day stays a constrained 1–28 number.)
- **Regression:** `scripts/check_date_edit_roundtrip.py` — an edited date MOVES the txn across months
  (Calendar reads the ledger, not a cache) AND the data-version bumps. Wired into the self-check ritual.
  PASS; picker + osama-in-August verified at 2400px.

## 🧮 One net worth, every surface — canonical `_networth()` + regression (12 Sep 2026)
Hisham caught two screens minutes apart disagreeing: net worth −113,480 vs −114,486 (gap ~1,006 on the
debt side). Diagnosed, not patched.
- **Root cause:** three separate net-worth computations (`dash()`, `brief_data()`, `accounts_grouped()`
  + the accounts-page frontend), each with its own `sar()` and account filter. Two latent divergences
  made them agree only by luck: (1) FX — the accounts frontend summed **raw** per-group balances while
  the dashboard FX-converted (breaks on any foreign balance); (2) archived/hidden — the dashboard loop
  counted them, the accounts totals excluded them. **The gap = the BNPL/financing liabilities** the
  debt side treated inconsistently: **1,005.46 = Amazon 351 + flynas #2 271.77 + flynas Riyadh 382.69** —
  one surface counted only cards as debt (130,764.87), the other counted all liabilities (131,770.33).
- **Fix (one door):** new canonical **`_networth()`** — ALL *active* asset+liability accounts,
  FX-correct, hidden included (cosmetic), archived excluded (not owned); returns assets · cash ·
  cards_debt · other_debt · debt · net. Dashboard, Morning Brief, Accounts hero + cash-vs-debt rail all
  read it; nobody re-derives. Dashboard now also surfaces **financing debt** + total debt (was cards-only).
- **The honest number:** net worth **−114,485.51** (assets 17,284.82 − debt 131,770.33). The **Accounts
  page was right**; the surface showing 130,765 debt was under-counting the financing liabilities.
- **Regression (the real deliverable):** `scripts/check_networth_consistency.py` asserts Dashboard ==
  Accounts == Brief == canonical — wired into the self-check ritual (CLAUDE.md). Two-doors-one-number
  drift is now structurally caught. PASS; both pages show SAR 114,486 at 2400px.

## 🏷 BNPL category picker → live dropdown + clickable traceability badges (12 Sep 2026)
Closing the UX + trust loop on the meaning layer: chosen from truth, provable on tap.
- **Free-text category → the standard live picker** everywhere a plan's category is set (wizard · 🏷
  meaning editor · `bnpl/purchase`): a searchable overlay reading **`/api/tree` fresh each open** (new
  endpoint) — parents + subcategories, always current, no typos, no orphan categories. Swept the
  accounts surfaces; no category free-text inputs remain.
- **Person from the live list:** wizard chips + the meaning editor now read `BOOT.persons` / `/api/tree`
  (Hisham·Sarah·Aser·Adam·Family·Maid·Driver), never a hardcoded copy.
- **Clickable badges (traceability):** the plan card's **🧳 {category} ↗** and **👤 {person} ↗** deep-link
  to the Desk — category → filtered to that category **AND** this plan (`?category=…&tag=plan:{id}`),
  person → their spending — with a wide date range so installments across months all show. One tap
  answers "did my flynas installments really land in Travel?"
- *Verified at 2400px (screenshots):* 🧳 Travel from flynas #2 → its two **271.79** installments,
  Travel-tagged, filtered to plan:396; 👤 Sarah from Amazon → the **117.00** installment sitting in
  Clothing. Fresh picker reads live categories. Transfer-visibility regression PASS.

## 🏷 BNPL plans carry category + person; all payments inherit (11 Sep 2026)
The cash model made the amounts true; this makes the *meaning* true — a plan declares what it is and
who it's for once, and every payment it touches self-files forever.
- **Wizard gains two fields:** **category** (required — e.g. flynas→Travel) + **person** (optional,
  the person chips incl. Hisham·Sarah·Aser·Adam·Family·Maid·Driver). Stored on the schedule.
- **Everything inherits both:** the checkout installment · every linked/converted installment
  (`bnpl_match` now sets the plan's category + person instead of clearing) · manual settlements.
  Real spending legs are card→provider so they never touch the liability account — caught by a new
  **`plan:{aid}` tag** stamped on every plan transaction (the account-membership match alone missed
  them; found + fixed in-build).
- **`/api/bnpl/meta`** (new) — set/change category+person and **re-tag every past payment** (skips the
  excluded funding leg). Powers **🏷 Category · person** on the plan card + the retro-apply.
- **Plan card** shows **🧳 {category} · 👤 {person}** badges in the header; **committed-money** debt
  items now carry item·category·person·date so "what's coming" reads "Travel — flynas 191 on 20 Oct".
- **Retro-applied (live plans, re-tagged):** Amazon → **Clothing · Sarah** (Aug 117 checkout now files
  in Clothing + shows in By-person Sarah); flynas #2 + flynas Riyadh → **Travel** (Travel spend total
  3,717.80 across their real installments). Verified end-to-end: fresh Tabby plan (Clothing · Aser) →
  checkout charge inherited both; By-person Sarah shows Amazon; Categories→Clothing includes the 117.
  Card badges DOM-verified. Transfer-visibility regression PASS.

## 🔍 BNPL investigation — Amazon amount, June ghost, manual settlement, Tabby model (11 Sep 2026)
Two anomalies Hisham flagged, both traced to the source of truth (bank statements) + one root cause.
**Findings (statements as arbiter):**
- **Amazon (Tabby, 29 Aug):** ledger booked the **full 468 as an Aug expense**; only **117** actually
  hit the card at checkout. The 29 Aug purchase is **outside every statement** (card •4331 statements
  cover ~26 Jul→13 Aug) → the 468 plan had **zero bank backing** (hand-entered). But the statements
  *prove Tabby's model*: every Tabby line is a **single installment on the purchase day** (20 Jul 191.34,
  23 Jul 271.79), never a plan total → **Tabby charges installment 1 at checkout.**
- **flynas #2 (Tabby, 1087.14):** the "June 23 ghost" = real txn `#851`, the plan's full-purchase lump
  **dated 23 Jun (pre-ledger)** — Hisham's own entry. It "appeared then vanished" because once verified
  it left the needs-decision queue, and being June-dated it sits **below the ledger's July window**. Not
  a system phantom — but it made **June (a month with no data) show 1087.14 of spending**.
- **Root cause (both):** the BNPL wizard assumed *"full purchase now as spending, all installments
  unpaid later"* — wrong on both halves vs Tabby's reality.
**Decision (Hisham, owner):** BNPL uses the **cash/installment model** — only what's charged is spending;
the rest is debt owed.
**Fixes shipped:**
- **`bnpl/create` rebuilt** to the cash model: the plan total funds the liability **tagged `excluded`
  (no lump spending)**; for Tabby/Tamara it asks **which card** and books **installment 1 at checkout**
  (real spend + non-cash debt reduction), so a 468 plan = 117 spent, 351 owed. Proven: 400 plan →
  inst-1 100 charged, liability −300, `proof_ok`.
- **`/api/schedule/settle-manual`** (new) — settle an installment that can't be linked (pre-ledger ·
  paid-by-other · outside · other). Reduces the liability via a **non-cash EXCLUDED deposit→liability**
  (tracked cash never moves, never counts as spend/income); marks it **SETTLED ✓ (manual — reason)**,
  rendered distinctly from the mint PAID (integrity law extended, not diluted). Button on every unpaid
  installment.
- **Corrections applied (balance-proven):** *flynas #2* — excluded the June lump (June spending
  1087.14→**0**), settled the June installment manually (pre-ledger) → liability −543.56→**−271.77**;
  inst2/3 real-PAID, inst4 next. *Amazon* — excluded the 468 lump, booked the **117 checkout** charge
  (card •4331) + non-cash debt reduction → **Aug spending −351** (now 117, not 468), liability −468→**−351**,
  inst1 PAID.
- **Queue trust:** the "vanish" is now explained and, more importantly, pre-ledger installments are
  **settleable and visibly settled** — they can't haunt the queue again.

## 📊 Fund & ETF detail — monthly price ritual + honest performance (11 Sep 2026)
Completes the instrument trilogy: certificates lead with profit streams, funds/ETFs lead with the
growth story Hisham's own monthly-entered prices build. "I put the number I see, it tells me how I'm
doing" — made professional-grade, per global fund mechanics.
- **Two facts captured honestly.** *Distributing* funds pay dividends as cash (price drops by the
  payout, so price alone understates gain) vs *Accumulating* (reinvests internally, growth all in the
  price). That's exactly why the card shows **price return** (how the price moved) vs **total return**
  (price + dividends received) — the pro's true-performance number.
- **Creation** (`+ New ▾ → 📜 Investment → fund/ETF`): units · purchase price/unit (→ cost basis =
  opening balance) · **type** distributing/accumulating (one-line explainer each). Persists `fund_type`,
  `cost_basis` (purchases + reinvested → avg price/realised gain), `capital_in` (external money →
  total-return base), and a `price_history` seeded at purchase (month one).
- **The monthly price ritual** (`/api/fund/price`): the card leads with an always-visible
  **"This month's price"** slot — type the unit price, it stamps the date (editable per-date for
  corrections; missed months stay blank, never interpolated), revalues the holding via the proven
  non-cash excluded adjustment, and grows the history.
- **Performance story** (`/api/fund/detail`): headline **Your capital: {value} · {+X%} total return** →
  price-vs-total-return pair with the distributing honesty note → month-by-month table (price · value ·
  % vs purchase · % vs prev) + inline SVG line chart from the same points.
- **Dividends** (`/api/fund/dividend`): **cash** → deposit to a chosen account as "Investment income:
  funds/ETFs"; **reinvested** → buys units at that day's price (units + cost basis grow), booked into
  the fund as income. Accumulating funds show no dividend surface. **Sell** (`asset_trade`, enhanced)
  now states realised gain = proceeds − avg-cost × units sold, and maintains cost basis both sides.
- *Proven to the fils (demos, then cleaned):* **accumulating ETF** 100u@40 + prices 42/44/41 →
  price=total return **+2.5%** (equal, no dividends); rows 5%/10%/2.5% vs purchase, +4.76%/−6.82% vs
  prev — exact. **distributing fund** 200u@50 + price 52 + cash div 300 + reinvest 400@52 → units
  200→**207.69**, current value **10,800** (balance-proven), **price return +3.85% vs total return
  +11%** (diverge correctly — dividends lift total), dividends booked as income. Card DOM-verified
  1440/2400px; transfer-visibility regression PASS.

## 📜 Certificate detail — profit-first design (11 Sep 2026)
A certificate's principal is locked until maturity; the profit stream is the living part. The card
leads with **income, not balance** — completing timeline parity with loans/leases/BNPL.
- **Creation door** (`+ New ▾ → 📜 Investment → certificate`): name+bank · currency · **principal** ·
  **annual rate %** · **rate type** (fixed, or *variable/dynamic* — history kept) · **payout frequency**
  (monthly · quarterly · half-year · yearly) · **term** (1/3/5 yr or custom → maturity date auto-fills) ·
  early-redemption penalty note. `rate_type` + `principal` now persist in `positions.yaml`.
- **Profit-first card** (`/api/certificate/detail`): TOP = income story — **Next profit: {date} ·
  ≈{amount} (as contracted)** + **collected so far** of total-to-maturity. BELOW = the **profit stream**,
  every payout dated: real deposit match → **RECEIVED ✓**; past-due unmatched → amber *expected — not
  yet received*; future stays quiet. Principal sits calm underneath as **🔒 locked until {maturity}**
  (restricted net worth, not spendable). Final card: **maturity — principal released, renew or collect**
  with the 1-month-ahead alert. Variable rate → **✎ Rate** (new rate + effective date; past payouts
  untouched, future recomputes, old rate kept in visible history).
- **Principal-freeze bug (found + fixed in build):** per-payout was computed from the *live* balance, so
  a payout deposit arriving into the cert account inflated the profit (1,583.33 → 1,608.40). Principal is
  now frozen at the opening amount in the position and read from there in BOTH `certificate_detail` and
  the aggregate `api_certificates` — one number, everywhere.
- *Proven (demos, then cleaned):* monthly EGP 100k @19% → **1,583.33**/payout, 12 payouts, Σ 18,999.96;
  quarterly SAR 200k @5% → **2,500** (12 payouts/3yr); yearly SAR 50k @6% → **3,000** (3 payouts).
  RECEIVED matching: an Apr deposit of 1,583.33 flipped that payout to ✓ (received-to-date 1,583.33,
  5 past-due amber). Variable update 6%→7% → per-payout 3,000→3,500, history `[{6.0, until 2027-01-01}]`.
  **Calendar 💰 dots + committed-income read the same per-certificate schedule** across all frequencies
  (Sep income 7,083.33 = 1,583.33+2,500+3,000, all paying on the 9th). Card DOM-verified at 1440/2400px.

## 🏦 SAMA-grade loan amortization + lease walk-away map (11 Sep 2026)
Bank-grade debt anatomy — machinery-before-need (no live loan today).
- **Declining-balance engine** (`_gen_loan_schedule`, the Saudi standard SAMA mandates): monthly
  profit = remaining balance × rate ÷ 12; principal = payment − profit. Loan setup asks financed
  amount · **annual rate** · term · start (monthly computed by annuity, editable). *Proven:*
  100k @ 6% / 36mo → monthly 3,042.19, Σprincipal = 100,000.00 exactly, Σpayments = total repayable
  109,519.01, cost 9,519.01; payment-1 profit 500 → payment-36 profit 15.14 (shrinks, never stops).
- **The SAMA table** (expandable): # · date · payment · **profit** · **principal** · **balance after**,
  with the **◆ crossover row** (principal overtakes profit). Summary header: paid (principal/profit) ·
  remaining · next-payment split · total cost. **⚖️ Settle-today estimate** = balance + next 3 months'
  profit (SAMA declining-balance), honestly labelled "your bank's figure is final". Profit still feeds
  the Riba lens. Same table grammar for leases.
- **Lease Walk-Away Map** (`/api/lease/terms` + 🚪 If-I-exit-here): per-month "if I stop here" view from
  the contract's OWN early-termination clause (free text, never guessed) + committed-remaining; final
  row shows **both endings** — pay balloon → own (vs your resale estimate) or **return → balloon waived**.
  Built-in honesty note: Saudi allows the end-of-contract return; **mid-term exit is your contract, not
  a legal right**, and handback may not discharge everything. Loan SAMA view DOM-verified; lease
  walk-away shares the render path + endpoint tested.

## 💳 Per-card payment contract (mode + due rule) — the credit-card story closed (11 Sep 2026)
Each card's account detail gains **✎ Card settings** (self-service, `card_settings.yaml`, never guessed):
- **Payment mode:** Full, or Minimum (% + SAR floor — banks charge max(%, floor); capped at balance).
- **Due rule, both dialects:** *Day N of next month* (SNB = 5th) or *Last day of the month* (SABB) —
  per card. Next occurrence rolls forward correctly.
- The card shows **“Due {date}: SAR X”** computed from the live balance; it joins **committed-money**
  (expected payment in its true month) + a **💳 Calendar dot** on the due day + amber when ≤5 days out.
  Minimum mode carries a quiet honesty line (rest carries forward — fact, not advice; coaching gated).
- *Proven:* SNB 6510 (full, day 5) → due **2026-10-05** = full; SABB 4331 (min 5% floor 100, monthend)
  → due **2026-09-30** = 1,500; tiny balance caps at balance; committed picks it up. Test settings
  cleared — his real 5 cards stay unset for him to enter from the bank apps (mode · %/floor · due rule).
- Closes the card story: networks ✓ · limits ✓ · utilization ✓ · **payment contract ✓**.

## قطة QATTAH — shared-order splitting into per-person receivables (11 Sep 2026)
The most culturally-native feature in the system — Splitwise never heard the word. Three truths from
one action, balance-proven.
- **The Qattah action** (Desk expense detail; reachable from Calendar via tap-through): *قطة Split
  this shared order* → pick who else is in from the **inner circle** (free-add joins it; frequent
  groups remembered as "the usual") → **÷ Equal** (divides by everyone incl. you) or **✎ Custom**
  (type each; the remainder is automatically your share — the Money Pro instinct).
- **Under the hood** (`/api/qattah`): re-points the one expense into *(your share = the expense, same
  category)* + *(each other share = transfer → Owed-to-me + a receivable record, origin:qattah,
  merchant+date)*. **Three truths:** account still −full (cash), analysis counts only your share
  (consumption), each person's tab grows (receivable). *Proven:* 300 McDonald's 3-way → account
  −300 unchanged, Eating-out +100 only, Noura +100 / Soha +100, `proof_ok`.
- **One person universe, circle is convenience:** `qattah_circle.yaml` (self-service add/remove) only
  decides who's in the quick picker; the owed-to-me ledger stays open to anyone. Receivables gained
  an **origin** (qattah|loan|other); Owed-to-me page gained a **قطة lens** + per-person origin
  breakdown ("Noura: 300 — qattah 250 · loan 50") + the قطة summary total. Guide recipe same-commit.
- **Staged (BLOCKED §Qattah):** the **I-owe direction** (someone else paid; you owe your share →
  books into the I-owe liability, origin qattah) and the **⚖️ Settle** action (net "she owes you /
  you owe her" into one recorded settlement) — both need the asset↔liability offset shape worked out
  (the M2.0 wall). The headline (you-paid → receivables) is complete and proven.

## ⇄ Two-sided transfer visibility (Money Pro model) + located Hisham's charges (11 Sep 2026)
- **The 20/7 transaction:** not a hidden-view bug — it was my wrong-direction write (785), correctly
  deleted in the polarity repair. Nothing to restore; flynas balance is right.
- **His real charges, located:** the true 20 Aug installment (191.35) was already in the ledger
  (txn 573, Hisham SNB main). The true **20 Jul installment (191.34) was never imported** — found it
  in `TransHist (1).csv` (SABB Alfursan card ...4331) and **booked it** (txn 813, 20 Jul, statement
  provenance). Both now exist as plain expenses for Hisham to convert himself.
- **Disease cured — `account_series` (account detail) was SOURCE-ONLY:** a transfer/discharge INTO an
  account never showed on that account. Now includes **both sides**, and renders each row from that
  account's perspective, Money Pro-style: **"⇄ to {other} −amt"** on the payer, **"⇄ from {other}
  +amt"** on the receiver. (`/api/transactions` account filter was fixed both-sided last turn.)
- **Regression fixture:** `scripts/check_transfer_visibility.py` — asserts a transfer shows in BOTH
  accounts with opposite signs; added to the self-check ritual in CLAUDE.md. Verified **PASS**
  (⇄ to Sarah's wallet −123 / ⇄ from Hisham Wallet +123).
- **Acceptance walk is Hisham's:** convert 813 (20/7) → flynas 765.38→574.04, JUL flips PAID · convert
  573 (20/8) → 382.69, AUG flips · both transfers visible from both sides.

## 🔧 Four fixes — schedule anchoring · transfer visibility · Desk search · Edit-installments (11 Sep 2026)
1. **Schedule anchored to the wrong date (BUG):** the generator built from "next due" instead of the
   plan START, so flynas (started 20 Jul) began in Sep. New `/api/bnpl/reschedule` generates from the
   start date; past unpaid installments render **overdue amber** ("was due 20 Jul"). Repaired flynas →
   Jul/Aug (overdue) · Sep (next) · Oct (future). `_mshift_iso` helper.
2. **Converted transfers "disappeared" (BUG):** at the API level the converted discharge was always
   visible (search/all_txns/Calendar) — the real gap was the Desk account filter matched only the
   SOURCE, so a discharge (→ liability) didn't list under the debt account. Filter now matches
   **either side** — the payment shows under both the card AND flynas. (It correctly leaves the review
   queue once verified — that's handled, not lost.)
3. **Desk search broken (BUG):** typing fired `debS()` → `loadAll(true)`, which **rebuilt the panel
   incl. a fresh empty search box** — wiping the query every keystroke. `debS` now refetches the list
   only (query + focus preserved; `ALLQ` restores across filter re-renders).
4. **Installment count via Edit (FLOW):** creation stays minimal; the plan card carries **✎ Edit plan**
   → set/change installments (+ start), which re-lays the schedule from the start and preserves
   already-linked payments. Empty-with-balance shows **✎ Set installments**.

*Reminder rails already carry the next installment (Calendar dot · committed · alerts). The one missing
last mile is the **ntfy topic** (Hisham's 5-min setup) — until it's set, notifications compose but can't
reach his phone.*

## 📆 BNPL plan card → Tabby-style schedule timeline (11 Sep 2026)
Rides on the polarity fix. Replaced the financing stats block with the payment *story* Hisham knows
from his Tabby app: a **vertical list, one card per installment**, top-to-bottom, each with a date
block (day + month), amount, "Payment N of M", and a status on the right — **PAID** pill (mint, only
from the integrity law: a real linked discharge), the **next-due** card highlighted (gold), future
ones quiet, overdue amber ("not yet linked"). Header carries plan · total · owed · N-of-M-left.
- One renderer for BNPL, loans and leases; loans/leases keep **Record-payment** on the next-due card;
  balloon renders as its own 🎈 final card. Auto-retirement unchanged (all-PAID → Completed).
- No "Pay" button (we're a ledger) — the next-due card carries the honest hint: *paid it? convert the
  charge to a transfer → this plan.*
- *DOM-verified* on a 4-installment demo: JUL/AUG **PAID**, SEP **NEXT**, OCT quiet, Payment 1–4 of 4,
  invariant ✓ — then cleaned. (Pixel screenshot fought the deep-link auto-scroll; DOM is authoritative.)

## 🔁 BNPL connection = the plain transfer verb (11 Sep 2026)
Final door, literal to Hisham's ask: **no ⇄, no special sentence.** He opens any charge (Calendar or
Desk), changes its type to **transfer**, picks the debt account (flynas) as the destination from the
normal account picker — and the debt drops. Identical to how he pays a credit card.
- **`/api/transfer` translates silently:** when the chosen destination (or source) is a liability,
  the backend builds the proven `withdrawal → liability` discharge instead of a literal transfer
  (which Firefly 422s — the M2.0 wall). He never sees the 422 or a special verb — he picked an
  account, the money moved, the debt dropped. Downstream: the plan's schedule advances (installment
  counted, N-of-M, next-date) and auto-retires at zero — the schedule reads discharges regardless of
  which door made them. Same verb for ALL liabilities (BNPL/loan/lease/"I owe").
- **Bug found in the translation:** a single-account GET returns `type:"liabilities"` (plural), so
  the first `== "liability"` check missed and it fell back to the 422 shape. Fixed to accept both.
- **⇄ affordances removed** entirely — the Calendar day-panel button and the Desk "This belongs to a
  BNPL plan" block are gone. One familiar verb, everywhere.
- *Proven:* convert a 200 charge → transfer to a 600 plan → debt 600→400, schedule 1 of 3, next date
  advanced, invariant ok, no 422. Cleaned.
- **Hisham's flynas (351)** is set up correctly through the integrity-safe flow: 4 × ~191.34 = 765.38,
  all due, **0 falsely paid**, invariant ✓. He now converts each real Tabby charge to a transfer→flynas.

## 🚪 BNPL — doors rebuilt to Hisham's walk (11 Sep 2026)
The engine (discharge shape, integrity law, auto-retirement) was right; the surfaces were wrong.
Hisham's exact walk: **create with four facts → go to the transaction (Calendar/Desk) → “this belongs
to my Tabby” → done.** The plan card is a display, not a workbench.
- **Creation** — 🛍️ New Tabby/Tamara plan: name · total · start date · installments. Auto-divides,
  books the purchase, builds the schedule. No linking step in creation.
- **Connection lives on the transaction** — Calendar day-panel rows and Desk both carry a one-tap
  **⇄ “This belongs to a BNPL plan”** → pick plan → proven `withdrawal→liability` discharge, debt
  drops, installment counts. (The manual “transfer into a debt account” he tried is the exact shape
  Firefly 422s — this does the same thing through the shape it accepts.)
- **Plan card = display only** — owed now · N of M remaining · next payment date · progress · the
  connected-payment history. Removed the Link-a-payment button and candidate lists. Invariant stays
  enforced but silent (“✓ balance ↔ schedule agree”; speaks only on mismatch). Loans/leases keep
  Record-payment (paid from cash, not card charges).
- **Reminders** unchanged (Calendar dot · Upcoming · committed-money); **auto-retirement** unchanged.
- *Acceptance walk proven:* create 600 (=3×200) → Calendar day shows ⇄ on the charge → tap connects
  it (−600→−400, proof ok) → card shows 2 of 3 remaining, next 2026-10-05, 1 connected payment,
  invariant ok. Then cleaned.
- **Hisham's real flynas** re-entered live as account 351 (765.38 debt, opening balance, no schedule
  yet — honest, no false claims). His next tap: *Set up its schedule* on the account (existing-balance
  path, no double-count), then connect charges from the Calendar as they fall.

## ⚖️ BNPL integrity law + full lifecycle (11 Sep 2026)
**The integrity bug Hisham caught:** the first `bnpl/declare` recorded a typed "2 paid" and marked
installments paid **with zero real discharge transactions behind them** — the card claimed 2/4 paid
while the balance read the full total. A number typed into a form was masquerading as truth. That is
exactly what this system exists to refuse.

**The law now enforced & displayed:** `|liability balance| = Σ(unpaid installments)`, AND
`installments marked paid ≤ real linked discharge transactions`. `/api/schedule` computes both and
returns `invariant_ok` + a plain-language `mismatch` ("2 marked paid but only 0 linked — link them").
The plan card shows *owed now · remaining · linked payments*, never two contradictory claims.

**Redesign — "paid" is only ever a real linked transaction:**
- `bnpl/declare` no longer fakes a paid count — it records only the REMAINING installments (summing
  exactly to the balance) and **refuses inconsistent numbers** rather than fudging a monster last
  installment. "6 total / 2 before" is display context, never a paid-claim.
- **Link a payment** (plan card) / **⇄ This belongs to a BNPL plan** (Desk, from the charge itself):
  re-points a real expense into the proven discharge shape (`withdrawal → destination = liability`);
  the debt drops per link, balance-proven, original preserved, never double-counted.

**Full lifecycle shipped (spec §1–6):**
- **Birth** — one wizard: *Accounts → 🛍️ New Tabby/Tamara plan* (provider · item · total ·
  installments · dates · category). HAKIM **auto-divides** (total ÷ N), creates the account, books the
  purchase once, builds the dated schedule. No assembly.
- **Life** — installments ride the reminder rails (Upcoming · Calendar dot · committed-money).
- **Death** — when the last installment links and the balance hits 0, the plan **auto-retires** to a
  dimmed **"Completed plans"** section; the active list shows only live debts, history is kept
  (exclude-not-delete for accounts). Loans/leases retire the same way.
- *Proven end-to-end:* create 200 (=2×100) → link #1 −200→−100 (invariant holds, paid 1 = linked 1)
  → link #2 −100→**0, auto-retired**. All balance-proven, then cleaned.

**Banked lessons reused:** the M2.0 wall is real (transfers into a liability 422 — paydowns must be
`withdrawal`); `current_balance` is as-of-today, so only past/today-dated discharges move it (a
future-dated link is honestly flagged, not silently "paid").

**flynas:** deleted at Hisham's instruction (clean slate — no orphan schedule/kind, his real charges
untouched). It re-enters as the acceptance test through the new wizard, with real numbers.

## 🧾 First real-use report — Tabby retro-declare (11 Sep 2026)
The post-build era's first real receipt found its first real gap within the hour — not a bug in what
was built, but a **missing door** the test data never needed (test plans had no *past*; the real one does).

**What happened:** Hisham created his real Tabby account (`flynas`, id 344, opening balance 765.38 =
his remaining debt), then tried to convert his already-paid installment charges into **transfers** into
that account → Firefly **422**.

**Root cause (named):** the M2.0 wall — Firefly refuses a `transfer` into a liability
(*"Could not find a valid destination account for ID 344"*). The proven paydown shape is
`withdrawal` → destination = liability. His manual re-point used the exact shape the system itself
had to abandon. Confirmed by reproduction.

**Fixes shipped:**
1. **`/api/bnpl/declare` — "Declare the plan (schedule only)."** For a BNPL account that already
   carries its remaining balance (the retro case), this builds the installment schedule (Calendar
   dots · committed money · reminders) and **moves no money** — the remaining installments sum
   EXACTLY to the account balance, so it never double-counts. *Verified on flynas: 6 installments, 2
   paid → 4 remaining = 765.38 = the balance, to the fils, no money moved.* (Using "New BNPL
   purchase" here would have doubled the debt — the wizard steers away from that.)
2. **"🔗 Link an existing charge"** on the BNPL detail — pick a past card charge → discharge it via
   the proven shape (`/api/bnpl/match`), original preserved, balance-proven, never counted twice.
   The manual twin of the N-wave auto-matching, for *historical* charges.
3. **Empty BNPL account no longer a dead end** — a debt-carrying account shows a prominent
   *"already carries SAR X of debt — Declare the plan →"* prompt; a zero-balance one steers to
   *New BNPL purchase*. No orphan empty rooms.
4. **No raw errors reach the owner** — a global `httpx.HTTPStatusError` handler humanises Firefly
   failures (the 422 that leaked → *"Firefly won't accept this shape — you can't move money straight
   into a debt account with a plain transfer; use Record payment or Link an existing charge."*).
5. Guide gained a **"Declare a BNPL plan you're already paying"** recipe (same commit).

**No data harmed:** the 422 attempts never persisted; flynas held only its legitimate opening balance.
The test declaration was cleared — Hisham enters his real installment count/dates via the new door.
The walk-through rhythm survives the build era's close, exactly as it should.

## 🏁 BUILD ERA COMPLETE — Wave N+Z (+B pt2), the final rung (11 Sep 2026)
One combined closing wave, twelve items. HAKIM Finance is now **done in every way building can do
it** — the only remaining ingredient is lived weeks.

**N — nervous system:**
- **N1 Live data-refresh** — `/api/data-version` (cheap ledger fingerprint) + `/api/webhook/firefly`
  receiver; rail.js polls every 20s and shows a **🔄 refresh pill** when the ledger changes (new SMS
  txn, an edit, a delete). Each page exposes `window.hakimReload` for in-place refresh. Point a
  Firefly webhook at `/api/webhook/firefly` for seconds-latency; without it the poll still catches it.
- **N2 Transaction-links UI** — **bug found & fixed:** the old link code hit `link_types` /
  `transaction_links` (underscore) which **404 on this Firefly** — links never worked. Corrected to
  the hyphenated `link-types` / `transaction-links`. Desk now shows readable links ("(partially)
  refunds …"), a relationship picker (relates/refund/paid/reimburse), search, and ✕ unlink. Verified
  round-trip.
- **N3 Bill paid-status** — HAKIM-tracked marks (`bill_marks.yaml`) on top of the name-match
  heuristic (native `paid_dates` stays empty because SMS imports carry no `bill_id`). Recurring pill
  toggles paid/expected; **committed-money counts only the unpaid remainder**; Calendar dots flip.

**Z — closers:**
- **Z4 Strictness dial** — per-category `rollover` = carry (default) | strict; a strict envelope
  resets monthly (no carry-over). Toggle in Categories → Manage.
- **Z5 Two-period compare** — `/api/category/compare`; Categories → **⇄ Compare** picks any two
  months, per-category deltas, biggest movers first.
- **Z6 Merchant map** — `/api/merchants` + save/delete; **Settings → Merchant map** manages the
  normalization rules (the “Aser STC” class of fix) in-app.
- **Z7 Trip tagging** — `trip:<name>` tags via the Desk’s 🧳 Trip box; **Reports → Trips** totals each
  journey. Verified tag/summary/untag.
- **B8 Hijri budget periods** — a category target can be reckoned per **Hijri month** (Umm al-Qura
  cadence, ~29.53d).
- **B9 Budget history grid** — `/api/budget/history`; Categories → **▦ History** shows months ×
  categories, target-vs-actual ✓/✗, honest only from months with data.
- **B10 Irregular bill dates** — the **school-fees** shape: N specific dates + per-date amounts over
  ONE bill (`bill_schedules.yaml`, thin overlay — never three fake bills). Counts in Committed in its
  true month, lands on its own Calendar days; **🧧 sinking-fund handshake** creates an envelope toward
  the total. Verified: School 5,000 counted in Sep, Jan instalment excluded.
- **ⓘ In-place explainers** — single-sourced dictionary (12 concepts) + `data-tip` delegation in
  rail.js; any page drops an ⓘ. Placed on net-worth, committed, owed, paid-status, and more.

**G-split (item 12):** functionally covered by Wave M’s Record-payment (principal/cost split); a
dedicated Desk manual-split surface remains **optional polish** in BLOCKED.md — not built, honestly logged.

**New stores this wave:** `bill_marks.yaml`, `bill_schedules.yaml`. Guide gained 8 recipes same-commit.
**The ladder is finished. What remains is not building — it is Hisham’s lived weeks + the papers evening.**

## ✅ WAVE H — Household (11 Sep 2026) — the culturally-yours wave, complete
Five flows, the money-moving ones balance-proven, all cleaned after test.
1. **Owed-to-me ledger** (`/owed`, new rail page 🤝) — per-person receivables layered over the
   Firefly "Owed to me" asset account. **Lend** posts a real transfer cash→Owed-to-me; **Repay**
   transfers Owed-to-me→cash. Running balance, aging ("3mo ago"), settled state, and an **invariant
   line** proving the per-person ledger sums to the account balance. **Migrate** attributes the
   pre-existing 250 lump to a person with no money movement. *Proofs:* lend 500 → Owed 250→750,
   cash 666.67→166.67 (`proof_ok`); repay 200 → Owed 750→550, cash 166.67→366.67, outstanding→300
   (`proof_ok`). Cleaned.
2. **Cash-count wizard** (Accounts → 🧮 Count cash) — lists every physical-cash account (wallets,
   safes, kids'/EGP/USD/AED safes, HISSAR trading cash) with book balance + live diff; applies an
   adjustment per line **in the account's own currency**, stamped "counted {date}". Per-account
   **last-counted staleness** in the detail (amber >45d) + `/api/accounts` carries it. *Proof:*
   Sarah's wallet 0→300, +300 adjustment, after=300 (`proof_ok`). Cleaned.
3. **Seasonal goals** (Goals → New goal → 🌙 By season) — Ramadan · Eid al-Fitr · Eid al-Adha ·
   School start, resolved to the **next occurrence** via Umm al-Qura (`/api/seasons`); the deadline
   **rolls forward automatically** each read. Season chip on the card. *Verified:* Eid al-Adha →
   2027-05-16.
4. **Goals math** — required **per-month** (remaining ÷ months-left) + **25/50/75% milestone ticks**
   on every dated/seasonal goal card. Arithmetic only. *Verified:* 6,000 target, 8 months → SAR 667/mo.
5. **Riba & fees lens** (Reports → 💸 Cost of debt preset, new `riba` report type) — gathers the real
   "Bank & fees: financing cost" charges Wave M's flows book: total, avg/month, **per-card/per-loan
   bars**, **6-month trend line**. Empty-and-honest until real financing costs exist.
Guide gained 4 recipes (Owed-to-me, Count cash, Seasonal saving, Cost of debt) same-commit.
**Cleanup, named honestly:** the new Riba lens surfaced **Wave M test residue** — an orphan loan
schedule (321, account purged) + two financing-cost test txns (730/741) that had inflated **Hisham
Wallet by a fake SAR 666.67**. Removed all three; wallet now reads its true **0** (count it with the
new wizard). New stores: `receivables.yaml`, `counted.yaml`. **Ladder: Wave N → Wave Z. Then done.**

## 🛡️ Dead-man's switch + branch merge + quick wins (10 Sep) — branch `feat/loose-ends`
- **Branch merge (Brief 3):** the linear ladder (master → feat/calendar → feat/moneypro-comfort →
  feat/accounts-tab, 29 commits) fast-forwarded into **master**. Going-forward: one ladder branch per
  review-tour page/wave, merged when Hisham accepts. New work now on `feat/loose-ends`. All 11 pages
  green post-merge, fresh restic snapshot (8 snaps / 1.9M).
- **Dead-man's switch (Brief 2):** silent agent death is the one real failure mode — closed it.
  (1) Weekly health line now states **"all 6 agents ran this week — nightly-backup · backup-trigger ·
  restore-drill · health · morning-brief · sms-capture all green"**, and names any that didn't, loud.
  (2) The line carries the **dead-man principle in its own text**: "you get this every Sunday — if it
  stops arriving, the health agent itself is down; check /settings → Agents." (3) **`/settings` →
  Agents panel** (`/api/agents`, reads live from the mounted `~/Library/Logs/hakim` + logs dirs): each
  of the 6 agents with green/red dot + last-run + expected interval + run-now on backup. (4) **Dashboard
  alerts strip** gains a red "Agent {name} hasn't run in {interval}+" (dead-man alert). Added a
  `:/app/joblogs:ro` mount.
- **Brief 1 quick wins:** #5 **queue burn-down snapshot** — the morning brief now writes a daily
  `data/queue_history.json` point (`/api/queue_history`); the To-review trend becomes real as history
  accumulates. #6 **SADAD chip cosmetics** — Desk merchant filter chip shows a clean prettified name,
  not the raw normalized key. #7 **Net-worth ⇄ Debt-remaining toggle** on the dashboard hero
  (presentation-only: shows |net worth| falling toward 0 with "↓ shrinking debt" in mint; never inverts
  the series/axis). Plus a consistency fix: rail.js now injects its own `.acc/.rsec` styles so the
  sidebar account widget is identical on every page (was cramped on /settings).
- **STAGED for dedicated passes (Brief 1 heavy + Brief 4):** G+L money-write micro-wave (#1 — mints
  linked transactions, needs full balance-reconcile + undo instrumentation), cross-month split ⑂ (#2),
  strictness dial (#3), two-period compare (#4), merchant manage surface (#8); Brief 4 tour self-audit
  (report list). Reasoned in the session report.

## 📖 Categories restructure — the biography of your spending (10 Sep) — branch `feat/accounts-tab`
Big rework so spending-share/budget live in their right homes + the "one bar, two meanings"
ambiguity dies + hierarchy math is honest. Backend + full render rewrite; verified @2400/1440.
- **Sections:** main column splits into EXPENSES (header+total) then INCOME (mint header+total),
  each sorted by amount, both in Rows and Circles. Summary strip: Total spending · Total income ·
  Net · vs-last-month.
- **Bar convention (Money Pro, Addendum C — one meaning):** target → coloured fill spent/target %
  (caps 100% visually, label shows true %, rose >100); no target → FULL dim dashed bar = "no limit",
  label "no target · set →" (opens Manage). Section legend explains the two states once. Killed the
  old spending-share-in-the-bar ambiguity.
- **Spending share → right rail (Addendum, all clickable):** ALL active exp cats (not top-N) with %
  + mini-bar, donut on top, scrollable, each row → openDrill. Rail also: **Income** (by source +
  total + vs-last-mo), **Movers** (ALL cats w/ meaningful change both directions, clickable),
  **Unused** (kept), **Budget health** (≥1 target: N of M on track + worst offender — arithmetic only).
- **Retired the Budget toggle** (Rows⇄Circles remain); added a "with targets" filter chip. COMING-
  SOON Budget tab stays (that's the future intelligence engine, distinct from these manual targets).
- **Direct-on-parent (Addendum A — math-transparency LAW):** backend `direct` = parent total − Σ subs.
  Drill shows a **⊙ Parent (direct)** pseudo-row + a sum-check line "subs X + direct Y = total ✓" so
  the visible children ALWAYS sum to the header (the bug: 15k booked on the villa parent was invisible).
  Row → Desk `?catexact=Parent` (exact category, excludes subs; new backend filter) + "assign to subs →"
  cleanup CTA (Addendum D). Applied on the Categories drill; Reports/Desk-chip parity is a follow-up.
- **Drill dossier (Addendum E):** new `/api/category_detail` — monthly avg, highest month, txn count,
  first-seen, top merchants within the category, 6-month trend bar chart. Row sparklines restored.
- **vs-typical (F):** each row shows "typical SAR X" (3-month avg from trend). **Season chips (G):**
  summary shows 🌙 Ramadan / 🎉 Eid / 🕋 Hajj / 🎒 back-to-school when the period overlaps (Umm al-Qura,
  `_season`). **To-review burn-down (I, light):** "+N added this week" from created dates (true
  down-trend needs a stored daily snapshot — noted).
- **STAGED (Addendum B + H)** — honest follow-ups, not built this pass: **B** strictness setting
  ("require subcategory on a parent with children", default OFF + Desk-picker disable/hint — Money Pro
  behaviour as a dial); **H** two-period compare view per category (Reports already expresses it).

## 🚪 Dashboard deep-links — every data point is a door (10 Sep) — branch `feat/accounts-tab`
Turned the dashboard from a report you read into a map you travel. Inner data rows now each
navigate to the filtered truth behind them, carrying the dashboard's active month.
- **Backend:** `/api/transactions` gained `merchant` (matches `merchant_key`) + `dow` (0=Mon..6=Sun)
  filters; person reuses the existing `tag` filter. `/api/dash` merchants now include `key`.
- **Desk:** boot reads `?merchant=` / `?person=` (or `?tag=`) / `?dow=` → filtered All view;
  dismissible 🏬 merchant / 📅 day chips; query carries them + `from`/`to`.
- **Click → destination map:** category row → Desk `?category=&from&to` · top-merchant row → Desk
  `?merchant=key&from&to` · by-person row → Desk `?person=&from&to` · day-of-week bar (with data)
  → Desk `?dow=i&from&to` (empty days non-clickable, cursor default — no fake handle) · recent
  activity row → Desk `?txn=id` (opens the card) · card face + mini-rows → `/accounts?account=` ·
  quick-nav Card debt + Available cash → `/accounts` (were stale `/account` and `/`).
- **No-dead-doors sweep:** added `cursor:pointer` to `.trow` (were clickable-on-hover but no
  pointer); alerts without a destination now render `cursor:default` (were fake handles);
  audited every pointer-cursor class — informational rows (upcoming payments, completeness
  squares) correctly stay non-doors.
- Verified: merchant/dow/person backend filters return correctly; `?dow=2` deep-link lands on the
  Desk filtered to Wednesdays with the month range + a dismissible chip. @2400px dashboard intact.

## 🩹 Desk right-rail regression + global Ask Finance (10 Sep) — branch `feat/accounts-tab`
- **REGRESSION (root cause named):** the Desk's right rail (This Session / Biggest First / By
  Account / Recently Resolved) vanished after the rail.js consolidation. Cause: the Desk's header
  **HUD strip (#hudclock/#hudlive/#hudqueue) lived inside the old left-rail markup** that the
  shared-rail refactor replaced; `startClock()` had **no try/catch**, so `getElementById('hudclock')`
  → null → `.textContent` threw → **init aborted BEFORE `renderDeskRail()`**, silently killing the
  right rail (and the New badge). Fixed by guarding `startClock` (clock now lives in the shared rail
  anyway). **Audited all 11 pages:** the Desk was the ONLY casualty — every other page's `loadRail`
  is try/catch-wrapped and no other init fn touches rail elements unguarded. Lesson logged: a
  regex-replace of shared chrome can take an unrelated neighbor down when a sibling init isn't guarded.
- **Ask Finance went global (into the shared shell):** moved out of the Desk-only bottom bar (removed)
  into `rail.js` — a persistent **✦ Ask Finance…** affordance pinned above the sidebar status on every
  page, a global **⌘J** shortcut, and an overlay that works page-independently (posts the current page
  as context to `/api/ai`). Honest helper text: reads the live ledger (cash position, spending by
  category, "what is SADAD 902?"), answers personal-finance only, defers business/trading/factory +
  the coaching still coming. The ⌘K palette's Ask action now calls the same global handler. Verified
  live: "what's my cash position?" → real answer. `?ask=1` deep-link opens it.
- Verified @2400px + @1440px: Desk right rail restored, Ask Finance reachable from Dashboard/Accounts/
  Reports/Desk.

## 🗺️ Complete "Coming in waves" map (9 Sep) — branch `feat/accounts-tab`
The sidebar now shows the system's whole future, honestly — and BLOCKED.md became the single
complete register (no longer partial).
- **BLOCKED.md rewritten as the master register** (A–F): reconciled the build-logged blockers
  with the full Hisham/Claude session history. A = surplus-gate intelligence · B = the G+L
  money-write micro-wave · C = data-completeness/human tasks (+ Morning Brief NTFY, Tailscale) ·
  D = maturity/scale (Insights, receipt-items, tell-Finance) · E = deferred-by-choice (light
  theme, Arabic, custom dashboard, Tauri, PWA, hakim-ui pkg) · F = ecosystem (Factory, MENTCO,
  Regulatory, Shield, Scout, IDEAS). Flagged: **Wealth/SIMAH needs an access decision Hisham
  hasn't made**. Marked **custom icons ✅ SHIPPED** (was listed pending). Tab-worthy items → [TAB].
- **rail.js COMING IN WAVES** — 9 dimmed SOON surfaces in unlock order: Today · Budget · Forecast ·
  Subscriptions · Debt coach · Zakat · Wealth · Family · Insights. Grayscale icons + SOON tag,
  self-contained injected CSS so they read quiet on every page (the future must not shout over the
  present). **Recurring moved UP** into the live nav (it's live, not coming); Settings joined it.
  Each SOON row → `/soon?s=<key>`; the section header has an `all →` link to the `/soon` index.
- **`/soon` honest placeholder** (soon.html, one template): single-surface detail (icon, wave,
  what-it-does, a **🔒 Unlocks when** block with the named gate, and a "traces to Blueprint §X ·
  register #" line) OR the full index grid. **No mock data, no fake previews** — the promise and
  the gate only. Every entry traces to a real BLOCKED.md/blueprint item. Kept the single-entry
  collapse option wired (the `all →`/`/soon` index) but shipped the full 9-item map — at 2400px it
  reads as a quiet, intentional roadmap, present stays dominant.
- Non-tab future items (tell-Finance, receipt-items, whisper layer, cross-month split ⑂, G+L,
  ecosystem) intentionally kept OFF the rail — in BLOCKED.md, not cluttering the map.
- Verified @2400px (dashboard rail + /soon?s=today). `/soon` route + soon.html baked in Dockerfile.

## 🏦 Accounts as a first-class tab (9 Sep) — branch `feat/accounts-tab`
Accounts was split (sidebar widget + /accounts view + management buried in the Desk) with
affordances that flickered per-page. Promoted to a real tab + one command center + a truly
shared sidebar shell.
- **Shared rail shell (`rail.js`, served at `/rail.js`, one component):** replaces the
  per-page `<aside class="rail">` on ALL 11 pages with `<aside id="hakim-rail">` + the script.
  Renders identical nav (Dashboard · Desk · Calendar · Categories · Reports · Goals · **Accounts**
  · Recurring · Settings), path-based active state, the live balance widget with a **manage →**
  link, cards, and status (SMS/queue/backup/clock). Account clicks anywhere route to
  `/accounts?account=NAME`. Fixes the root inconsistency (was wired per-page). Desk keeps its
  special RIGHT rail (`renderDeskRail`); its `loadRail` is now a no-op so it never fights the shell.
- **`/accounts` rebuilt as the command center (accounts.html):** net-worth hero (assets/debt);
  grouped sections (Payment accounts · Wallets · Cards · Owed to me · Other assets · Other
  liabilities) with rich rows (avatar, network mark, directional balance, subtotals) + **drag-
  reorder within group**; **click-to-expand inline detail** — balance curve (full chart anatomy),
  recent activity, cleared vs available (when reconciled), and ALL management inline (add · edit ·
  correct-balance · hide/unhide · merge · close · delete · card network); **Hidden & closed**
  collapsed section; right rail insight (cash-vs-debt split · accounts by group · card debt).
- **One owner:** the Desk's in-page account manager is retired → its header button is
  **"Manage accounts →"** and `openAccounts()` redirects to `/accounts`. Accounts owns account
  management; the Desk owns judging transactions.
- Verified @2400px + @1440px across Desk/Categories/Reports (identical rail) + the /accounts page
  with an expanded account (balance chart + actions). `/rail.js` + accounts.html baked in Dockerfile.

## 🚨 Backup incident + visibility (9 Sep) — ROOT CAUSE NAMED, fixed & proven
**Symptom:** dashboard "⚠ BACKUP FAILED"; last real snapshot was 32h old. **Root cause (not
just symptom):** the `com.hakim.backup` launchd agent had **never run successfully** — every
snapshot in the repo was a *manual terminal* run (all at midday, never the 03:15 schedule). The
agent died at launch: first with **exit 78** (its `StandardOutPath`/`StandardErrorPath` pointed
into `~/Documents/`, which is **TCC-protected** — launchd couldn't open the log), then, after
moving the log, with **exit 126 "Operation not permitted"** because launchd/bash also can't
*execute* a script inside `~/Documents`. The nightly was silently dead since setup; only the
30-hour staleness guard surfaced it. (sms-capture survived only because its venv python was
granted Full Disk Access.) **Fix (no fragile manual FDA grant):**
- Script now lives OUTSIDE Documents at `~/Hakim-Backups/backup.sh` (source: `scripts/backup.sh`,
  installed copy); logs → `~/Library/Logs/hakim/backup.log`. Plist updated (`launchd/com.hakim.backup.plist`).
- Backup reads project data **through Docker** (which has FDA): `docker cp` for `data/` +
  `hakim-brain/` (added a `:ro` mount), `docker exec` to write status/manifest into `data/` — the
  host process never touches `~/Documents`.
- Fixed the "no parent snapshot" bug (was a random `/tmp` staging path → full re-read nightly);
  stable `~/Hakim-Backups/.staging` → real incremental (verified "using parent snapshot").
- **Proven via launchd** (not manual): `launchctl kickstart` → **exit 0**, snapshot saved, status
  green. Repo now 1.7M / 7 snapshots.
- **Recurrence guard:** the 30h staleness footer stays; the fix means the agent actually runs on
  the next wake after a missed 03:15; plus a manual **Back up now** safety valve (below).

**Backup visibility (item C) — `/settings` → Backups:** last snapshot time + green/red status,
snapshot count + repo size, location, schedule, retention, includes list, recent-snapshots list,
and a **Back up now** button. The app is containerised and can't run host restic, so: the nightly
publishes `data/backup_snapshots.json` (via Docker); "Back up now" writes a trigger into a
**non-Documents** mount (`~/Hakim-Backups/triggers` → `/app/triggers`) that a new launchd
**WatchPath** agent `com.hakim.backup-trigger` watches → runs the same `backup.sh` (dedup: delete-
then-run so the delete event doesn't loop). Proven end-to-end (button → snapshot in ~6s). Restore
stays deliberately **not** one-click (assisted only). Endpoints `/api/backup/status|run`.

**Fleet-wide fix (same root cause) — all 6 launchd agents now exit 0:** the Documents-TCC trap
hit every agent launchd ran via a non-FDA interpreter. Fixed: **morning_brief** (was exit 2 —
`/usr/bin/python3` can't even open a script in Documents) + **health_check** now run via the
**FDA-granted `.venv-importer/bin/python3`** (the same interpreter sms-capture uses — the one agent
that always worked); **restore_drill.sh** relocated to `~/Hakim-Backups/` with logs → `~/Library/
Logs/hakim/` (like backup). `health_check.py` now searches BOTH `~/Library/Logs/hakim` and
`~/Documents/…/logs` for job logs. **Proven via launchd:** morningbrief exit 0 (whisper composed,
queue=19), health exit 0 ("all systems ran this week"), **restore-drill exit 0 — RESTORE DRILL
PASSED, ledger 280/280 journals restored into a throwaway Postgres**. The backup guarantee is now
end-to-end real: it runs, and the restore is proven. Fleet: backup · backup-trigger · restore-drill
· health · morningbrief · sms-capture all exit 0.

**Offsite / NAS (item D) — CONFIRMED GAP, capability built:** the repo is on
`/dev/disk3s5` = the **Mac's internal disk**, NOT a symlink, and **no NAS is mounted** — a dead Mac
loses ledger + backups together. `backup.sh` now rsync-mirrors the repo to `$HAKIM_NAS_REPO` when
set/mounted (honest log + amber `/settings` warning when absent). **Hisham action:** mount the NAS,
set `HAKIM_NAS_REPO` (e.g. `/Volumes/NAS/HAKIM/restic-repo`) in `com.hakim.backup.plist`, reload —
the offsite mirror then runs every night automatically.

## 🎯 Money Pro Comfort Wave (9 Sep) — branch `feat/moneypro-comfort`
Replicated Money Pro's *interactions* in the HAKIM/Rasool dark system (look stays HAKIM,
behaviour becomes Money Pro). Full audit of Money Pro's 5 tabs + manual → **20 of 22 items
shipped**, 2 deferred with named unlocks (BLOCKED.md). All verified via 2400px screenshots.
- **Categories (`/categories`, rewritten):** show ALL categories incl. zero-spend (dimmed, `0`,
  never hidden); **Rows ⇄ Circles ⇄ Budget** view toggle (persisted in settings `cat_view`);
  Money Pro circle-fill (spent/target, over=rose ring, no-target=plain ring); subcategory **drill**
  modal; type-to-filter box. `/api/categories` rewritten: universe = all mains, roll-up subs onto
  parents, periodic + income targets, parent target = Σ children.
- **Subcategory hierarchy (item 3):** `data/category_tree.yaml` is OURS (presentation truth);
  Firefly stays flat. Manage → **Hierarchy** tab: add/rename/delete sub + **drag-to-reparent**
  (moves real txns by renaming/merging the flat `Parent: Sub` Firefly category). Endpoints
  `/api/tree/sub_add|sub_delete|sub_rename|reparent`.
- **Icons (item 4):** curated **local line-icon library** (10 sections, no CDN) + **custom photo**
  upload cropped to circle → `data/category-icons/` (mounted volume, not baked) served at
  `/data/category-icons/`. Emoji stays fallback. Icon picker modal.
- **Budget (items 6/A/J):** summary pills (income/expense/net planned), spent-vs-target bars,
  **periodicity** weekly/biweekly/monthly/quarterly/yearly, **income targets**, Total=income−expenses.
  Manual only (AI proposals + rollover → BLOCKED, need surplus history).
- **Accounts (item 5 + F):** **drag-reorder** (persists in rail/pickers/all-accounts,
  `data/account_order.yaml`); **hide (≠close)** — out of active views, balance kept, faded+Unhide,
  `data/hidden_accounts.yaml`; **merge-first** delete (Hide button + merge leads the flow).
  **Other Assets / Other Liabilities** groups (`other_asset`/`other_liability` types →
  `data/account_kinds.yaml`) → **net worth now whole** (was liquid-only). Endpoints
  `/api/account/reorder|hide`.
- **Reports (NEW tab `/reports`):** 7 types (Income&Expenses · Net Worth · Cash Flow · Debt ·
  Assets&Liabilities · Transactions · By Person; Projected Balance omitted=forecast-blocked).
  Controls: date presets incl. **Hijri month** (`/api/hijri/current`) + custom, account/category
  multi-select, txn-type, person, **class**, group-by. Styles bars/line/pie/table. Export
  **CSV+PDF+QIF**. **Saved reports** (`data/saved_reports.yaml`). `/api/report` + `/api/report/export`.
- **Goals (NEW tab `/goals`):** save-toward-X (existing balance counts) / pay-down-card-Y (paid
  since baseline); progress from REAL live balances; no coaching/projections (blocked).
  `data/goals.yaml`, `/api/goals` + `/api/goal/add|delete`.
- **Desk card:** **classes** Personal/Business (`class:` tag → report filter) · **reconciled** flag
  (`reconciled` tag, subtle ✓ in rows, filter, + **cleared vs available** balance in the account
  manager) · **attachments** viewable (`/api/txn/{id}/attachments` + `/api/attachment/{id}/view`
  proxy) · **type-to-filter** category picker · cross-currency **received-amount** override (already
  built) · planned-vs-actual **overlay line** on the cash-flow chart.
- **Deferred (named unlocks, BLOCKED.md):** **G** liability-payment interest/principal split ·
  **L** asset buy/sell entry types — both mint linked money-movement transactions, so they ship in
  one focused money-write micro-wave with balance-reconcile + undo tests, never rushed. Present
  value low: Tawarruq cost already captured as imported line items; Other-asset accounts already
  fundable via normal transfers.

## 📘 Intelligent-layer roadmap → `HAKIM_Finance_Blueprint_v1.1.md`
The full feature map (Dashboard, Budget engine, Safe-to-spend, Debt coach, Forecast,
Zakat, etc.) lives in that blueprint, built in **waves with HARD gates**. **Gate G0
(before ANY wave):** Sarah imported · queue ≈ 0 · cash/safes counted · 3–4 normal weeks
lived. Nothing starts until Hisham says "build Wave N". **Wave 1 = the Dashboard**
(read-only reading layer, separate surface from the truth-desk; constellation lives here).
**Wave 1 v1 SHIPPED (8 Sep):** `review-ui/dashboard.html` at **`:8001/dashboard`** (📊 link in
desk header). Read-only `/api/dash?month=` computes from the ledger: cash position (per-currency),
net worth, card debt, month statement line (in/out/net/count), spending-by-category bars,
by-person, top merchants, day-of-week chart; month selector. HAKIM-OS glass tiles + the
**constellation background** (its home). Numbers real but **provisional** (banner says so) until
G0. Next v1.x: Sankey, Hijri calendar, net-worth trend, drill-through to desk. Hisham uses it
~2 weeks before Wave 2 (real tiles chosen by the questions he actually asks).
**Dashboard v1.1 (8 Sep) — app shell + design language:** persistent **left rail** shared by
Desk + Dashboard (HAKIM wordmark · 📊 Dashboard / ⌨ Desk with active-highlight · dimmed
"coming in waves" placeholders Debt-Coach/Forecast/Zakat · system status SMS-LIVE/queue/
`FINANCE · ALL SYSTEMS NOMINAL`/clock at the bottom — header decluttered). Content
viewport-centered on wide screens (rail floats over the left margin), offset on narrow.
Design language adopts **Copilot category cards** (icon chip + per-category accent colour +
bar), **YNAB weight** on hero numbers, Monarch hierarchy — HAKIM's glass/mono/constellation
stays the skin. **Merchant names never raw strings** (`merchant_display`: counterparty →
SADAD-biller/"SADAD payment" → cleaned). **Honest small-data**: <10 txns/month → "N txns · N
days in — sharpens as the month fills" instead of broken charts. Verified both at 2400px.
**Design v2 + App Shell (8 Sep):** warm neutral-dark palette (`#16181d` page / `#1d2026` cards /
`#2a2e36` hairlines) replacing the cold navy; **gold `#e8b95a` = HAKIM identity only** (✦ wordmark,
active nav/tab, Review-Mode btn), **teal `#4fd1a5` = positive money**, **red `#e05252` = alerts
only** (backup-failed), **amber `#c9a15f` = debt/card balances** (net worth negative renders neutral
white, not giant red). Two fonts: JetBrains-Mono numbers + system/SF-Pro body. **Left sidebar v2
(both pages, `/api/rail`):** ✦HAKIM+FINANCE · Dashboard/Desk(queue badge)/Calendar(stub) · **ACCOUNTS
live balances** (cash + cards amber) each **clickable → Desk filtered by that account** (`?account=`)
· Coming section · bottom status SMS-LIVE/queue/**backup ✓ or ⚠ BACKUP FAILED (red)**/clock. **Dashboard
v2:** time-aware greeting, **net-worth hero + Maybe-style area line chart** (`nw_series`, 1M/3M/ALL
range chips, +Δ this month teal) · cash + **card-debt tile shaped like a card** w/ clickable last-4
chips · statement strip · **Copilot category rows** (colored icon pill + bar) clickable→Desk-by-category
(`?category=`) · **merchants w/ initials avatars** (clean names, never raw codes) · **Upcoming payments**
(Firefly bills, honest empty) · **Data-completeness tile** (exact %, replaces vague "provisional") ·
person + day-of-week. All read-only; every click-through navigates to the Desk. Verified Dashboard +
Desk + account-filtered-Desk at 2400px.
**v2.1 + A0 — Rasool layout replication (8 Sep, final design round):** goal = mirror Ghulam
Rasool's "Finance Dashboard Dark theme" (Dribbble) layout/rhythm/anatomy on the real ledger,
gold identity kept, read-only. **Palette harmony:** page `#101114`, teal-tinted card surfaces
`#1c2124`, nested `#232b2c` (3 elevation steps); gold identity-only. **Dashboard:** top bar (title
+subtitle · search pill · month selector · calendar · bell w/ amber dot when queue>0/backup-failed ·
✦ avatar) · **4 quick-nav tiles** (Review queue/This month/Cards/Cash, live numbers, alt tones) ·
**two-zone grid** (main 8fr / right rail 4fr, max-w 1600) · net-worth hero + **real SVG chart**
(Y-axis ticks+gridlines, X date labels, **hover crosshair + tooltip chip** "date · SAR · ▲Δ", teal
line+area, latest dot, 1M/3M/ALL re-render axes) · statement · category rows + merchants · person +
**day-of-week bars** (today highlighted) · right rail = **physical card stack** (SABB teal-green /
SNB deep-blue two-tone, last4, click→Desk) + Recent activity + Upcoming + Data-completeness. **Row
anatomy (Desk + dashboard):** avatar → name → meta(1-line, refs demoted) → amount → status; **red
"?" retired** (→ direction icon; To-review = amber "· review" dot); **money typography everywhere**
(`mm()`/`m()`: SAR + decimals at 60% muted). NB: bank **logos = brand-colored initials avatars +
two-tone card colors** (self-contained) rather than SVG files in `/assets/logos/` — real SVGs can
drop in later behind the same fallback chain. Self-check passed: 24px rhythm · 14px radius · 3
elevation steps · chart axes+gridlines+hover · money-typo everywhere. **Design chapter closes here
until Sarah + queue-zero + cash count.**

**Option A Rasool palette + POLISH 2 (8 Sep):** full navy/mint reskin across Desk + Dashboard —
page `#0D0F16`, card gradient `#1B1F2C→#151823`, **mint `#72D5C8` = all accent roles**, **gold
retired to the ✦ spark glyph ONLY** (HAKIM wordmark white), white tooltip chips (`#FFFFFF`/`#0D0F16`).
**Directional money colors** (glow=attention, color=direction): income mint · **expense dusty rose
`#D98A93`** · transfer lavender `#9BA3C9`; **alert red `#E05252` reserved for failures only** — fixes
the Who-tab alert-red scream. Muted at rest, full saturation on hover; color on amounts + left accent
line only, never row floods/names. **Real credit-card face** (EMV chip · contactless · embossed
masked number · card-holder · balance · sheen · ornament circles · 1.586 aspect) replacing the flat
rectangle. Desk **queue strip** now colored by transaction direction. Verified at 2400px.

**Git repo initialized (8 Sep):** `git init` with a strict `.gitignore` — `.env`, `data/`, `logs/`,
`inbox/`, `statements-archive/`, `hakim-brain/`, `*.db`, virtualenvs all excluded. Only code + config
+ docs versioned. Verified no secrets/PII staged before the initial commit.

**Calendar SHIPPED (8 Sep, under logged build-freeze override — owner's decision, Sarah pending):**
`review-ui/calendar.html` at **`:8001/calendar`**, sidebar item live. Read-only `/api/calendar?month=`
returns per-day net/in/out, types present, review flag, and full day transactions, with **Umm al-Qura
Hijri dates** (`hijri-converter` lib; verified: 8 Sep 2026 → 26 ربيع الأول 1448). Sunday-start month
grid (Gregorian + Hijri per cell, day-net in directional color, direction dots, today ringed, amber
review dot); **day panel** (in/out/net + row anatomy); writes route to the Desk (`/?add=YYYY-MM-DD`
pre-dates Quick-add · `/?txn=ID` opens the card); honest zero/sparse states. Header shows Gregorian +
Hijri month(s). Self-check passed. **Buildable-now ladder:** Calendar ✓ → Categories → Recurring →
Morning brief → Quick-add math; then the data debt (surplus/normal-weeks/Sarah) comes due.

**Categories SHIPPED (8 Sep):** `review-ui/categories.html` at **`:8001/categories`**, sidebar live.
Read-only `/api/categories?month=` (or `all`): per active category → month total, count, **3-month
trend sparkline**, **% of month's spending** (proportional bar in the category's color). Summary strip:
total spend · active count · biggest · **vs-last-month delta in direction-of-*good*** (rose if spending
grew, mint if it shrank). **"To review" pseudo-row pinned on top** — the uncategorized bucket refuses
to hide (Aug: 29 items / SAR 144k, larger than all categorized spend; that row → 0 is the Big Review's
scoreboard). Income categories render mint. Click row → Desk `?category=` filter (verified). Honest
zero/sparse states; no zero rows. Self-check passed; 2400px Aug + click-through verified.
**Categories v1.1 (8 Sep) — layout + right rail:** killed the long table-rows (hollow at 2400px) →
**two-zone** (main 8 / rail 4). Main = Copilot-style **2-col category cards** (icon+name, big amount,
full-width % bar in the **category's own color**, wide sparkline ~240px). Rail = **donut** (category
colors, total centered, white hover chip name+amount+%) → **Movers this month** (top 3 by Δ vs last
month, direction-of-good; hidden on all-time) → **least-used category**. Fixes: sparkline draws only
with ≥3 real months (else omitted — Aug window incl. pre-ledger June → suppressed, not a false
drop-to-zero); all-time summary shows **monthly average** not a dash-stat. Self-check + 2400px Aug &
all-time (donut hover) verified.

**Recurring SHIPPED + v1.1 (8 Sep):** `review-ui/recurring.html` at **`:8001/recurring`**, sidebar live.
Firefly **bills = source of truth** (read-only). `/api/recurring` + shared `bills_view()` projects each
active bill's **next-due** (computed from anchor date + repeat_freq — Firefly's next_expected_match was
empty), monthly-normalized amount, best-effort name-matched "paid". **Honest-amounts doctrine:** the 20
bills all carry placeholder `1.00` → shown as **"set amount"** (dashed amber link → Firefly bill edit),
never fabricated. **Dashboard Upcoming now reads the same projection** (one source, two surfaces).
**v1.1 two-zone:** main = tightened rows + category-colored icon pills; rail = **next-30-days timeline**
(1 Oct cluster) · **completion ring** (0/20 amounts, Open-Firefly) · **monthly-by-category** (ghost until
amounts) · **annual cost** (ghost). Ghost cards never fake numbers; auto-light as amounts are filled
(proven via client-side sim — no write to Firefly). **Human task surfaced: fill the 20 real amounts.**

**Two-zone completion — Calendar + Desk (8 Sep, house-rule rollout):** **Calendar** — grid stretched to
fill the main zone (bigger cells), **day panel sticky + state-aware** (empty day → Hijri + "no txns" +
**bills due today** from the bills projection + last/next activity, instead of a void), **month summary
footer** (in/out/net/txns + busiest-day chip), weekend (Fri–Sat) tint. `/api/calendar` now projects
active bills onto their due days. **Desk** — 8/4 two-zone; new **work-tool rail**: **This-session** ring
(queue count + SAR to cover + Review Mode) · **Biggest first** (top-3 by amount → scroll) · **By account**
(queue counts → filter) · **Recently resolved** (undo-drawer data + undo link). Queue strip unchanged.

**Morning Brief SHIPPED (8 Sep) — the whisper layer, HAKIM speaks first:** `scripts/morning_brief.py`
+ `launchd/com.hakim.morningbrief.plist` (07:00 Asia/Riyadh daily; `BRIEF_HOUR` const documents it) +
`Makefile` (`make brief` / `brief-dry` / `brief-install`). New `/api/brief` endpoint composes everything
from the same ledger sources as the dashboard (one call, no new pipeline): greg+**Hijri (Arabic-Indic)**
date · yesterday out/in/net + count (or "quiet") · cash + card debt · queue (omitted when 0 — silence is
the reward) · next bill (amount only if real, never the `1.00` placeholder). ≤6-line ntfy push. **Failure
is loud** (fallback "brief failed" push, high priority) and **wired into the weekly health line** (JOBS +=
brief.log). Read-only, one-way. **Human task: set `NTFY_URL`** to a private topic in the plist to deliver
(currently unset → composes but doesn't push; script says so honestly). Agent loaded; dry-run verified.
**Buildable ladder: Calendar ✓ Categories ✓ Recurring ✓ Morning brief ✓ → Quick-add math (last rung).**

**INCIDENT + FIX — main column clipped under sidebar (9 Sep):** the Desk main column rendered under
the fixed 222px sidebar for viewports ~1300–1884 (header/tabs/rows clipped on the left, dead gutter on
the right). **Root cause:** the two-zone completion (commit `2027a57`) widened the Desk `.app` from
820→1440px but left the old `@media(max-width:1300px)` sidebar-offset breakpoint — so `margin:0 auto`
centering pulled content left under the sidebar until the viewport was wide enough (≥1884) to clear it.
The other pages carried a smaller latent version (1860 breakpoint vs their max-widths). **Fix (shell-
level, all 5 pages):** replaced the centering + media-query with a bulletproof
`margin-left:max(222px, calc((100% - MAXW)/2)); margin-right:auto` — content is centered when there's
room and pinned just right of the sidebar when not; never overlaps at any width. Verified no overlap /
no h-scroll at 2400/1884/1600/1440/1120 on Desk, Dashboard, Calendar, Categories, Recurring.

## 🔨 Mega-brief execution (9 Sep, branch `feat/calendar`)
- **0 ✓** Blueprint v1.2 changelog appended.
- **1 ✓** Morning Brief (built 8 Sep, a73067b). On-phone delivery proof → BLOCKED.md (needs NTFY_URL + phone).
- **2 ✓ (core)** Money Pro Entry DNA on the Desk: **keypad math** (safe evaluator, `50+30×2 = 110`
  live preview, +−×÷ C ops), **payee + reference** fields (payee → description/counterparty, ref → notes),
  **⌘K amount search** (numeric query → "Find transactions = SAR X" → All filtered by amount, clear chip).
  Split-by-category + local FX (`fx_rates.yaml` + `convert()`) already existed. **Deferred sub-item:
  cross-month split (⑂ marker)** — a multi-transaction+link feature; noted for a dedicated pass.
- **3 ✓** Calendar season shading: meteorological season cell tint (winter/spring/summer/autumn) +
  **Umm-al-Qura markers** (🌙 Ramadan m9 · 🕋 Hajj m12 d≤13 · ✦ Eid m10 d≤3) + legend + weekend stripe.
  Verified March 2027 (رمضان – شوال 1448) renders the badges correctly.
- **4 ✓** Exports: `scripts/export_ledger.py` + `make export` → `~/Documents/Hakim/exports/` dated files:
  **CSV** (full per-split detail, UTF-8-BOM) + **one-page PDF summary** (hand-rolled, stdlib-only, no
  external libs — valid PDF 1.4, renders in Chrome). Ran: 270 txns, in 165,230 / out 144,469 / net
  20,761. `exports/` added to .gitignore (ledger data never enters git).
- **5 ◐** Responsive 390px pass: added the ≤900 mobile rule (sidebar → 56px icon-only, account rows hidden)
  to Calendar/Categories/Recurring (were missing it) + ≤480 phone tweaks; fixed grid blowouts via
  minmax(0,1fr)/min-width:0 and the credit-card number wrap. **Verified hscroll=0 at 390px on all five
  pages.** Tailscale phone access → BLOCKED.md (needs Tailscale up on Mac+iPhone; tailnet URL is yours).
- **6 ⊘ deferred (rationale):** custom category icons (assets/category-icons/). The emoji icon system is
  already self-contained and working; a bespoke SVG set + static-asset serving is asset-heavy / low
  marginal value / adds container surface — better as a deliberate design pass on explicit request.
- **7 ✓** Per-account balance drill-down: `/account` page + `/api/account_series` (running balance
  reconstructed from the ledger, anchored to the live Firefly balance). **Full chart anatomy**
  (Y-gridlines+labels, month X-axis, area+line, hover crosshair + white tooltip), current/net-change/
  opening stats, recent-activity rail. Dashboard rail accounts drill in here. Verified Hisham SNB main
  (104 txns, hover '22 Aug 2026 · SAR 758').
- **8 ✓ (beta)** Spending heatmap: `/heatmap` + `/api/heatmap`. GitHub-style daily-intensity grid (rose
  scale, Sun–Sat rows, month labels), hover (date · SAR · txns), legend, rail stats (total/active-days/
  busiest/avg). **Beta-tagged honestly** (only 60 days of data → "reads more like a sketch"). Reached
  from Categories ("🔥 heatmap →").

## 💳 Card networks + self-service card management (9 Sep)
**A ✓** Networks verified by Hisham → `data/card_networks.yaml`: 5019 visa · 5158 mastercard · 4331
mastercard · 6510 mastercard · 8381 visa · 437x unknown (clean face). Card face renders the correct mark.
**B ✓** Manage-cards (Desk `openAccounts`/`acctActions`, already doctrine-correct — extended):
- Add card: last-4 + **network** (verified) + bank/currency/opening; writes the Firefly account (one owner).
- Per-card **network dropdown** ("VERIFIED, NOT GUESSED") → `/api/card/network` (audited write).
- Balance correction posts a proper adjustment entry (existing `correctBal`); Edit; **Close/archive**
  (hides, keeps history, final-transfer of remaining balance); **delete only if empty**, else move-history-
  then-delete or purge-with-typed-name-confirm (never orphans ledger entries); Reopen.
- `/accounts` view shows a **"closed" badge** (archived accounts, excluded from active subtotals).
- Self-check passed: added TEST CARD •9999 → set network mada → verified → deleted (cleanup).

## 🎛️ Operator control layer — "Full Control" wave (9 Sep)
1 ✓ Sidebar **Accounts ✎ edit** (dashboard) → opens the Desk account manager (`/?manage=accounts`).
2 ✓ **Categories management** (/categories → **Manage**): add · rename · icon (emoji) · colour · **merge**
  (re-tag txns + delete, counts+confirm) · delete (→ uncategorized, never orphaned). Firefly categories API;
  icon/colour in `data/category_meta.yaml`.
3 ✓ **Budget targets (manual)**: per-category monthly target (`data/category_targets.yaml`) + **actual-vs-
  target bar** on cards (over→rose). No coaching/projection — engine stays in BLOCKED.md.
4 ✓ **Account merge**: existing move-history-then-delete relabelled "Merge into another account" (typed
  confirm, counts shown; Firefly has no native merge → audited move+close).
5 ✓ **/settings** (`/api/settings`, `data/settings.yaml`): theme (dark; light shown, disabled), language
  (en; Arabic shown, disabled — no half-translation), **default landing** (works via `/home` redirect).
  Only switches that work. ⚙ in dashboard topbar + sidebar.
6 ✓ **Control audit → CONTROL.md**: every entity's add/edit/delete/merge status. Gaps surfaced:
  **Bills/recurring** (managed in Firefly UI — biggest remaining gap, recommend next), merchants/payees
  (partial), person/tag list (deferrable).
7 ✓ Roadmap appends: Arabic localization · light theme · customizable dashboard.
New card-mgmt writes are audited; card networks in `data/card_networks.yaml` (verified, not guessed).

## 🖥️ Dashboard polish round 1 (9 Sep, from Hisham's page-by-page review)
1 ✓ Tile truth: "This month · net" (net big + in/out sub) · "Card debt" (−amber) · "Available cash".
2 ✓ Global **⌘K search palette** (`/api/search`): pages · accounts · categories · transactions (merchant/
  amount/desc) → routes to the right surface. Injected into all reading pages; Desk keeps its command palette.
3 ✓ **/accounts** grouped view (Banks/Wallets/Owed-to-me/Cards + subtotals + net-worth) via `/api/accounts_grouped`;
  sidebar "All accounts →"; rows drill into /account.
4 ✓ **Card-network truth fix** (flag-don't-guess): verified `network` from `data/card_networks.yaml`
  (last4→visa/mastercard/mada); unknown → clean face, NO mark. Stopped inferring network from the name.
  **QUESTION FOR HISHAM: confirm each card's network (below).**
5 ✓ Category header "Top N · {month} · View all →". 6 ✓ Recent activity relative dates ("2mo ago").
7 ✓ Sign+color audit: category/merchant/person amounts − in expense rose. 8 ✓ Day-of-week: hover totals,
  max labeled (rose), sort toggle (Mon–Sun / high→low). 9 ✓ **Cash-flow chart** (monthly income mint vs
  spending rose). 10 ✓ Tile delta (vs last month %, omitted when no prior month). 11 ✓ **Alerts strip**
  (backup failed / SMS stale / bills missing amounts / queue) — links to fixes, hidden when clear.
12 ✓ Roadmap: customizable dashboard (Monarch pattern) appended to blueprint.

## 🏠 House layout rule (locked 8 Sep — applies to every full page)
**8/4 two-zone grid everywhere** (main 8 / right rail 4), like the Dashboard. The **right rail carries
derived insight, never filler.** Rail cards **may render honest ghost states** ("waiting for amounts")
but **never fabricated/placeholder numbers** — they light up automatically when the real data exists.
Applied to: Dashboard, Categories (donut/movers/least-used), Recurring (timeline/completion/by-category/
annual), Calendar (grid/day-panel). New pages inherit this without re-deciding.

## Live services (docker compose)
Open WebUI :3000 · Homepage :3001 · Firefly III :8080 · Finance agent :8000 ·
PostgreSQL + Redis (internal) · Ollama on host (qwen2.5:7b-instruct, swappable).

## Node Zero — the brain (`hakim-brain/`) — COMPLETE
`hisham.md`, `businesses.md`, `family.md`, enforcement `README.md`. Doctrines:
one-system-per-domain · what-stays-his (never delegated) · confirm-before-editing
ground truth · access rules per person.

## Finance (agent #1) — LIVE, personal-only, read-only
- Talks in Open WebUI as `hakim-finance`. Read-only, flags-don't-guess, append-only log.
- Answers cash position (across all accounts, per currency), spending, income,
  breakdowns, categorisation. Defers MENTCO/trading/factory to their agents.

## Firefly III — v2 structure + REAL DATA imported
Built by `scripts/build_structure.py` (idempotent). Currencies SAR (default)/EGP/USD/AED.
~24 asset accounts (banks, wallets, safes, 6 ccAsset cards, Trading cash, receivable) +
"I owe" liability; 31 categories; 13 tags; 20 skeleton bills. Real transactions imported
from bank/card statements (see importer section below).

**Boundary decisions (6 Sep):** Trading = asset account "Trading cash (HISSAR)"
(cash only; transfers in/out personal, positions/P&L stay in HISSAR). Factory =
expense category "Capital contribution: Factory". Cards = ccAsset assets (see below).
Agent answers personal sides; defers trading-performance / factory-business.

### ⏳ Still open (non-blocking, real data — not to be invented)
- Physical wallets/safes counts · Bank Misr (Egypt) statements · Trading cash balance.
- Bill amounts + due dates (esp. government renewals → expiry alerts).
- Sarah SNB Mastercard •437x last-4 (placeholder) · dedicated `FIREFLY_ADMIN_TOKEN`
  (still empty; using FIREFLY_PAT fallback) · rent-vs-own confirm.

## Statement importer (Brief 03) — BACKFILL DONE ✅ (7 Sep)
Real import applied: **273 transactions** (254 plain + 19 transfers) from 8 files,
≥1 Jul. Rerun writes **0** (idempotent; 47 overlap dupes between the two SNB files
collapsed correctly). All account balances reconcile to reality (banks 0.00,
wallets/Travel exact, 5 cards show true debt as negative ccAsset balances). Finance
reports cash position **SAR 107.32**. Review queue: **153 To-review, 101 merchants**
(`data/review_queue.md`).

**Card model decision:** Firefly v6.6.6 API rejects transfers to a liability, so the
6 credit cards are **asset/ccAsset** (charges push balance negative = debt; payments
are transfers). "I owe" stays a liability. Agent excludes ccAsset from cash position.
`external_id` carries a **per-file occurrence index** (distinguishes genuine same-day
duplicates while keeping overlapping exports idempotent).

**Transaction-type fix + backfill (7 Sep):** SNB files' column C (the type — "SADAD
Payment", "POS purchase - Apple Pay", "Incoming internal transfer"…) used to be dropped.
Now stored descriptions are composed `type — reference` + a `txn-type:<T>` tag (and
`fx-candidate` for international POS). `external_id` still derives from the raw reference
ONLY, so this changed **no** ids — reruns stay idempotent (254/254 already-imported, 0
new). SABB files have no type column. `scripts/backfill_descriptions.py --apply`
re-derived all ~280 from source: **96 descriptions + 56 tags upgraded**, only where the
description was still the untouched raw reference (never clobbers a human edit) and tags
only on un-answered items (answered = description-only). Idempotent; `logs/backfill.log`.
Rows now read *"SADAD Payment — 001-05032…"* instead of a bare number.

Still open (non-blocking): physical wallets/safes counts, Bank Misr (Egypt) statements,
Trading cash balance. Not yet built (brief: "after backfill works"):
`scripts/apply_reviews.py`, `scripts/import_watch.py` + launchd.

## Brief 04 — matcher v2 (done) + SMS capture (live built; wallets monitoring-now)
**Part A — cross-run transfer matching (DONE):** `import_statements.py` proposes fusions
between rows and existing ledger txns (equal |amount|, opposite dir, ±3 days, diff
accounts; skip confirmed/self); `--fuse-existing` fuses (delete legs → one transfer,
before/after logged, external_id preserved). **Fused 3 real internal transfers**
(20,000 & 4,000 SNB↔SABB, 1,500) — 24k of own money that had posed as spending;
To-review 144→138. Sarah-file acceptance runs when her files land in inbox.

**Part B — SMS capture (`scripts/sms_capture.py`, HOST, FDA):** chat.db read-only,
attributedBody decoder (typedstream), SENDER_MAP + CARD_MAP, per-template parsers, hard
filters (decline/OTP/ad/login/notice), rules-first categorisation, rowid dedupe index.
- **Wallet backfill finding:** SMS history is NOT reliably reconstructable — STC/D360
  back-solve to *negative* openings (missing messages); barq had 1 unexplained gap (400)
  + parser edge-cases. So all 3 wallets set to **monitoring-now**: opening = current
  balance (56.14 / 25.15 / 20.03) dated 7 Sep, live capture forward. Balances exact.
- **Live mode** (`--live`, incremental via `data/sms_index.db` watermark): wallets +
  SNB/SABB **known** templates import (tag `sms`); unknown bank templates →
  `logs/sms_unknown.log` (monthly review), never the Review UI; filters dropped.
- **launchd** agent `launchd/com.hakim.sms-capture.plist` (every 2 min) + `launchd/README.md`
  — NOT loaded yet: needs Hisham to grant Full Disk Access to the venv python + `launchctl load`.

**AWAITING HISHAM:** grant FDA + load the launchd agent (see launchd/README.md), then a
live test purchase. Decisions applied: (1) wallets → monitoring-now (backfill unsound);
(2) barq breaks reported (1 unexplained); (3) SNB/SABB known-only + unknown→log; (5) fused.

## Entry & Review Desk v2 (Brief 03c + addendum) — LIVE at :8001
Full rebuild of `review-ui/` into HAKIM's truth-desk (data entry + review + confirm
ONLY; **no charts/analysis** — that's the future intelligence layer). Polished dark,
card-based, colour language (GREEN in / RED out / BLUE transfer + stripe + arrow),
RTL-safe, big tap targets (phone via Tailscale).
- **Tabs:** Needs answer · All (search desc/note/account, filters, infinite scroll,
  unverified-only) · Quick add (Expense/Income/Transfer, keypad, account pickers w/ balances).
- **Shared card:** direction-first identity; direction-matched **two-step category**
  (Main→Sub, stored "Main: Sub", recents float up, `data/category_tree.yaml`); note;
  person/context tags (optional, "no tag = normal"); **transfer BOTH ways** (to/from,
  pickers show balances); smart suggestions (ATM→Hisham Wallet, card→transfer, SADAD→cat);
  links (transaction-links API); receipt attach (Firefly attachments); **trust dots**
  ⚪imported/🟡proposed/🟢verified + Verify ("Reviewed by Hisham, <date>", tags).
- **Accounts sheet:** grouped live balances + **Manage** (add / edit / **close** (default;
  requires final transfer if balance≠0; hidden from pickers, history kept, reopenable) /
  **delete** (danger: move-history-then-delete, or purge w/ name-confirm; guardrail —
  accounts with >25 txns can't be purged, only closed) · balance-correct (logged)).
  Logs → `logs/accounts.log`. Cards created as ccAsset (matches importer).
- **Embedded AI bar** (every tab) → Finance agent :8000, slide-up panel, read-only,
  graceful when down.
All writes Hisham-initiated + logged before/after (`logs/review.log`); importers never
disturb verified items.
- **Addendum-2 (built+tested):** cross-currency transfers (Firefly `foreign_amount`,
  each account in its own currency); foreign manual entries (🟡 proposed, "pending bank
  confirmation") + importer **reconciliation** (`try_settle`: a bank row within 5%/±3d
  settles the 🟡 to the true figure, keeps note/tags, → imported-confirmed); **split
  editor** (native Firefly split withdrawal, remainder-must-be-0, `group_title`); FX in
  `data/fx_rates.yaml` (editable, inline rate entry when missing → offer to save).
- **Universal currencies:** picker offers all (favorites SAR/EGP/USD/AED pinned),
  `data/currencies.yaml`, any code enabled/created on demand in Firefly (`ensure_currency`).
- **HAKIM OS restyle:** cyan (#22d3ee) system accent, JetBrains-Mono numerals, angular
  corners, glow only on verified dot / active tab / AI spark; AI bar = slim pill +
  slide-up panel (Esc/tap-out), no scanlines. No charts.
Acceptance verified via API (transfer-from, verify→🟢, 2-step quickadd, search-by-note,
close/reopen/move-delete guardrails, cross-currency transfer, foreign 🟡, settle, split).
- **Date-range filter (7 Sep):** All + Needs get a range control — preset chips (This
  month / Last month / 30d / 90d / This year / All) + **Custom** (from/to pickers +
  jump-to-day); active range = dismissible chip; combines with search/account/unverified.
  Result line "N txns · SAR in / SAR out" (counts only — `/api/transactions` returns
  `sum_in`/`sum_out`, no charts). Range is a **URL param** (`?from=&to=`, linkable/
  bookmarkable). Default = All while the ledger is <~6 months old, **auto-flips** to This
  month past that (`bootstrap.ledger_start`). Rows now show the **transaction type
  prominently, reference beneath** (desc split at " — ").
- **SADAD biller map (7 Sep):** rows carry `biller` (3-digit code) + `biller_name`; an
  unnamed biller shows a "name this biller" input in the card → `POST /api/sadad` saves
  to `data/merchants.yaml` `sadad_names:` — named once, named forever (like the merchants
  map). Display then reads "SADAD Payment — Electricity/SEC".
- **Background (7 Sep):** flat dark replaced by a layered CSS atmosphere — depth-gradient
  vignette + ghosted HAKIM constellation starfield (~5%, drifts 90s, respects
  prefers-reduced-motion) + fine SVG grain (~2%) + one cyan aurora behind the title; cards
  get a soft shadow to sit on it. Near-zero cost, no canvas, text contrast untouched.

### Feature pass (7 Sep) — Review Mode · Counterparties · Undo · Batch · ⌘K
- **Review Mode** (green button atop Needs, or ⌘K): full-screen one-at-a-time stepper over
  the queue (respects the date range). Keyboard: **1-9** pick a category chip · **V** save
  & verify · **⏎** save · **S**/→ skip · **Esc** exit. Advances automatically after each
  write; "Review N/total" banner + progress. The surface for the big Sarah review.
- **Who tab** (Counterparties): `/api/counterparties` — People (person tags, count + net,
  tap → All filtered by that `tag`) and Merchants (most frequent, count + total spent, tap
  → All searched). Browsing not analysis, no charts.
- **Undo** (↶ header button): append-only ring `data/undo.json` (last 60), every undoable
  write snapshotted — `edit` (apply/verify → restore tags/category/notes), `create`
  (quickadd → delete), `convert` (transfer → delete new + recreate original w/ external_id).
  `/api/recent` + `/api/undo`; each undo is itself audited (never silent). **Round-trips
  proven:** apply→undo restored category; quickadd→undo deleted the txn. Split/balance-
  correct not yet instrumented (appear in `logs/review.log`, not the undo drawer).
- **Batch select** (☑︎ in All): multi-select rows → floating bar → Categorise (main-cat
  picker) or Verify 🟢 applied to all; reuses `/api/apply` + `/api/verify` per id.
- **⌘K palette:** command+search overlay (⌘K / Ctrl-K) — jump to any tab, Review Mode,
  Recent/Undo, Accounts, Ask Finance, range presets; typing offers "Search all for …".
  Arrow keys + Enter. Tabs are now **Needs · All · Who · Quick add**.

### First production incident (7 Sep) — Save hang, fixed + guarded
**Symptom:** answering an Uber *group* with Save & Verify hung the button, then the whole
desk stopped responding (`/health` 000, container Up but wedged). **Root cause:** a
self-deadlock — `add_rule()` (fires when "always apply to this merchant" is checked, the
Review-Mode default) called `audit()` **while holding the non-reentrant `threading.Lock`**;
`audit()` re-took the same lock → thread wedged forever → held lock starved every other
request. **Data integrity: perfect** — the hang was *after* all writes committed (7 Uber
txns categorised+verified, rule saved); nothing half-applied. **Fixes:** (1) `_lock` →
`RLock` (reentrant); (2) moved `audit()` out of `add_rule`'s lock; (3) `one_txn` returns a
clean 404 for a deleted txn instead of an unhandled 500; (4) global exception handler logs
+ audits every unhandled error and returns JSON; (5) frontend `postJSON()` wraps writes
with a 25s AbortController timeout — a failed/slow save now re-enables the button + toasts
("Nothing lost; try again") instead of hanging; (6) `openCard` skips a vanished txn in
Review Mode. **Proven:** the exact group+always+verify action now returns in ~0.8s with the
server still serving, and `rule_added` logs (add_rule completes). Test mutations rolled back
clean.

### HUD v2 restyle (7 Sep) — "chrome performs, reading surfaces stay calm"
Turned the futuristic dial up while keeping Arabic/text calm + high-contrast. **Glass:**
backdrop-blur on singular chrome ONLY (header, sheet) — never per-row (60fps law);
translucent rows keep the green/red/blue left accent. **HUD frame:** fixed viewport border
with edge tick-marks + corner brackets (`#hudframe`). **Instrument strip** (header): live
clock · `● SMS LIVE/IDLE` (from `/api/status` ← `health.json` SMS heartbeat) · `QUEUE nn`;
a running data-stream line under the header. **Footer:** `HAKIM · FINANCE · ALL SYSTEMS
NOMINAL` (red if degraded). **Chrome:** section labels `⟨ CATEGORY ⟩` cyan mono; active
card = pulsing cyan targeting brackets; amounts glow + count-up on open; **verify → HUD
sweep**; scanline texture ONLY on header / empty states / review-complete screen. All
motion 150–650ms + `prefers-reduced-motion`. **This is the design system the October
dashboard inherits.** Verified with headless-Chrome screenshots (list + open card).
**Background — settled FLAT + cache fixed (7 Sep):** the glass/constellation atmosphere ate
several rounds (whisper → wrong-band → unlit-wide-margins because gradients were px-sized).
Root cause of the "no change" loop turned out to be **caching**, not CSS: the desk had no
`Cache-Control` header and Hisham reaches it via a **Fastly tunnel** that served stale HTML
past ⌘⇧R. Fixes: (1) **deleted the entire `#atmo`/constellation/grain layer** — background is
now `html,body{background:#152230}`, flat slate, unbreakable at any width/scroll/device;
constellation banked for the dashboard. (2) `/` route sends `Cache-Control: no-cache,
no-store, must-revalidate` (+Pragma/Expires) so builds always reach the browser. Verify the
pipeline server-side: `diff <(curl -s localhost:8001/) review-ui/index.html`. Amounts flat
(glow only on verify sweep / active-card brackets / ● LIVE). **Design chapter closed.**

### Naming (final, 8 Sep)
The finance agent is **Finance**. "MAAL" is **retired** — purged from desk footer (`HAKIM ·
FINANCE`), docs, STATE, memory. Do not reintroduce.

### Morning batch (8 Sep) — provenance · New tab · badge fix · backup fix · calendars
- **Provenance** on every row/card (`prov`): captured-by (📲 SMS / 🏦 statement / ✍️ manual)
  + status by account class — SNB/SABB SMS "⏳ awaiting statement confirmation" → "✅ confirmed
  by statement" on the twin; wallets "✔️ SMS — final source"; statement "🏦 from statement".
  Filterable in All (source / awaiting-confirmed). Completes the triad: what · trust · how-it-knows.
- **New tab** — `/api/new?since=<last-visit>` (localStorage), auto-sorted vs needs-answer, badge count.
- **SMS badge fix** — was reading the WEEKLY `health.json`; now reads the real 2-min heartbeat
  (`logs/sms.log` last `live:` line). ≤5m ● LIVE · ≤10m IDLE+age · >10m amber, tooltip explains.
- **Backup fix** — nightly failed **exit 78** (fired on wake before Docker ready → no snapshot).
  `backup.sh` now waits for Docker (≤5 min) + writes `data/backup_status.json`; `/api/status` →
  footer `⚠ BACKUP NEEDS ATTENTION` if failed/stale (loud within a day). Manual backup ran; fresh
  snapshot exists. **The 03:15 job produced no snapshot last night — now fixed + surfaced.**
- **Calendar pickers** — Custom range = labeled From/To/Jump native date calendars, not spinners.

## Review UI (Brief 03b) — superseded by v2 above
`review-ui/` FastAPI service, Homepage tile, RTL-safe. Queue = live "To review" txns.
Two tabs: **Merchants** (grouped by digit-normalized key; answer → optional permanent
`merchants.yaml` rule) and **One-by-one** (تحويل/TRANSFER/AC TO AC/IPS/SADAD items,
individual). Card: category + person/context tags, or convert to transfer / owed-to-me
(delete+recreate keeping external_id), skip/back. All writes logged to `logs/review.log`;
transfer conversions log before/after. Writes are the ONE place category/tag PUT +
transfer delete+recreate are allowed (Hisham's explicit decisions).

Acceptance passed: UBER *TRIP ×7 → Transport & taxis + Hisham + rule; تحويل → transfer
to Sarah SNB main (one transfer, balances shift, logged); importer rerun 0 dupes,
converted items don't reappear. Note: transfer conversion logs BEFORE the delete so a
slow Firefly call can't lose the audit; httpx timeout 60s.

Next (Brief 04 territory): SMS capture feeds this same UI; `scripts/apply_reviews.py`
now largely superseded by the UI; watcher (`import_watch.py`) still pending.

## Backups & health (7 Sep) — proven, on rails
- **Restic** encrypted local repo `~/Hakim-Backups/restic-repo` (password file chmod 600,
  outside the project). `scripts/backup.sh` = Postgres (firefly+openwebui) + Firefly
  attachments + `data/*` + `hakim-brain/`. `scripts/restore_drill.sh` restores to temp
  and **proves** all three layers (rules, receipts, and the ledger restored into a
  throwaway Postgres with matching journal count). **Drill PASSED** (280/280).
- **Uptime Kuma** service on :3002 (Homepage tile) — real-time monitoring dashboard
  (first-run: create admin + add monitors for Firefly/agent/review-ui/etc.).
- **`scripts/health_check.py`** — the weekly health LINE (services up + launchd jobs
  last-succeeded freshness) → `logs/health.log` + `data/health.json`; set `NTFY_URL` for
  a phone push. Currently: **all green**.
- **launchd loaded:** `com.hakim.backup` (nightly 03:15) · `com.hakim.restore-drill`
  (Sun 03:45) · `com.hakim.health` (Sun 10:00) · `com.hakim.sms-capture` (every 2 min).
  Caveat: Docker Desktop must be running for the Docker-dependent jobs (backup/drill).

## ✅ WAVE M — COMPLETE (11 Sep 2026) — the twice-deferred, once-walled wave, sealed
The full asset & debt anatomy, every flow balance-proven. The closing proof list (11 flows):
1. **Loan paydown** — withdrawal asset→liability, principal+cost split; liability −100k→−97,222.22,
   cost→"Bank & fees: financing cost". `proof_ok`.
2. **BNPL purchase** — full expense once + liability + schedule; Tabby 0→−2,000, Zara booked once. `proof_ok`.
3. **BNPL installment discharge** — −2,000→−1,500 via the paydown shape, no double-count. `proof_ok`.
4. **Early settlement (with rebate)** — settle 49k on 50k principal → liability→0, cash net −49k
   (1k rebate back as income). `proof_ok`.
5. **Certificate payouts** — 100k @19% monthly → 1,583.33/payout, expected-income + maturity alert.
6. **Certificate Calendar dots + payout-matching** — 💰 on due dates, "received ✓" when a deposit matches.
7. **Lease-to-own + balloon** — car 100k, liability −84k (N×monthly+balloon), down −20k, balloon as
   named final item; `proof_ok`. Forget-proofing: dashboard amber-6mo/red-3mo + 🎈 Calendar dot.
8. **Metals buy/sell** — cash↔asset transfer, partial sale; buy 0→5,000, sell 5,000→3,000. `proof_ok`.
9. **Fund/ETF buy/sell** — same asset-trade shape. `proof_ok`.
10. **BNPL charge auto-matching** — Desk propose-link re-points an arriving charge to discharge the
    installment (never a 2nd expense); liability −2,000→−1,500, `proof_ok`.
11. **⑂ cross-month amortization** — 1,200 insurance ÷ 4 → Categories/Reports show 300/mo across the
    window; ledger keeps the single true entry; ⑂ marker + card action.
**G-split:** functionally covered by the loan/lease/BNPL "Record payment" (principal/cost split) —
a dedicated Desk manual-entry surface is logged as OPTIONAL polish in BLOCKED.md, not a gap.
Doctrine held throughout: HISSAR blind (balance+transfers only), equity = book value (M12), positions
FX-converted, restricted-vs-available honest, everything zakatable feeds the hawl base. Guide updated
same-commit across the wave. **Ladder now: Wave H → N+Z.**

## M2.4 — certificate Calendar dots + payout-matching (11 Sep 2026)
- **Certificate payout dots on the Calendar** — `calendar_data` now places each certificate's
  expected payout dates (💰 cell marker + a day-panel "Certificate payout (expected)" section, "as
  contracted"). Verified: NBE cert @19% monthly → 2026-10-01 shows +SAR 1,583.33. Lease **balloon**
  also gets its own dated 🎈 marker.
- **Payout-matching (visual)** — a payout shows **received ✓** when a matching deposit (±5%) landed
  that day, else "as contracted". Guide + committed already carry the income line.
- **HONEST — Wave M is NOT complete.** Remaining true closers: **BNPL charge-arrival auto-matching**
  (Desk propose-link) and **⑂ cross-month analysis amortization** (both genuine builds, not rushed).
  G-split is functionally covered by the loan/lease/BNPL "Record payment" (principal/cost split);
  a dedicated Desk manual-entry surface is the only polish left there. I will declare Wave M complete
  only when BNPL-matching + ⑂ are proven — per the standard set in M2.2. Two flows remain.

## M2.3 — lease wizard + asset buy/sell (11 Sep 2026) · 3 of 7 closers
Honest count: Wave M is NOT yet complete — 3 of M2.3's 7 flows proven this pass, 4 named for M2.4.
- **Lease-to-own wizard** (`/api/lease/setup` + Accounts "🚗 New lease") — creates the car in
  Other-assets at value, the lease liability at the **total remaining commitment** (N×monthly +
  balloon), books the down payment (transfer cash→car, no P&L pollution), and a schedule with the
  **balloon as a named final item**. **Balance-proven:** value 100k · down 20k · balloon 30k · 36×1500
  → car 100,000, liability −84,000, cash −20,000, financing cost 4,000, `proof_ok`. Openings dated at
  **signing (today)** not first-due — the banked future-date lesson, which this flow re-taught (first
  attempt showed car 20k / liability 0 because openings were future-dated).
- **Balloon forget-proofing** — `/api/balloons` + dashboard alert (amber ≤6mo, red ≤3mo). Pure
  dates+arithmetic, no advice.
- **Asset buy/sell** (`/api/asset/trade`) — cash↔asset transfer, partial sale supported; covers
  **L (metals) AND fund/ETF** buy-sell in one shape. **Proven:** buy 0→5,000, partial sell 5,000→3,000,
  both `proof_ok`. Surfaced as ＋/− on Holdings rows.
- Guide gained lease + buy/sell recipes. Tests cleaned.
- **Remaining → M2.4 (BLOCKED.md, named): BNPL charge-arrival auto-matching · G-split UI · ⑂
  cross-month · certificate Calendar dots + payout-matching.** Wave M closes when these 4 are proven
  — NOT claiming complete before then (the standard set in M2.2).

## M2.2 — early-settlement + certificate payouts (11 Sep 2026)
Two more cascade flows on the proven shapes; the papers evening is now fully powered.
- **Loan early-settlement** (`/api/loan/settle` + loan-detail button) — Hisham enters the bank's
  ACTUAL settlement figure (never computed). Discharges principal to zero + books the profit
  rebate. **Balance-proven:** settle 49,000 on a 50,000 principal → liability −50,000 → 0 (cleared),
  cash net −49,000 (paid 50k, 1k rebate returned as income). cost>0 → extra financing cost; cost<0
  → rebate deposit back to cash.
- **Certificate payout machinery** (`/api/certificates`) — expected payouts = principal × rate ÷
  frequency ("as contracted", arithmetic not forecast); next payout; **expected certificate income
  this month** (dashboard line); **maturity countdown + renew-or-collect alert 1mo before**
  (dashboard). Verified: NBE 100k @19% monthly → 1,583.33/payout, next 2026-10-01, 24mo to maturity.
- Guide gained certificate + early-settlement recipes. Test accounts cleaned.
- **Cascade remaining → M2.3 (BLOCKED.md, all named):** lease wizard+balloon+forget-proofing+endings ·
  BNPL charge-arrival auto-matching · fund/ETF buy-sell+distributions · G-split UI · L buy/sell ·
  ⑂ · certificate payout Calendar dots + payout-matching. Each a focused pass, no limbo.

## M2.1 — BNPL, balance-proven (11 Sep 2026) · the debt cascade begins
Rode the proven paydown engine into BNPL (Tabby/Tamara).
- **`/api/bnpl/purchase`** — books the **full expense today** (withdrawal source=provider liability →
  real category) + the debt + an equal-installment schedule. Fixes both lies of SMS-only capture:
  the item lands **once** at full price in its category (not N little charges), and the debt is visible.
- **Installments discharge via the proven `/api/financing/pay`** (principal=installment, cost=0) —
  never a second expense. Surfaced on the BNPL account detail (kind-aware: **New BNPL purchase** →
  schedule → **Record payment**).
- **Balance proofs (through the app):** purchase → liability 0 → −2,000 (`proof_ok`), Zara expense
  booked exactly once in Clothing; installment → −2,000 → −1,500 (`proof_ok`). Test cleaned.
- Guide gained a BNPL recipe. `/api/accounts` now exposes each account's `kind` (loan/bnpl/lease)
  so the UI shows the right setup.
- **Cascade remaining (BLOCKED.md, on the proven engine):** BNPL charge-arrival **auto-matching**
  (propose-link a card charge → discharge) · Tawarruq early-settlement · lease wizard+balloon+endings
  · certificate payout schedules+maturity · fund/ETF buy-sell+distributions · G-split UI · L buy/sell
  · ⑂. Each named, no limbo.

## WAVE M part 2 (10 Sep 2026) — FX + schedule engine shipped; paydown-write hit a Firefly wall
Deepest write session; judged by balance proofs, so I shipped only what's proven and staged the rest.
- ✅ **FX-correct mixed-currency totals** — `/api/positions` now converts EGP/USD → SAR via
  `to_sar()` (rates.yaml: EGP 0.075, USD 3.75); Holdings + net-worth restricted split are SAR-honest.
- ✅ **Financing schedule engine** — `/api/loan/setup` generates a straight-line principal/cost
  amortization (`data/schedules.yaml`); `/api/schedule` reads it; committed-money **debt bucket now
  wakes** from schedules (this month's unpaid installments, real-month). Proven: 100k→112k over 36 =
  total cost 12,000; installment = principal 2,777.78 + cost 333.33 (→ "Bank & fees: financing cost",
  the Riba-lens feedstock).
- ✅ **M2.0 — the paydown-WRITE, SOLVED + surfaced + balance-proven.** The "wall" was **my own test
  bug**: I dated payments in the future (Oct 1), so `current_balance` (as-of today) didn't reflect
  them. The correct Firefly debt-paydown shape is a **withdrawal, source=asset, destination=liability,
  current date** (NOT a transfer — that 422s). `/api/financing/pay` fixed to that shape. **End-to-end
  balance proof through the app:** liability −100,000 → −97,222.22 (principal_discharged 2,777.78),
  cash −2,777.78, cost 333.33 → "Bank & fees: financing cost", **proof_ok: true**. Surfaced on the
  **loan account detail**: set-up-schedule → amortization (principal · total cost · cost-to-date ·
  paid N/term · payoff bar · next payment split) → **Record payment** (shows the balance-proof).
  Test accounts cleaned. *Lesson banked: current_balance is as-of-today; never date a proof in the future.*
- **Cascade still to build (BLOCKED.md, on the proven engine):** BNPL purchase+installment-matching ·
  Tawarruq early-settlement · lease wizard+balloon+endings · certificate payout schedules+maturity ·
  fund/ETF buy-sell+distributions · G-split UI · L buy/sell · ⑂. Each named, sequenced, no limbo.

## WAVE M — foundation (10 Sep 2026) · the layer the whole asset/debt anatomy attaches to
Biggest wave; built the foundation now, per-instrument write-flows honestly staged as part 2.
- **New account subtypes** (self-service from Accounts → + Add): certificate/fund/etf/gold/silver/
  hissar/equity (assets) · loan/bnpl/lease (liabilities), grouped Investments · Gold & metals ·
  HISSAR · Company equity · Financing. (TYPE_MAP + account_kinds + `_group2`.)
- **positions.yaml** per account: as-of · restricted-until · rate/maturity/units/nav. **`/api/positions`**
  → **Holdings mini-view** on Accounts (value · restricted-vs-available · staleness). **Restricted-vs-
  available net-worth sub-line** ("of which restricted 🔒") — certificates count in net worth but
  are honestly flagged locked-to-maturity.
- **Monthly quick-update** (`/api/position/update`): a value change posts a **non-cash revaluation
  tagged `excluded`** — moves the balance (net worth follows) but never pollutes income/spend.
  **Dashboard staleness reminder** when a position hasn't been updated in 60+ days.
- **Hawl base extended** — certificates/funds/etf/silver join the zakatable total.
- Verified: certificate (restricted 2028) + fund → Holdings 150k = **100k restricted + 50k
  available**, net-worth "of which restricted 🔒" shown; demo accounts cleaned after.
- **Part 2 staged (BLOCKED.md):** G+L split · ⑂ · BNPL purchase+matching · Tawarruq loan schedule ·
  lease wizard+balloon+endings · depreciation · certificate payout schedules+maturity alerts ·
  fund/ETF buy-sell+distributions · FX-correct mixed-currency holdings totals. Doctrine held:
  HISSAR blind (balance+transfers only), equity = book value (M12). Guide gained an investments recipe.

## WAVE B — Budget arithmetic (10 Sep 2026) · smart-now, no intelligence
Arithmetic arranged to feel like advice — every number states what already is; nothing proposes.
- **B1 Committed-money view (headline).** `/api/committed`: Σ bills due THIS month (counted in
  their real month, never smeared — a quarterly/school bill lands in its month) + envelope
  contributions (+ a debt bucket = 0 until Wave M books loans/lease/BNPL). Surfaces: a Dashboard
  line and a Categories-summary "Committed" stat. Honest empty state: "set bill amounts to light
  up" (all 20 bills unset today → total 0). **This is the payoff of the 20-bills sitting.** Facts
  only — NOT "available to spend" (safe-to-spend stays gated). Verified: 3 demo bills → SAR 420,
  then reverted to honest 0.
- **B2 Set-from-history.** `/api/category/averages` → last / 3-mo / 6-mo, **gated on real ledger
  months** (Travel: avg3 shown, avg6 hidden at 4 months history — honest). "⟲ hist" button per
  Manage row fills the target from the chosen window.
- **B5 Fixed/flexible tag.** Per-category `flex` in category_meta (Manage toggle 🔒 fixed / 🌊 flex);
  Categories summary shows the fixed-vs-flexible spend split.
- **B3 Sinking funds** — the envelope engine already computes required-monthly (goal ÷ months-left)
  and feeds committed; remaining piece = due-month Calendar dot (staged).
- **Staged (BLOCKED.md):** B4 Hijri budget periods, B6 budget history grid, B7 irregular bill dates
  (school-fees thin schedule + sinking-fund handshake). Guide gained budget + committed recipes
  (guide-is-code rule honored).

## INCIDENT — category delete/rename fail "not found" (two-store disease, 10 Sep 2026)
Hisham added categories (working post-reload ✓) then **delete → "category not found"** (in a raw
browser `alert`). Root cause: a category lives in **two stores** — Firefly + our tree
(`category_tree.yaml`) — and delete/rename resolved existence via `_cat_id()` (Firefly only) while
the Manage list is drawn from the **tree**. A category present in the tree but not Firefly (e.g.
`ZZNewCat`, which my own earlier test-cleanup deleted from Firefly but not the tree) shows in the
list yet fails delete with a **lying "not found"**. **Why the earlier "sweep siblings" missed it:**
task #55 consolidated only the *add* path; I did not actually re-test delete/rename/merge against a
tree-only category — the sweep was claimed, not done. Incident-honest: that gap is the miss.

**Fix (all verbs now resolve through BOTH stores + keep them in sync):**
- Added `_cat_in_tree` / `_tree_remove` / `_tree_rename`. Existence = "in either store"; "not found"
  only when truly absent from both.
- **delete:** removes Firefly cat (if present) + tree entry + meta/target/envelope config; verified on
  a tree-only orphan (old code failed, new returns ok, gone from tree).
- **rename:** renames Firefly cat (moves real txns) AND the tree key; verified both-store sync.
- **merge:** now also removes the orphaned source tree entry (was leaking) + ensures dest in tree.
- meta/icon/color/target/env were already name-keyed (no id lookup) — clean.
- **Killed every raw `alert()` in Manage** → design-system toasts (err/ok), never "localhost says".
  Added success toasts on add/delete.
- Left `ZZNewCat` + `test` in place — Hisham deletes them via the fixed UI as the acceptance test.

## INCIDENT — "the fix didn't reach me" + Guide wave (10 Sep 2026)
**Incident: add-category "still broken" after the atomic fix (d3265b9).** Root cause was NOT the
code — the served `/categories` had the atomic fix (seed-dance gone, one door), the API worked, a
fresh headless load worked. The real gap: **a browser tab opened BEFORE a deploy keeps running its
old in-memory JavaScript forever.** `_NOCACHE` only helps on reload; nothing told an open tab a new
build shipped. My verification (curl + always-fresh headless) never exercised the stale-tab path —
*that* is the incident. **Systemic fix:** `/api/version` (build id = app.py mtime, moves every
rebuild) + rail.js polls it every 45s and shows a "🔄 HAKIM was updated — click to reload" pill when
it changes. Every future fix now reaches an open tab within a minute. Banked the lesson + the
"verify the way the owner uses it" rule in the new **CLAUDE.md**.

**Guide wave (Wave G) — shipped.** Three audiences (Sarah / future-Hisham / next session):
- **/guide** (rail, near Settings): 21 task recipes grouped Daily · Monthly · Fixing mistakes ·
  Money concepts · Household · Getting around — numbered steps with real UI names, **written to
  match the system as it is** (staged features omitted, not described aspirationally). Plus a
  **"How HAKIM thinks"** tab: the doctrines in owner language (one door · truth-engine-below ·
  flag-don't-guess · honest empty states · totals prove themselves · exclude-not-delete · surplus
  gate). Search box across recipes.
- **/changelog "What's new"**: rendered from STATE.md via `/api/changelog` (splits `##` sections,
  pulls dates, newest-first) — zero manual upkeep. STATE.md now mounted read-only at
  `/app/STATE.md` (compose) so it's live without a rebuild.
- **CLAUDE.md** created: the guide-is-code maintenance rule (any brief changing a guide-listed flow
  updates the recipe in the same commit) + the discipline + the build/rebuild + verify-as-owner rules.
- *Staged (remaining Wave-G piece):* the ~8 ⓘ in-place explainers (net-worth axis · envelope formula
  · ⊙ direct row · cleared-vs-available · queue-vs-confirm badge · utilization bar · hawl line ·
  committed-money) — single-sourced from guide content; ship per-surface. BLOCKED.md.

## Walk-through bug fixes (10 Sep 2026) — three load-bearing catches from real use
Owner's-hands testing found three; each root-caused (incident discipline), fixed, verified.

**1 · Split modal had no usable per-line amount (broke the whole feature).** Root cause: the
amount `<input>` existed in code but sat in `.line{display:flex}` with `.line input{flex:1}` next
to a wide category `<select>` — on the narrow sheet it collapsed to a sliver, reading as absent, so
the remainder never moved. Rebuilt each split line: **prominent right-aligned amount input on its
own row** + **keypad math** (`120+35` evaluates) + **"assign rest"** one-tap (Money Pro
deduct-from-total) + Enter-to-next-line + **sub-category per line**. Live remainder mints at 0;
Save is gated (remainder must be 0, every line > 0, ≥2 lines, exact sum — never rounds silently)
with a guiding label ("Assign SAR X more" / "Over by"). Verified at 2400px on SADAD 212.03. Added
a `?txn=X&split=1` deep-link. *Was it ever there? — the input existed but was never usable at that
width; a layout regression, effectively never-worked-in-practice.*

**2 · Add-category "broken" in Manage.** Root cause: the API works (verified — a category added
via the flow appears), but the Manage add used a fragile client-side **two-step seed-dance**
(create Firefly cat → add `__seed__` sub → delete it) to register in our tree; if either tree call
failed mid-way, the category landed in Firefly but not the tree → invisible = "drift". **Fix +
consolidate:** `/api/category/add` now creates the Firefly category AND registers the tree entry
**atomically in the backend**, taking a `role` (expense/income). Frontend is one call; the
seed-dance is gone. One owner for the add path.

**3 · Manage Bills kicked out to Firefly's UI (doctrine violation).** "Set amount" and "Open
Firefly bills" linked into Firefly's own screens — against "the truth engine's screens are not your
screens". Root cause: the Manage-Bills surface shipped as **link-out**, never as in-app CRUD.
**Fixed:** full in-app bill management — `/api/bill/create|update|delete` (name · amount w/ keypad ·
schedule freq · active · delete); Recurring page gains a bill-edit modal, **"＋ New bill"**, and a
fast **"Set all amounts"** list (the 20-bills sitting, in one sitting). Every Firefly link removed
and swept. Native Firefly freqs (weekly/monthly/quarterly/half-year/yearly) supported. *Staged:*
the genuinely-irregular "school fees on 3 specific dates" case → a thin schedule file over a Firefly
bill (BLOCKED.md) + the sinking-fund handshake; downstream calendar/committed integration with it.

## Envelopes + split verification (10 Sep 2026) — Hisham's real-life problems
Discipline held: arithmetic ships now, coaching stays gated, money-write machinery → Wave M.

**Envelope budgets + recovery (Part A — arithmetic only, SHIPPED).** A category target can be an
**envelope**: monthly contribution + start date → available = Σcontributions − Σspending-since-start.
Backend `/api/envelopes` + `_envelope_state` (proven: 9×1,000 − 2,262 = 6,738 available). **Negative
allowed and honest** — rose bar + **pure-math recovery countdown** ("at 1,000/mo → back to zero
{month}"; proven: −26,332 → 27mo → Dec 2028). **Sinking-fund** variant (goal + due → contribution =
remaining ÷ months-left). **Optional link-to-account** with drift flag ("envelope 4,000 · account
3,850 · Δ150" — flag, never auto-fix). Shows on Categories rows + circles; self-service "🧧 env"
toggle in Manage. NO coaching — sizing/stop-spending/safe-to-spend stay gated (BLOCKED.md gate note).
Demo envelopes used for the screenshot then removed — Hisham sets his own (e.g. Sarah's shopping).

**Split-by-category — verified + a real correctness bug fixed.** Hisham is using split on real
receipts (Zara 2,000 → 1,600 Aser + 400 self). Verified end-to-end: live remainder (Save gated on
zero), per-line category + person, sub-category per line, SMS/imported parity. **Bug found & fixed:**
`/api/split` correctly stored N lines in one Firefly group, but `norm()` read only `transactions[0]`
— so **every split line after the first was invisible to all analytics** (categories/by-person/
totals undercounted). `all_txns()` now **expands split groups into one row per line**; proven on the
Zara case: both lines visible, sum 2,000 (no double-count, no miss), Aser←1,600 / Hisham←400,
Clothing:Kids←1,600. Desk rows now show a ⑃N split marker. Test split created → verified → deleted.

## Review-tour fixes (10 Sep 2026) — edit · account-entry · confirmation
Four catches from Hisham using the system as an owner (manual entry → mistake → fix). All shipped.

**1 · Full transaction edit (write-discipline surface).** Every txn card gains "✎ Edit details" →
amount / date / description / account, all correctable. Posts via `/api/txn/edit` (Firefly PUT)
and **appends an honest audit note** ('edited by Hisham, 10 Sep 2026: amount 13.04→99.99') — never
a silent rewrite; undoable. **Delete** for manual entries (typed DELETE confirm); imported →
**Exclude** (`/api/txn/delete` mode=exclude): the statement line stays (bank truth), tagged
`excluded`, dropped from analytics — `all_txns()` now filters excluded by default across all 22
analytic sites; the Desk opts in (include_excluded) to show them, un-excludable. Provenance
(bank ref / statement line) shown read-only, never touched. Proven: edit→note→revert, note restored.
Person/class already editable via the card chips.

**2 · Accounts → enter the account.** The /accounts inline detail gains a prominent
"All N transactions in <account> →" door routing to the Desk filtered to that account.

**3 · Confirmation workflow (first-class).** New **Confirm** tab on the Desk = everything not yet
human-verified (white), with **type sub-chips (All / Expenses / Income / Transfers)** + live counts
from `/api/unconfirmed`, a "Confirm one at a time" Review-Mode run, and "Select to bulk-confirm".
Tab badge shows the count (distinct from the categorization queue — 22 to confirm vs 19 to
categorize). Dashboard gains an honest "N to confirm" alert → deep-links to `/?confirm=1`.

**4 · Add-subcategory verified (no build).** Confirmed clean on Travel (24 transactions): the sub
appears in the tree, existing transactions are untouched (still 24), delete reverts. Hisham's
Sightseeing/Activities add will work.

## WAVE R — Rules & bulk (10 Sep 2026) · pre-Sarah
Executed on "go Wave R". The rules-before-Sarah ordering is the payoff: her merchant-heavy
statements now meet a rule engine + batch tools instead of one-at-a-time review.

**R1 · Firefly-native Rules manager (the crown find) — `/rules` page + backend.**
- Surfaces Firefly's server-side rule engine (rule-groups → rules → triggers → actions), which
  runs on store/update AND on-demand over existing txns — unlike our import-only merchants.yaml.
- Endpoints: `/api/rules` (list + migration state), `/api/rules/impact` (queue estimate),
  `/api/rules/migrate`, `/api/rule/create|toggle|delete`, `/api/rule/{id}/test` (preview
  matches, read-only), `/api/rule/{id}/apply` (trigger over ledger — writes, audited).
- **Migration: 52 of 54 importer rules → Firefly** (idempotent by title). 2 skipped honestly —
  "D360 top-up" and "LEADER EXPRESS" both target category "To review" (no action to take).
  category → set_category; tags → add_tag; `|` alternations → OR of description_contains.
  Substring migration is best-effort (regex ⊃ contains) — flagged in the UI, spot-check via Test.
- **Queue-impact estimate (honest):** review queue = 19, but all 19 are transfers/SADAD — not
  merchant purchases, so rules-by-description genuinely can't address them (stated, not hidden).
  0 rule-addressable today → the real payoff lands on Sarah's merchant statements.
- Firefly quirk found: rule test/trigger reject year 2100 (422) → bounded range 2015–2035.

**R2 · Desk bulk operations — extended.** Multi-select + batch Verify + batch Categorise already
existed; added **batch Person** and **batch Class** to the batch bar (reuse `/api/apply`, undoable).

**R3 · "Make this a rule" → native.** The Desk "always apply to this merchant" path now ALSO
creates a Firefly-native rule (description_contains → set_category/tags), so it runs on existing +
future txns, not just at import. Idempotent by title; failure is caught + audited (never blocks the categorize).

**R-limits (Z5 pulled forward) · credit-utilization + editable limits.** `data/card_limits.yaml`
(Hisham's 5 verified limits) + `/api/card/limit` (self-service from Accounts → card → Credit
limit). Utilization bar on each card: amber >70%, rose >90%, red >100%. **Honest surfacing —
two cards over limit:** •5158 106% (30,210/28,500), •5019 102.8% (15,418/15,000); •4331 maxed at
99.8%; •8381 42%, •6510 63% healthy. Sarah's •437x has no limit → no bar (never faked). This is
the picture Debt Coach will one day start from.

**Decision applied:** nisab = 85g-gold estimate (SAR 25,500), kept flagged everywhere.

## Wave — Final Sweep · Last Dig · Inward Dig (10 Sep 2026)
Three briefs; scope taken honestly (time-critical + regression + cheap wins + audits shipped;
heavy items staged in BLOCKED.md §G, not silently dropped).

**Shipped & verified (2400/1440 screenshots):**
- **Heatmap regression fixed.** Root cause: the `🔥 heatmap →` link was dropped in commit
  `2def160` (the Money-Pro categories rewrite) — the page/route/API were intact but orphaned
  (⌘K-only). Rebuilt in its best home: **Calendar day-cell intensity shading** — a rose overlay
  per day, opacity ∝ √(day-spend / month-max), behind a visible "🔥 Spending heat" toggle
  (persisted; `?heat=1` deep-linkable) with a less→more scale legend. Verified: Sep 1 (−31) and
  Sep 2 (−212) shade correctly.
- **Hawl tracking groundwork — TIME-CRITICAL, now recording.** The hawl (one lunar year at/above
  nisab) can only be known from a *daily* record — never backfilled — so this had to start now.
  `scripts/hawl_track.py` (nightly, `com.hakim.hawl.plist` @ 23:50) → thin trigger POSTing to
  **`/api/hawl/snapshot`**; money-math in the review-ui: zakatable = liquid/monetary asset
  balances (cash/bank/digital/receivable/gold; excludes cards + property), nisab from
  `data/zakat.yaml` (85g-gold estimate until Hisham sets his own — flagged). Writes append-only
  `data/hawl_trail.json` + derived `data/hawl_state.json` (streak, hijri-anniversary due date).
  **Calculates nothing** (no zakat assessed, no fatwa). One `/settings` line (status + nisab
  input). Registered as the **7th dead-man's-switch agent** (health + /api/agents). First real
  record: 2026-09-10, zakatable SAR 18,853, below the 25,500 estimate → clock not yet running.
- **Cheap wins:** gold asset type (zakatable, "Gold & metals" group); 6 built-in **report
  presets** (Zakat base, Sadaqah/charity, Business-vs-personal, Household-by-person, Cash-flow
  90d, This-month spending); **dashboard pace indicator** on the This-month tile (% of month
  elapsed vs % of typical spend, typical = mean of prior full months — honest, live-month only);
  Monarch Flex 3-bucket roadmap note.

**Audits (findings in BLOCKED.md §G):**
- **Goals ownership:** parallel `data/goals.yaml`, NOT Firefly piggy banks (zero piggy-bank API
  calls). Kept parallel deliberately (piggy banks can't do pay-down-card / target-dates); honest
  cost = invisible in Firefly UI, preserved only via restic snapshot of `data/`. No migration.
- **Firefly-native:** using native = bills / transaction_links / attachments / categories-tags-
  accounts / reconciled. Reimplemented = rules (merchants.yaml vs native engine — the crown
  find), budgets (targets.yaml, deliberate), piggy banks, webhooks (poll vs push), recurrences.

**Staged (BLOCKED.md §G, with reasons):** Firefly Rules manager (#34, highest-leverage next),
Desk bulk ops (#35), owed-to-me ledger (#36), cash-count wizard (#37), webhooks (#38), txn links
UI (#39), recurring bill-linking (#40), seasonal goals (#41), goals per-month math (#42), full
calendar bills layer (#43), **credit-utilization bar (#44 — blocked on missing per-card limit
data, not effort; refused to fake a limit)**, riba/fees lens (#45), strictness+compare (#46).

### Reconciliation pass (10 Sep, same day) — three digs → 100% dispositioned
Cross-checked the report against all three dig briefs; recovered 5 dropped/unstated items:
- **Built now:** Calendar bills layer (due-dots + day-panel bills with paid✓/amount-not-set +
  "N due · rest of month" footer — verified on Oct 2026: "🔔 16 bills due · 16 amounts not set").
- **Honest correction:** the **Riba & fees lens did NOT ship** — only the Sadaqah preset did.
  Staged at full spec (per-card + 6-mo trend + Categories drill) as WAVE H5.
- **Staged:** trip tagging (Z4), Recurring native paid-status (N3).
- **Delivered:** Inward #6 disposition table — every remaining Firefly-native feature marked
  adopt/stage/exclude+why (BLOCKED.md §G). Inward map now closed as fully as the outward one.
- **Sequenced** the whole staged pile into execution waves **R → M → H → N → Z**, one per "go".
  Ordering rationale: **Rules manager + Desk bulk ops (WAVE R) must land before Sarah's 3
  statements** — turns her import from ~200 one-at-a-time reviews into an afternoon of one-taps.
- **Decisions:** Goals-stay-parallel **ACCEPTED**; nisab (recording vs 85g estimate) + 5 card
  limits **PENDING Hisham** — will not be faked.

## Naming discipline (correction, 6 Sep)
The factory's name is **NOT decided**. "NWF" / "Al Nabeel" are placeholders from old
files and must **never** appear in the agent, categories, docs, or deferral messages —
always "the factory (name TBD)". The only legitimate NWF references are the actual
filename `NWF_Master_Model_v29.xlsx` and the line in `businesses.md` that *defines*
these as placeholders. Category stays `Capital contribution: Factory`; rename to the
real name only when it exists (one rename call then updates everything).

## Tokens
- `FIREFLY_PAT` — Finance agent (used read-only, enforced in code). Stays.
- `FIREFLY_ADMIN_TOKEN` — for setup scripts; empty ⇒ falls back to `FIREFLY_PAT`.
  DECISION: Hisham creates a dedicated admin token → goes here → **revoke after
  balances + bill amounts are entered.** Setup scripts already prefer it.

## Next
- Enter real opening balances → ask Finance "what's my cash position?" for a true number.
- Fill bill amounts/dates.
- Then agent #2: **Operations** (MENTCO / ERPNext).
