# HAKIM Finance — standing rules for this repo

The review-ui (`review-ui/`, FastAPI on :8001) is baked into a Docker image: `app.py` + every
`*.html` + `rail.js` are `COPY`ed in the Dockerfile. **Changes to those files require
`docker compose up -d --build review-ui`** to take effect. Only `./data` and `./logs` are mounted.
When you add a NEW `.html` page, add a `COPY` line to `review-ui/Dockerfile` (a missing COPY = the
route 500s with "No such file").

## Discipline (money system)
- **One door for writes** — the Desk (or a deliberate management surface). Never a second path.
- **Flag, don't guess** — unknown card network / bill amount / nisab / card limit → ask, never invent.
- **Honest empty states** — placeholders never printed as real numbers; half-built says so.
- **Exclude, don't delete** imported (bank-truth) transactions; hard-delete only manual entries.
- **The truth engine's screens are not the user's screens** — no kick-outs to Firefly's own UI; all
  CRUD happens in HAKIM via the Firefly API.
- **Surplus gate** — coaching (stop-spending, safe-to-spend, budget proposals) waits for lived data.
  Ship the honest arithmetic (envelope recovery date, committed-money) now; never guess with authority.
- **Money-math in code**, read-only to the ledger where the agent is read-only.

## Verify the way the OWNER uses it (incident 10 Sep — add-category "didn't land")
- A curl/API test and an always-fresh headless load BOTH miss the real failure mode: a browser tab
  opened BEFORE a deploy keeps running old in-memory JS. `_NOCACHE` only helps on reload.
- **Fix shipped:** `/api/version` (build id from app.py mtime) + rail.js polls it every 45s and shows
  a "🔄 HAKIM was updated — click to reload" pill when it changes. Every fix now reaches open tabs.
- **Rule:** when a fix touches a user-facing flow, verify by driving the actual UI on a fresh load,
  not just the endpoint. State in the report if a reload is needed.

## The Guide is code (Wave G)
- `/guide` recipes describe the system **as it actually is** — never aspirationally. A recipe for a
  staged feature is omitted, not written.
- **Any brief that changes a flow a guide recipe describes must update that recipe in the same
  commit.** The guide drifts the moment this slips. `/changelog` renders from STATE.md (zero upkeep).

## Every substantive change
- Self-check at 2400px **and** 1440px with headless Chrome (render, then look before claiming done).
- **If it touches ANY page's inline script** (adds/removes/renames a JS function), run the render smoke:
  `bash review-ui/smoke_pages.sh` (host-side — needs Chrome; must PASS — every page loads with no JS console
  error). **The mrange class (14 Sep):** `node --check` PASSES on a page that *calls a deleted function* —
  an undefined call is a runtime `ReferenceError`, not a parse error, so the 5-point bar and the greps all
  ran green while `/dashboard` was dead on live load. Deleting a function with a bulk line-edit can silently
  take an adjacent still-referenced one. Only executing the page catches it. Re-load EVERY page you didn't
  screenshot after a shared-code refactor, not just the one you were building.
- If it touches transaction listing/filtering, run the two-sided transfer regression:
  `docker exec hakim-review-ui python3 /app/scripts/check_transfer_visibility.py` (must PASS — a transfer
  shows in BOTH accounts, opposite signs). One-sided account filtering is a recurring disease.
- If it touches account balances / net worth / debt, run the net-worth consistency regression:
  `docker exec hakim-review-ui python3 /app/scripts/check_networth_consistency.py` (must PASS — Dashboard
  == Accounts == Brief == the canonical `_networth()`). Net worth is the headline truth; two doors to it
  is a recurring disease. Every net-worth/debt number reads `_networth()` — never re-derive it.
- If it touches transaction edit / dates / the data-version signal, run the date-edit round-trip:
  `docker exec hakim-review-ui python3 /app/scripts/check_date_edit_roundtrip.py` (must PASS — an edited
  date MOVES the txn across months AND bumps the data-version so open tabs refresh). Every write through
  `ff()` (POST/PUT/DELETE) bumps `_DATA_EPOCH` — a successful write that open tabs never see is a write
  that lied. All date inputs are the shared `rail.js` picker (no raw typing) — a recurring error source.
- If it touches the reading layer (`all_txns`/`norm`), a heavy endpoint, or ledger size, run the perf
  guard: `docker exec hakim-review-ui python3 /app/scripts/check_perf.py` (must PASS — warm dashboard <
  0.8s, `all_txns` cached < 0.15s). `all_txns()` is cached on the data-version fingerprint; never
  re-fetch the whole ledger per view. Slowness must be caught by the ritual, not felt by Hisham.
- **Restore before you pause.** Never leave the running service broken (or mid-rebuild) while stopping to
  ask a question — `docker compose up --build` restarts the container (~15s dark); finish the change,
  rebuild cleanly, verify the page loads, THEN pause. A dark dashboard is never an acceptable waiting state.
- If it touches balance corrections / cash-count / reconciliation, run the corrections guard:
  `docker exec hakim-review-ui python3 /app/scripts/check_corrections.py` (must PASS — a correction moves
  the balance but is EXCLUDED from all flow analytics). **The deepest line:** the ledger records what
  HAPPENED (spending/income); a correction records what we LEARNED (true balance). Corrections/opening-
  debt/cash-count adjustments are tagged `excluded` + no category (the non-cash revaluation model) — never
  `Bank & fees`, never spending.
- If it touches ANY YAML-backed config write (budget targets / envelopes / merchants / registry / tree /
  schedules), run the config-cache guard:
  `docker exec hakim-review-ui python3 /app/scripts/check_config_cache.py` (must PASS — a config write is
  reflected by the very NEXT cached read). **The stale-config class:** `_vcache` keys on the *ledger*
  data-version, but a config write doesn't bump `_DATA_EPOCH`; `_config_sig()` (mtime of every `*.yaml`)
  is folded into the vcache key so the write can't be served stale. A write that reads back stale is a
  write that lied — hit twice (card registry, budget targets) before it was generalized.
- If it touches the "needs review" count on any surface, run the review-parity guard:
  `docker exec hakim-review-ui python3 /app/scripts/check_review_parity.py` (must PASS — Desk queue ==
  canonical, Categories strip == canonical). **One definition:** needs-review = `category == "To review"`
  (the Desk's). Category-LESS rows (transfers, excluded corrections, funding legs) are NEVER review. Two
  definitions is the net-worth fork wearing a new hat; a strip that counts N must open a door onto exactly
  those N (hide when 0 — no dead doors).
- If it touches a gated Opening surface (Today · and the tabs to come) or the honest-maturity system, run
  the Today/maturity guard:
  `docker exec hakim-review-ui python3 /app/scripts/check_today.py` (must PASS — safe-to-spend is honest
  arithmetic `cash − committed_remaining`; maturity is derived from the REAL complete-month count with a
  real ready-date; the dashboard's temporary forward view stayed retired; Today owns due+heads). **The
  Opening law:** every surface computes what its data supports and names — from the ledger, never
  hardcoded — the exact history a stronger claim needs and the date it's met. No estimate is ever printed
  as a pattern.
- Update `STATE.md` (dated section) and, for staged/deferred items, `BLOCKED.md`.
- Work on a ladder branch; commit with the required trailer.
- Report root causes explicitly (incident discipline): what was tested vs. what the owner does.

## Commit trailer
```
Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BVwc32qpxiQTokFBGpRWRb
```
