# HAKIM — Architecture & Design Rules

## The core rule: one system per domain

**Every domain has exactly one system that owns its data. Each HAKIM agent reads
from its own system. Agents never copy each other's data into one pot.**

| Domain | System of record | HAKIM agent | Status |
|---|---|---|---|
| **Personal money** (your pocket) | **Firefly III** | **Finance** | ✅ live |
| **MENTCO** (medical-devices distribution) | **ERPNext** + intelligence layer | Operations | later |
| **Trading** | **HISSAR** | (HISSAR) | live, external — never mirrored |
| **The factory (name TBD)** (50/50 LLC) | its own books | (later) | when the company exists |

### Why
An agent that owns one domain completely beats an agent that half-owns four.
Making Firefly a mini-ERP that mirrored MENTCO, the factory and trading violated this — it
duplicated data whose system of record lives elsewhere, and blurred Finance's
identity. Firefly is now your **personal ledger only**.

### Cross-domain views happen at the answer layer, not in storage
"What am I worth across everything?" is **not** answered by piling all data into
one database. It's a later agent's job (**Wealth / WAZIR**) that asks Finance,
Operations, and HISSAR each for a summary and combines them **at answer time**.
Aggregation happens in the question, not in the storage.

### The one nuance: money crossing the boundary is personal
Money moving between *you* and *your entities* is your pocket's side of the
transaction, so it lives in Firefly — but only as **categories in the Personal
book**, not as separate books mirroring the entities:

- MENTCO salary/drawings → income category **`Business income`** (what MENTCO pays you)
- Factory capital → expense category **`Capital contribution: Factory`** (capital that
  leaves your book; the factory's own books hold the equity)
- Trading → asset account **`Trading cash (HISSAR)`** (your cash at the broker); transfers
  in/out are personal, while positions/P&L stay in HISSAR

Firefly records that (say) SAR 50,000 left your pocket toward the factory. The factory's
own books record what happened to it after. Neither mirrors the other.

## How Finance behaves (enforced in code)

- **Personal only.** It answers about your personal money.
- **Defers, doesn't guess.** Ask about MENTCO's sales, trading performance, or the
  factory and it names the owning agent instead of answering from data it doesn't
  own. (Personal-side flows — drawings, capital contributions, trading transfers —
  it *does* answer.)
- **Read-only on money.** The Firefly client blocks any non-GET request.
- **Flags low confidence.** Anything it can't classify confidently is flagged.
- **Append-only audit log.** Every action is recorded.
- **Money math in code.** The model only phrases computed figures.

## Runtime shape

```
┌──────────────┐     ┌───────────────┐     ┌─────────────────────┐
│  Open WebUI  │────▶│ Finance Agent │────▶│ Firefly III         │
│  (chat)      │     │ (read-only)   │     │ (PERSONAL ledger)   │
└──────────────┘     └───────────────┘     └─────────────────────┘
        │  Ollama (host, swappable model)         PostgreSQL + Redis

Later: Operations→ERPNext, HISSAR→trading, Wealth/WAZIR→aggregates at answer time.
```
