"""Minimal Firefly III API helper for the setup/seed scripts.

Standard-library only (urllib) so it runs on the host Python with no installs.
Reads FIREFLY_URL and FIREFLY_PAT from the environment or the project .env.
"""
import json
import os
import urllib.error
import urllib.request

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env() -> dict:
    """Load KEY=VALUE lines from the project .env (does not override real env)."""
    env = {}
    path = os.path.join(_PROJECT_ROOT, ".env")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    # real environment wins
    for k in ("FIREFLY_URL", "FIREFLY_PAT"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    env.setdefault("FIREFLY_URL", "http://localhost:8080")
    return env


class Firefly:
    def __init__(self, env: dict):
        self.base = env["FIREFLY_URL"].rstrip("/")
        self.token = env.get("FIREFLY_PAT", "").strip()
        if not self.token:
            raise SystemExit(
                "FIREFLY_PAT is not set. Create a Personal Access Token in Firefly III "
                "(Options → Profile → OAuth → Personal Access Tokens) and add it to .env "
                "as FIREFLY_PAT=... then re-run."
            )

    def _req(self, method: str, path: str, body: dict | None = None):
        url = f"{self.base}/api/v1/{path.lstrip('/')}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/json")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode()
            raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {detail}") from None

    def get(self, path, **params):
        if params:
            from urllib.parse import urlencode
            path = f"{path}?{urlencode(params)}"
        return self._req("GET", path)

    def post(self, path, body):
        return self._req("POST", path, body)

    def get_all(self, path, **params):
        out, page = [], 1
        while True:
            params["page"] = page
            data = self.get(path, **params)
            out.extend(data.get("data", []))
            pg = data.get("meta", {}).get("pagination", {})
            if page >= pg.get("total_pages", 1):
                break
            page += 1
        return out
