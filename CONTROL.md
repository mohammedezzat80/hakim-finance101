# HAKIM · Operator Control Audit
_Can Hisham add / edit / delete / merge every entity himself — no developer?_
_Rule: you build with us, but you never need us to operate. (9 Sep 2026)_

| Entity | Add | Edit | Delete | Merge | Surface |
|--------|:---:|:----:|:------:|:-----:|---------|
| **Accounts** | ✅ | ✅ rename/notes, correct-balance (adjustment) | ✅ empty; else move-history | ✅ move+close | Desk → **Accounts**; dashboard sidebar **✎ edit** |
| **Cards** | ✅ last-4 + network | ✅ network, balance, name | ✅ empty; else archive | ✅ | Desk → Accounts (card) |
| **Card networks** | ✅ | ✅ dropdown (verified) | — | — | Desk → Accounts (card) |
| **Categories** | ✅ | ✅ rename, icon, colour | ✅ → txns uncategorized (never deleted) | ✅ re-tag + delete, counts shown | **/categories → Manage** |
| **Budget targets** | ✅ | ✅ | ✅ clear | — | /categories → Manage |
| **Transactions** | ✅ Quick add | ✅ Desk review/edit, split, link | ✅ Desk | split / link | Desk |
| **Settings / prefs** | ✅ | ✅ | — | — | **/settings** |

### Gaps surfaced (for prioritization — not fixed this pass)
- **Bills / recurring — NON-TRIVIAL GAP.** No in-app add/edit/delete yet; bills (and their amounts — the 20×placeholder task) are managed in the **Firefly UI directly**. A "Manage bills" surface (Firefly `bills` API + a form: name, amount, cadence, next-due, archive) is the biggest remaining operator gap. Recommend it as the next control item.
- **Merchants / payees — PARTIAL.** Counterparty/SADAD naming is editable via the Desk merchant map (one biller at a time); there is no dedicated merchant register (rename/merge merchants globally). Non-trivial (touches `merchants.yaml` + counterparty extraction). Lower urgency.
- **Persons / tags (Hisham/Sarah/Aser/Adam + contexts)** — defined in config, applied on the Desk; no in-app add/rename of the person/tag list. Trivial-ish; deferrable.

### Expanded by the Money Pro Comfort Wave (9 Sep)
- **Accounts** — now also **drag-reorder** (order persists everywhere), **hide/unhide** (≠ close,
  balance kept), **Other Assets / Other Liabilities** groups (net worth whole). Merge still leads delete.
- **Categories** — now also **subcategory tree** (add/rename/delete/**drag-reparent**), **budget
  periodicity** (weekly…yearly) + **income targets**, **icon manager** (line-icon library + custom
  photo), rows/circles/budget views. Hisham owns the whole hierarchy from `/categories → Manage`.
- **Transactions** — now also **class** (Personal/Business), **reconciled** flag, **attachments**
  viewable, type-to-filter picker. All self-service on the Desk card.
- **Reports** (`/reports`) — full builder + **saved reports**, CSV/PDF/QIF, no developer needed.
- **Goals** (`/goals`) — define/track save & debt goals himself.
- Still developer-adjacent (deferred, BLOCKED.md): liability interest/principal split (G) + asset
  buy/sell entry (L) — money-write flows, one focused pass. Bills-manage remains the top open gap.

### Fixed this pass (trivial gaps closed)
- Categories were **not editable at all** → full CRUD + icon/colour/target now on /categories → Manage.
- Account manager was **hidden in the Desk** → discoverable via the dashboard sidebar **✎ edit**.
- **No settings** → /settings with real toggles (landing works; theme-light & Arabic shown honestly as not-yet-available).
- Budget **targets** (manual) → per-category, with actual-vs-target bars.
