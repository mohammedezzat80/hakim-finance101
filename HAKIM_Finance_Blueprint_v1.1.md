# HAKIM · FINANCE — Master Blueprint v1.1 (The Intelligent Layer)
_8 Sep 2026 · v1.1: renamed per the FINAL design docs — the finance agent is **Finance**
(the CFO, build target #1); "MAAL" is retired everywhere. Same rule as NWF: never
reuse the old name. The complete feature map for HAKIM's personal-finance intelligence, compiled
from three deep research passes over the best of the market (Copilot, Monarch, YNAB,
Simplifi, PocketGuard, Rocket Money, Empower, Origin, Snoop, Emma, Cleo, Finny, Whistl,
plus enterprise FP&A) + HAKIM-only capabilities no market app can build.
**TO CLAUDE CODE: this is a BLUEPRINT to store and build from in waves — NOT a build-now
order. Nothing here starts until Hisham explicitly says "build Wave N". Save this file,
reference it in STATE.md, and treat the wave gates as hard.**_

## 0 · Standing principles (inherited, non-negotiable)
- Desk (:8001) = truth only, no analysis. The intelligent layer is a SEPARATE surface
  (the Dashboard) + the Finance agent + notifications.
- Agents draft, Hisham decides. Guarded writes only. Everything logged. Flag don't guess.
- Privacy absolute: no cloud, no third-party rate/data services; reference tables local.
- Design system: the desk's glass + HUD chrome; the constellation background is BANKED
  for the Dashboard. Law: glow = attention, color = direction. Visual claims need pixels
  at Hisham's real viewport. Arabic first-class everywhere.
- Provenance is a first-class fact (built 8 Sep): every transaction carries its
  source (SMS / statement / manual / import-run) and confirmation status — SNB & SAB
  SMS items await statement confirmation; digital banks (stc/D360/Barq) are
  SMS-final. All analytics can filter by source and by trust state.
- Data gates matter because every feature below divides by ONE number — true monthly
  surplus — which requires: Sarah's statements imported · review queue ≈ 0 · safes/cash
  counted · ≥ 3–4 normal weeks observed.

## 1 · THE DASHBOARD (Wave 1 — the beautiful reading layer)
Fullscreen HAKIM OS-styled surface (constellation lives here), tiles tap-through,
every number drills down (rule: no dead-end numbers — click shows how it was computed).
- **Month view + pace bars** (Copilot): per-category bars filling with the month, a
  "today" marker; ahead/behind visible without reading.
- **Sankey cash flow** (Monarch's fan favorite): income → categories/savings/debt as a
  flow picture; filter by person; monthly + custom range.
- **Net-worth line** (Monarch/Empower): assets vs liabilities over time; the villa
  (Home creation total) shown as a becoming-asset overlay; multi-currency consolidated
  to SAR with per-currency detail.
- **Calendar** (Money Pro's crown, upgraded): bills + expected salaries on a DUAL
  Hijri/Gregorian calendar; Ramadan/Eids/school-season/Egypt-summer shaded as seasons.
- **Spending heatmap**: day-of-week × time intensity (late-night delivery, Thursday
  patterns) — mirror, not judgment.
- **Per-person tiles**: Hisham / Sarah / Aser / Adam month totals from person tags.
- **Statement line everywhere**: N txns · SAR in / out for any view (bank-style).
- **Merchant view**: month-on-month by merchant (Snoop), logos/icons for recognition.
- **Safe-to-spend tile** — see §3; the dashboard's biggest number.
- Saved custom reports (any dimension: category/sub/tag/person/merchant/account/period),
  favorites, comparison across periods INCLUDING payday-to-payday and
  Ramadan-vs-Ramadan (Money Dashboard/Snoop period flexibility, Hijri-aware).
- CSV/Excel export of any view (NAS habit).

## 2 · BUDGET ENGINE (Wave 2 — the best of three religions, merged)
- **Structure = Monarch Flex**: Fixed / Flexible / Non-monthly buckets (human, gentle).
- **Non-monthly = YNAB True Expenses**: every irregular known cost (school installments,
  insurance, Eids, car service, Egypt trips, renewals) amortized into a monthly
  set-aside — this IS the sinking-funds design (Firefly piggy banks on SABB
  School/Travel/Shopping + new buckets), now formalized.
- **Live plan = Simplifi**: "left to spend" recalculates in real time; planned one-off
  expenses enterable in advance (birthday dinner next week reduces this month's free).
- **Health metric = YNAB Age of Money**: how old is the riyal you spend today; rising =
  breaking the hand-to-mouth cycle. Displayed on Dashboard, tracked over time.
- **Margin finder** (EveryDollar): periodic scan proposing where breathing room exists.
- Salary-day ritual: one message — set-asides list + resulting safe-to-spend.
- Rollover rules per bucket (shopping rolls over → visible reward for discipline).

## 3 · SAFE-TO-SPEND (Wave 2, the one number — PocketGuard's soul)
"Today you can spend X without touching anything promised."
X = liquid cash − (bills due before next income) − (set-asides this cycle) − (card
payment plan) − buffer. Honest because the ledger is complete (incl. cash + wallets —
no market app has this). Eventually the phone-widget number.

## 4 · FORECAST & SCENARIOS (Wave 3)
- Projected balance curves per account, weeks/months ahead (bills register + salary
  dates + recurring patterns + set-asides). Shortfall warnings BEFORE the event.
- **Saved comparable scenarios** (Monarch): "pay 8K extra on MC •5158" vs "buy laptop
  in March" vs "increase school bucket 10%" — side-by-side outcomes, kept, revisited.
- **Variance explanations in words** (FP&A): auto-written "August ran 2,100 over July,
  driven 80% by Travel (trip:Cairo)". Arabic or English.
- What-if chat: Finance answers scenario questions conversationally from the same engine.

## 5 · DEBT COACH (Wave 2–3 — the highest-value coach)
- Fee odometer: tawarruq/fees per card per month + running year total, framed in real
  terms ("= a school term"). Data already tagged (Bank & fees: Card fees & tawarruq).
- Avalanche plan from TRUE surplus: order, monthly number, debt-free date, fees saved
  vs alternatives; recalculated monthly from actuals.
- Card-vs-cash drift meter: card spend this cycle vs cash available — the early-warning
  number that prevents the next 130K.
- Fee-date warnings from SMS statement dates; payment reminders.
- Pre-purchase planner: "laptop 8K on Visa — plan?" → fits-this-cycle / split-cost in
  fees / or "wait until <date>, here's the bucket".
- (Never shame. Numbers + dates + choices.)

## 6 · RECURRING & SUBSCRIPTION HUNTER (Wave 2 — Rocket Money absorbed)
- Auto-detect recurring charges beyond the known bills register (Copilot-style scour).
- Price-increase alerts ("STC line up 12% vs its 6-month norm").
- Pre-renewal warnings (3 days before) + unused-subscription flags (paying, not using).
- **Refund/duplicate tracker** (Snoop): duplicate charges, refunds that never landed,
  wrongful fees — flag with evidence. (Snoop users clawed back real money; ours sees
  more data than Snoop ever did.)

## 7 · WHISPER LAYER (Wave 3 — proactive, tiny, rare; ntfy → phone now — the FINAL
specs name Signal as the eventual family channel; migrate when the Watch/notification
layer is built)
- Morning brief: 3 sentences (yesterday, today's bills, one heads-up). Arabic optional.
- Weekly smart review (Snoop cadence): the Sunday health line grows a money section.
- **Friday CFO meeting**: generated 5-minute agenda (3 numbers, 1 decision needed,
  1 win) — for Hisham, later Hisham+Sarah.
- Anomaly whispers: double charge, bill 40% above norm, odd-hour card use, balance
  shortfall approaching. RARE by design — a system that pings daily gets muted.
- Moment-of-spree awareness (SMS real-time advantage): "3rd purchase at the mall in
  40 min, 890 total" — one calm line, mid-spree. No app can do this; HAKIM can.

## 8 · BEHAVIORAL LAYER (Wave 3–4 — Whistl/PsyFi lessons, HAKIM voice)
- Precommitment rules Hisham sets, HAKIM remembers: "luxury waits 48h" → when a
  luxury-tagged purchase appears, quote him to himself; never block.
- Pattern mirrors: time/trigger/context groupings presented as self-knowledge.
- Time-cost translation: prices restated as "≈ N days of MENTCO profit" or "≈ 2 months
  of card fees" (visceral, optional toggle).
- **Financial health score** (Emma): one honest number from debt ratio, age of money,
  buffer months, bills coverage — trend line, not judgment.
- Optional personality modes (Cleo lesson): default = calm Arabic-capable coach;
  opt-in "روستني" honest-roast mode. Engagement through character, never shame default.

## 9 · WEALTH VIEW (Wave 4 — Empower absorbed, awaits Wealth agent era)
- Full net worth: banks, cash, wallets, receivables, cards, + manually anchored assets
  (villa value, gold, Egypt assets, vehicles). Trend line, allocation view.
- Investment fees analyzer → HISSAR's domain, surfaced at Wealth level later.
- **SIMAH credit report tracker** (Saudi analog of credit-score features): periodic
  manual import of SIMAH report → obligations vs ledger cross-check, score trend.
- Islamic estate awareness (far future, Origin analog done right): faraid-aware net
  worth snapshot + wasiyya checklist. Documentation, not fatwa.

## 10 · CAPTURE PERFECTION (Wave 3–4 — Finny absorbed)
- Tell-Finance entry: "غداء ٤٥ من المحفظة" in chat → drafted transaction → one-tap
  approve (needs its guarded write gate, designed like the importer's).
- Receipt snap: photo → parsed draft (amount/merchant/date) → approve. Batch mode.
- Voice later via HAKIM voice layer. Unified currency view is already native.
- **Receipt Intelligence / items layer** (nobody has this): local parsing of receipts
  into item/qty/unit-price DB → consumption rates (rice/milk per month), price
  comparison per store, personal inflation index, bulk-buy suggestions; groceries
  first, then perfumes/clothing/electronics. Depends on the attach habit (already live).
- Later feeds: email + WhatsApp invoice ingestion (gated on Shield + access layer).

## 11 · FAMILY (Wave 4 — Monarch household, done privately)
- Yours/mine/ours account labeling; Sarah's household view per family.md rules.
- Kids' money school: Aser's safe with goals, allowance schedule, savings match —
  real-data money education; Adam's later.
- **HAKIM Wrapped**: end-of-year private "year in money" story (biggest month, villa
  total, fees paid vs saved, top merchant, most-sent person) — beautiful, Arabic,
  no one else's eyes. Also month-in-review (Copilot) as the monthly mini-version.
- Time machine (year 2+): "this day last year", Ramadan-vs-Ramadan.

## 12 · ZAKAT ENGINE (Wave 3 — HAKIM-only, high value, quietly profound)
- Continuous nisab tracking across all zakatable assets (cash, gold if anchored,
  receivables per fiqh setting), hawl date tracking, madhhab-configurable rules.
- One-tap zakat report when due: amount, basis, full audit trail; links to
  Zakat & charity category to close the loop. (Local gold-price table, user-updated.)

## 13 · MONEY PRO DNA (the app that kept Hisham for years — its soul, fully absorbed)
Money Pro's core invention, adopted as a first-class Finance concept:
- **The plan → approve → actual cycle (Wave 2, high priority):** planned transactions
  live on the calendar WITHOUT touching balances; a **Today view** (dashboard tile +
  desk surface) shows bills due + *predicted repeats* ("you usually buy groceries on
  Thursdays — add it?"); each approved with ONE tap (the PAID moment). Feeds the
  forecast engine directly. Quick-reschedule verbs on any due bill: tomorrow / 3 days /
  next week.
- **Budget rollover, both directions (Wave 2):** leftover rolls forward as reward;
  optional NEGATIVE rollover — overspending last period automatically tightens this
  one. Per-bucket setting.
- **Per-period budget limits (Wave 2):** set a different limit each month — the taper
  plan ("reduce eating-out gradually: 2,000 → 1,700 → 1,500").
- **Budget bar language (Wave 1):** actual (colored) drawn over plan (ghost) — richer
  than plain pace bars; income bars in their own color.
- **Calculator keypad in Quick add (desk, near-term):** amount field does math
  (26.5+38+12 =) and inline currency conversion — Money Pro's entry keypad, kept.
- **Icons everywhere + custom icons (Wave 1):** icon per category/subcategory in every
  picker/row; allow custom images (Hisham's own photos) for personal categories.
- **Extra fields (desk, near-term):** payee (→ feeds Counterparties book), optional
  reference/check#.
- **PDF export (Wave 1):** reports export to PDF as well as CSV/Excel (NAS archive).
- **Profiles (Wave 4):** maps to family access (Sarah household view, kids) — already
  planned; Money Pro validated the need.
- **Habit reminder (optional, off by default):** a gentle daily "log your cash" nudge —
  offered because it worked for Hisham for years; respects the whispers-are-rare rule
  by being explicitly opt-in.

## PLATFORM (rides along each wave)
- Dashboard on Homepage + Tailscale phone access; later PWA/app-like packaging.
- Widgets/watch/Siri-style entries — far future, after mobile packaging.
- All features honor trust states; analytics can filter to "verified only".

## BUILD WAVES & GATES (the contract)
- **Gate G0 (before ANY wave):** Sarah imported · queue ≈ 0 · cash/safes counted ·
  3–4 normal weeks lived. Surplus number exists.
- **Wave 1:** Dashboard core (§1) — read-only, no writes, constellation skin.
- **Wave 2:** Budget engine + safe-to-spend + Debt Coach core + subscription hunter
  (§2/3/5/6).
- **Wave 3:** Forecast/scenarios + whisper layer + zakat engine + tell-Finance entry
  (§4/7/12/10-partial).
- **Wave 4:** Behavioral layer + wealth view + family + Wrapped + items layer
  (§8/9/11/10-rest).
- Each wave: its own brief, its own acceptance tests, Hisham's explicit "go".
- After Wave 1 ships: two weeks of USE before Wave 2 — the dashboard's real tiles are
  chosen by which questions Hisham actually asks.

## THE MOAT (why this beats every app in the file)
Complete data (banks+cards+wallets+CASH — market apps miss the last two and all Saudi
wallets) · real-time SMS capture (they see yesterday; HAKIM sees now) · trust-stamped
verified truth with audit logs · Hijri/seasons/Zakat/SIMAH (no Western app will ever
build these) · receipt-item intelligence (impossible on cloud privacy models) ·
cross-domain future (MENTCO/factory/HISSAR/personal in one brain) · Arabic-first ·
and zero third parties — every app above ships data to Plaid/Yodlee; Finance ships nowhere.

- **v1.2-roadmap:** Full **Arabic localization** (RTL layout + every string) — a real project, not a toggle.
- **v1.2-roadmap:** **Light theme** (full palette pass) — deferred; the switch is shown but off until built.
- **v1.2-roadmap:** Customizable dashboard — user-selectable/orderable widgets (Monarch pattern). Unlocks after system stabilization + Hisham's go.

## CHANGELOG
- **v1.3 (9 Sep 2026) — Money Pro Comfort Wave.** Made HAKIM feel like Hisham's daily
  instrument by replicating Money Pro's *interactions* in the Rasool dark system (look stays
  HAKIM, behaviour becomes Money Pro). Shipped after a full audit of Money Pro's five tabs +
  manual: **20 of 22 items built**, 2 consciously deferred with named unlocks. Built: categories
  show ALL (zero-spend dimmed, never hidden) · rows⇄circles⇄budget views (circle-fill vs target,
  over=rose ring) · subcategory hierarchy layer (`category_tree.yaml` = ours, Firefly stays flat
  truth; drag-reparent moves real txns by renaming the flat category) · icon system (curated local
  line-icon library by section + custom photo→circle upload in `data/category-icons/`) · budget
  targets with periodicity (weekly…yearly) + income targets + Total=income−expenses + parent=Σ
  children · account drag-reorder + hide(≠close) + merge-first · Other Assets/Other Liabilities
  groups (net worth now whole, not liquid-only) · **Reports tab** (7 types, Hijri-aware ranges,
  multi-filters, bars/line/pie/table, CSV+PDF+QIF export, saved reports) · Goals (save-toward /
  pay-down-card, progress from real balances, no coaching) · transaction classes (Personal/Business
  tags → report filter) · reconciled flag (+ cleared vs available balance) · attachments viewable ·
  type-to-filter category pickers · cross-currency transfer received-amount override (found already
  built) · planned-vs-actual overlay on the cash-flow chart. **Roadmap (blocked/deferred, named
  unlocks in BLOCKED.md):** AI budget proposals + budget rollover (need lived surplus history) ·
  Projected Balance report (forecast) · report scheduling (delivery rail) · liability-payment
  interest/principal split (item G) + asset buy/sell entry types (item L) — both deferred as one
  focused money-write micro-wave, since they mint linked transactions and the Desk doctrine ships
  money-writing flows only with exhaustive balance-reconcile + undo tests, never rushed. Standing
  finish line: *nothing Money Pro does daily that HAKIM doesn't — in Hisham's design, on his
  hardware, with his truth discipline.* Branch `feat/moneypro-comfort`.
- **v1.2 (9 Sep 2026):** Readable-surfaces wave shipped ahead of Gate G0 (owner override,
  logged) — the reading layer built while the ledger fills. **Design:** Option-A Rasool
  navy/mint reskin across Desk + Dashboard (gold retired to the ✦ spark only); **directional
  money colors** (income mint · expense dusty-rose · transfer lavender; alert-red reserved for
  failures) as the standing color doctrine; real credit-card face. **Surfaces:** Calendar
  (Umm-al-Qura Hijri, state-aware day panel, bills-due projection), Categories (donut / movers /
  least-used, To-review bucket surfaced), Recurring (Firefly bills as source of truth, computed
  next-due, honest placeholder amounts, dashboard Upcoming hookup), **Morning Brief** (ntfy 07:00
  whisper — HAKIM speaks first, one-way, honest). **House rule locked:** 8/4 two-zone on every
  full page; right rail carries derived insight; rail cards may show honest ghost states but
  never fabricated numbers. Repo initialized with strict .gitignore (no secrets/ledger/brain in
  git). Two standing human tasks surfaced by the build: fill the 20 bill amounts in Firefly, and
  set NTFY_URL for the whisper. Mega-brief execution (items 0–8) begun on branch `feat/calendar`.
- **v1.1 (8 Sep 2026):** Renamed MAAL → Finance per HAKIM_Agent_Specifications_FINAL /
  Design Manual 2nd ed. / Coordination & Reliability v2.0 (English agent names; system
  names HAKIM/WAZIR/HISSAR unchanged). Added the provenance principle to §0 (built
  into the live desk the same day, alongside the "New since last visit" view, calendar
  date pickers, and the agreed ⟨COMPLETE THE PICTURE⟩ completeness panel — these are
  DESK features, live before Wave 1, not wave-gated). Noted ntfy-now/Signal-later for
  whispers. Alignment check against the FINAL docs: agent names used here (Finance,
  Wealth, HISSAR, Watch, Shield, Mail, Docs, Archive, Vault, WAZIR) all match; the
  live decisions Firefly-personal-only and statements+SMS (no aggregators) supersede
  the older spec lines and the spec docs should be updated to match.
- **v1 (8 Sep 2026):** Initial — three research digs + gems + Money Pro DNA + waves/gates.
