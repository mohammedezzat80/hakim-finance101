"""Read-only client for the Firefly III API.

HARD RULE (enforced here, in code — not in a prompt):
  This client can ONLY issue HTTP GET requests. `_request` raises if any other
  verb is passed, and there are no create/update/delete methods on this class.
  The agent therefore has no mechanism to initiate a payment, transfer, or any
  change to the ledger. Finance is structurally read-only.
"""
from __future__ import annotations

from typing import Any

import httpx

from .config import config

_ALLOWED_METHODS = {"GET"}


class ReadOnlyViolation(RuntimeError):
    """Raised if anything ever attempts a mutating request."""


class FireflyClient:
    def __init__(self, base_url: str | None = None, token: str | None = None):
        self.base_url = (base_url or config.FIREFLY_URL).rstrip("/")
        self.token = (token if token is not None else config.FIREFLY_PAT).strip()

    @property
    def _headers(self) -> dict:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    # --- core --------------------------------------------------------------
    async def _request(self, method: str, path: str, params: dict | None = None) -> dict:
        if method.upper() not in _ALLOWED_METHODS:
            # Structural guarantee: the agent cannot write to the ledger.
            raise ReadOnlyViolation(
                f"Blocked non-GET request ({method} {path}). Finance is read-only."
            )
        if not self.token:
            raise RuntimeError("FIREFLY_PAT not configured")
        url = f"{self.base_url}/api/v1/{path.lstrip('/')}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(method, url, params=params, headers=self._headers)
            resp.raise_for_status()
            return resp.json()

    async def _get_all(self, path: str, params: dict | None = None) -> list[dict]:
        """GET every page of a paginated Firefly collection."""
        params = dict(params or {})
        params.setdefault("limit", 100)
        page = 1
        out: list[dict] = []
        while True:
            params["page"] = page
            data = await self._request("GET", path, params=params)
            out.extend(data.get("data", []))
            meta = data.get("meta", {}).get("pagination", {})
            if page >= meta.get("total_pages", 1):
                break
            page += 1
        return out

    # --- health ------------------------------------------------------------
    async def ping(self) -> bool:
        try:
            await self._request("GET", "about")
            return True
        except Exception:
            return False

    # --- reads -------------------------------------------------------------
    async def asset_accounts(self) -> list[dict]:
        """Return asset accounts (the books) with balances, normalised."""
        rows = await self._get_all("accounts", {"type": "asset"})
        out = []
        for r in rows:
            a = r.get("attributes", {})
            out.append(
                {
                    "id": r.get("id"),
                    "name": a.get("name"),
                    "balance": float(a.get("current_balance") or 0.0),
                    "currency": a.get("currency_code"),
                    "role": a.get("account_role"),
                }
            )
        return out

    async def categories(self) -> list[str]:
        rows = await self._get_all("categories")
        return [r.get("attributes", {}).get("name") for r in rows if r.get("attributes", {}).get("name")]

    async def transactions(self, ttype: str, start: str, end: str) -> list[dict]:
        """Return flattened transaction splits of a given type in [start, end].

        ttype: 'withdrawal' (spending), 'deposit' (income), or 'all'.
        Dates are YYYY-MM-DD (inclusive).
        """
        params = {"start": start, "end": end}
        if ttype and ttype != "all":
            params["type"] = ttype
        groups = await self._get_all("transactions", params)
        splits: list[dict] = []
        for g in groups:
            for t in g.get("attributes", {}).get("transactions", []):
                splits.append(
                    {
                        "type": t.get("type"),
                        "date": (t.get("date") or "")[:10],
                        "amount": float(t.get("amount") or 0.0),
                        "currency": t.get("currency_code"),
                        "description": t.get("description"),
                        "category": t.get("category_name"),
                        "source": t.get("source_name"),
                        "destination": t.get("destination_name"),
                    }
                )
        return splits
