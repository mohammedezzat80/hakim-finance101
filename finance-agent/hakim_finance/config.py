"""Runtime configuration, read from environment. No secrets baked in."""
import os


class Config:
    # --- Firefly III (read-only target) ---
    FIREFLY_URL = os.environ.get("FIREFLY_URL", "http://firefly:8080").rstrip("/")
    FIREFLY_PAT = os.environ.get("FIREFLY_PAT", "").strip()

    # --- LLM (used ONLY to phrase answers; never to compute money) ---
    OLLAMA_URL = os.environ.get("AGENT_OLLAMA_URL", "http://host.docker.internal:11434").rstrip("/")
    MODEL = os.environ.get("AGENT_MODEL", "qwen2.5:7b-instruct")
    # When False (or model unreachable), the agent replies with clean templated text.
    USE_LLM = os.environ.get("AGENT_USE_LLM", "true").lower() in ("1", "true", "yes")
    LLM_TIMEOUT = float(os.environ.get("AGENT_LLM_TIMEOUT", "45"))
    # Provider switch: "local" = Ollama on your machine · "online" = Gemini API.
    # Runtime toggle via /switch (or POST /v1/provider) overrides this default.
    PROVIDER = os.environ.get("AGENT_PROVIDER", "local").strip().lower()
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    # --- API auth (key Open WebUI presents) ---
    API_KEY = os.environ.get("AGENT_API_KEY", "").strip()

    # --- Behaviour ---
    # Rules-engine confidence below this => FLAG for human review, never guess.
    CONFIDENCE_THRESHOLD = float(os.environ.get("AGENT_CONFIDENCE_THRESHOLD", "0.6"))
    # Currency shown in answers.
    CURRENCY = os.environ.get("AGENT_CURRENCY", "SAR")
    TIMEZONE = os.environ.get("FIREFLY_TZ", "Asia/Riyadh")

    # --- Firefly is the PERSONAL ledger only (one system per domain) ---
    # Finance owns personal money across many accounts (wallets, banks, safes,
    # wallets). Cash position = sum of asset accounts EXCEPT receivables
    # ("Owed to me") which are money owed, not liquid cash.
    RECEIVABLE_MARKERS = ["owed to me", "مستحقات"]

    # Trading cash held at the broker is a PERSONAL asset account (cash only).
    # Transfers to/from it are personal; positions/P&L/performance are HISSAR's.
    TRADING_CASH_ACCOUNT = "Trading cash (HISSAR)"
    # Factory capital leaves the personal book as an expense (not an asset).
    FACTORY_CAPITAL_CATEGORY = "Capital contribution: Factory"

    # Questions about these domains are NOT Finance's to answer. It defers to the
    # owning agent instead of guessing from data it doesn't have.
    # The factory's name is NOT decided — always "the factory (name TBD)".
    # Never hard-code any placeholder name here or in agent output.
    OTHER_DOMAINS = {
        "mentco": "Operations (MENTCO lives in ERPNext)",
        "trading": "HISSAR (trading)",
        "hissar": "HISSAR (trading)",
        "factory": "the factory (name TBD)",
    }

    # --- Audit log (append-only) ---
    LOG_PATH = os.environ.get("AGENT_LOG_PATH", "/app/logs/finance-agent.log")

    MODEL_ID = "hakim-finance"  # what appears in the Open WebUI model list


config = Config()
