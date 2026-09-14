"""Append-only audit log.

Every action the agent takes is written here as one JSON object per line.
The file is only ever opened in append mode ("a") — the agent has no code path
that truncates, rewrites, or deletes it. This is the tamper-evident record of
everything Finance did.
"""
import json
import os
import threading
from datetime import datetime, timezone

from .config import config

_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(event: str, **fields) -> None:
    """Append one structured event to the audit log. Never raises to the caller."""
    record = {"ts": _now_iso(), "event": event, **fields}
    line = json.dumps(record, ensure_ascii=False, default=str)
    try:
        os.makedirs(os.path.dirname(config.LOG_PATH), exist_ok=True)
        with _lock:
            # "a" = append only. Never "w", never seek/truncate.
            with open(config.LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
    except Exception as exc:  # logging must never break a read-only query
        print(f"[audit] failed to write log: {exc}\n[audit] {line}", flush=True)
