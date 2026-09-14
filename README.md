# HAKIM

A private, self-hosted personal AI system. This repo is the foundation plus the
first agent: **Finance** — a read-only assistant for your **personal** money that
you talk to in a normal chat window.

> **Design rule:** one system per domain. Firefly III = personal money, ERPNext =
> MENTCO, HISSAR = trading, the factory (name TBD) gets its own books later. Each agent reads only its
> own system; cross-domain "what am I worth everywhere" is a later agent's job
> (Wealth/WAZIR) that aggregates **at answer time**. See **[ARCHITECTURE.md](ARCHITECTURE.md)**.

```
┌──────────────┐     ┌───────────────┐     ┌─────────────────────┐
│  Open WebUI  │────▶│ Finance Agent │────▶│  Firefly III        │
│  (chat,3000) │     │ (read-only,   │     │  (PERSONAL ledger,  │
└──────┬───────┘     │  8000)        │     │   8080)             │
       │             └───────┬───────┘     └──────────┬──────────┘
       ▼                     ▼                         ▼
   Ollama (host)      append-only log          PostgreSQL + Redis
  qwen2.5:7b-instruct  finance-agent.log         (shared platform)

        Homepage (launcher, 3001) ties it all together.
```

## Services

| Service        | URL                     | Purpose                                  |
|----------------|-------------------------|------------------------------------------|
| Open WebUI     | http://localhost:3000   | Chat interface (talk to HAKIM/Finance)   |
| Homepage       | http://localhost:3001   | Dashboard launcher + live status         |
| Firefly III    | http://localhost:8080   | **Personal** finance ledger (SAR)        |
| Finance Agent  | http://localhost:8000   | Read-only personal finance API (via chat)|
| PostgreSQL     | (internal)              | Shared database                          |
| Redis          | (internal)              | Shared cache                             |

The LLM runs on the **host** via Ollama (`qwen2.5:7b-instruct`), reachable from
containers at `host.docker.internal:11434`. It is **swappable** — change
`AGENT_MODEL` in `.env` (e.g. to a GLM endpoint later) and restart the agent.

## Start / stop

```bash
cd ~/Documents/Hakim
docker compose up -d        # start everything
docker compose down         # stop (keeps data)
docker compose down -v      # stop and WIPE all data
docker compose logs -f finance-agent
docker compose ps
```

Ollama (host) is managed separately: `brew services start|stop ollama`, `ollama list`.

## First-time setup

1. **Open WebUI** — http://localhost:3000, create the admin account (first account
   is the owner). Pick `qwen2.5:7b-instruct` for general chat or `hakim-finance`
   for finance questions.
2. **Firefly III** — http://localhost:8080, register the admin account, then create
   an API token at **Options → Remote access and tokens → Personal Access Tokens →
   Create new token** (Firefly v6.6.x). It's a long JWT starting with `eyJ…`, shown
   once. Put it in `.env` as `FIREFLY_PAT=…`.
3. **Personal ledger structure** (v2 — accounts, categories, tags, bills; idempotent):
   ```bash
   python3 scripts/build_structure.py   # spec: HAKIM_Finance_Structure_v2.md
   ```
   Then enter your **true opening balances** per account from your bank apps.
4. **Finance agent** — build/start and (already wired) selectable in Open WebUI:
   ```bash
   docker compose up -d --build finance-agent
   ```

### Putting in your real data
- **Set your true opening balance** on the Personal account (Firefly → account →
  edit → opening balance = your actual cash/bank position today).
- **Enter your real expenses** as you go.
- **Add recurring transactions** for fixed items (rent, subscriptions, school fees).
- Optional demo data (fake, personal-only, empty ledger only):
  `DEMO=1 python3 scripts/seed_firefly.py`  · undo with `python3 scripts/reset_ledger.py`.

## Talking to Finance

Pick **HAKIM Finance** in the model dropdown and ask, in plain language:

- "What's my cash position?"
- "How much did I spend on groceries last month?"
- "Give me a spending breakdown for this month."
- "How much did I draw from MENTCO this year?" (personal side of a boundary flow)
- "How much capital did I contribute to the factory?"
- "Categorise: Nahdi pharmacy 220"

Ask it about **MENTCO's sales, trading performance, or the factory** and it will
tell you that's another agent's domain and decline to guess — that's by design.

## Hard rules (enforced in code, not prompts)

- **Personal only + defers.** Finance answers about your personal money; business
  and trading questions are deferred to the owning agent (`intents.py`).
- **Read-only on money.** `finance-agent/hakim_finance/firefly.py` blocks any
  non-GET request and exposes no write methods.
- **Never guesses.** Low-confidence categorisation or unmapped questions are
  **flagged** for review (`rules.py` / `intents.py`).
- **Append-only audit log.** Every action → `finance-agent/logs/finance-agent.log`
  (open mode `"a"` only, `audit.py`).
- **Money math in code.** All figures are computed in Python from Firefly; the
  model only phrases them.

## Secrets

Secrets live in `.env` (local only, never commit). To rotate the Postgres
password: `ALTER ROLE hakim WITH PASSWORD '…'` in the DB, update `.env`, then
`docker compose up -d`. To rotate the agent key: update `AGENT_API_KEY` in `.env`
and the `openai.api_keys` row in Open WebUI's `config` table, then recreate.
For a new Firefly token: delete the old one in Firefly, create a new one, paste
into `.env`, `docker compose up -d finance-agent`.

## Project layout

```
docker-compose.yml        # the whole stack
.env                      # secrets & config (local only)
ARCHITECTURE.md           # design rules (one system per domain)
postgres/init/            # creates per-service databases
homepage/config/          # Homepage launcher config
finance-agent/            # the Finance agent (FastAPI, OpenAI-compatible)
  hakim_finance/          # firefly (read-only), rules, intents, llm, audit
scripts/                  # build_structure.py (v2 builder), reset_ledger.py, _ff.py
HAKIM_Finance_Structure_v2.md  # the finance structure specification
STATE.md                  # running build state
```

> Firefly holds your **personal** money only. Real data lives here; business and
> trading data live in their own systems.
