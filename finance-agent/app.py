"""HAKIM Finance — OpenAI-compatible API server.

Open WebUI connects to this as an "OpenAI API" endpoint, so "HAKIM Finance"
shows up as a selectable model in the chat window. The user talks to it like any
normal chat; under the hood every answer is computed from Firefly III (read-only)
and only phrased by the local model.

Endpoints:
  GET  /health
  GET  /v1/models
  POST /v1/chat/completions   (stream + non-stream)
"""
from __future__ import annotations

import json
import time

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from hakim_finance import __version__
from hakim_finance.audit import log
from hakim_finance.config import config
from hakim_finance.firefly import FireflyClient
from hakim_finance.intents import answer as intent_answer
from hakim_finance.llm import phrase, get_provider, set_provider, available as llm_available

app = FastAPI(title="HAKIM Finance", version=__version__)
ff = FireflyClient()

DISCLAIMER = "\n\n_HAKIM Finance is read-only. I never move money — I only read your ledger._"


def _check_auth(authorization: str | None) -> None:
    if not config.API_KEY:
        return  # auth disabled
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token != config.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/health")
async def health():
    ff_ok = await ff.ping()
    return {"status": "ok", "version": __version__, "firefly_reachable": ff_ok,
            "model": config.MODEL}


@app.get("/v1/models")
async def list_models(authorization: str | None = Header(default=None)):
    _check_auth(authorization)
    return {
        "object": "list",
        "data": [{
            "id": config.MODEL_ID,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "hakim",
        }],
    }


async def _produce_answer(question: str) -> str:
    """Run the read-only pipeline and return the final answer text."""
    log("query_received", question=question)
    try:
        result = await intent_answer(question, ff)
    except Exception as exc:
        msg = str(exc)
        if "FIREFLY_PAT not configured" in msg:
            log("firefly_token_missing")
            return ("My Firefly III token isn't set yet, so I can't read your ledger. "
                    "Add your new token to `.env` as `FIREFLY_PAT=…` and restart me "
                    "(`docker compose up -d finance-agent`).")
        if "401" in msg or "Unauthenticated" in msg:
            log("firefly_auth_error", error=msg)
            return ("I can't reach your Firefly III ledger — the API token was "
                    "rejected (401). Check that FIREFLY_PAT in .env is current.")
        log("error", error=msg)
        return f"Sorry, I hit an error reading the ledger: {msg}"

    text = result.text
    used_llm = False
    if result.allow_llm and config.USE_LLM and result.facts:
        phrased = await phrase(question, result.facts)
        if phrased:
            text = phrased
            used_llm = True

    log("query_answered", intent=result.intent, flagged=result.flagged,
        used_llm=used_llm, facts=result.facts)
    return text + DISCLAIMER


def _extract_question(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            c = m.get("content", "")
            if isinstance(c, list):  # OpenAI content-parts form
                c = " ".join(p.get("text", "") for p in c if isinstance(p, dict))
            return c
    return ""


@app.post("/v1/chat/completions")
async def chat_completions(request: Request, authorization: str | None = Header(default=None)):
    _check_auth(authorization)
    body = await request.json()
    messages = body.get("messages", [])
    stream = bool(body.get("stream", False))
    question = _extract_question(messages)

    if not question.strip():
        answer_text = "Ask me about your finances — e.g. \"what's my cash position?\""
    else:
        answer_text = await _produce_answer(question)

    created = int(time.time())
    cid = f"chatcmpl-hakim-{created}"

    if not stream:
        return JSONResponse({
            "id": cid, "object": "chat.completion", "created": created,
            "model": config.MODEL_ID,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": answer_text},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        })

    async def event_stream():
        # role chunk
        first = {"id": cid, "object": "chat.completion.chunk", "created": created,
                 "model": config.MODEL_ID,
                 "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]}
        yield f"data: {json.dumps(first)}\n\n"
        # content chunk (single block — answer is already fully computed)
        content = {"id": cid, "object": "chat.completion.chunk", "created": created,
                   "model": config.MODEL_ID,
                   "choices": [{"index": 0, "delta": {"content": answer_text}, "finish_reason": None}]}
        yield f"data: {json.dumps(content)}\n\n"
        done = {"id": cid, "object": "chat.completion.chunk", "created": created,
                "model": config.MODEL_ID,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
        yield f"data: {json.dumps(done)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


async def provider_get(authorization: str | None = Header(default=None)):
    return await llm_available()


async def provider_set(request: Request, authorization: str | None = Header(default=None)):
    body = await request.json()
    p = set_provider(str(body.get("provider", "")).lower())
    log("provider_switched", provider=p)
    return await llm_available()


_SWITCH_HTML = """<!doctype html><meta charset=utf-8><title>HAKIM · AI provider</title>
<style>body{background:#0D0F16;color:#E8EAF2;font:15px/1.5 -apple-system,sans-serif;display:grid;place-items:center;min-height:100vh;margin:0}
.card{background:#151827;border:.5px solid #232840;border-radius:14px;padding:24px;width:min(420px,92vw)}
h1{font-size:16px;margin:0 0 6px;letter-spacing:.06em}.sub{color:#5C637A;font-size:13px;margin-bottom:18px}
.opt{display:flex;justify-content:space-between;align-items:center;padding:12px 14px;border:.5px solid #232840;border-radius:10px;margin-top:8px;cursor:pointer}
.opt.on{border-color:#72D5C8;background:#1A1E33}.opt small{display:block;color:#9BA3C9;font-size:12px}
.dot{width:8px;height:8px;border-radius:50%;background:#5C637A;display:inline-block;margin-right:8px}.dot.ok{background:#72D5C8}
.note{color:#5C637A;font-size:12px;margin-top:16px}</style>
<div class=card><h1>ASK FINANCE · AI PROVIDER</h1><div class=sub>which model phrases the answers — the numbers are always computed locally</div>
<div id=local class=opt onclick="pick('local')"><div><span id=ld class=dot></span>Local · Ollama<small id=lm></small></div><b id=lb></b></div>
<div id=online class=opt onclick="pick('online')"><div><span id=od class=dot></span>Online · Gemini<small id=om></small></div><b id=ob></b></div>
<div class=note>Online mode sends only the question + the computed facts for that answer. The ledger never leaves. Local mode sends nothing anywhere.</div></div>
<script>
async function load(){const s=await (await fetch('/v1/provider')).json();
 document.getElementById('local').classList.toggle('on',s.provider==='local');document.getElementById('online').classList.toggle('on',s.provider==='online');
 document.getElementById('ld').classList.toggle('ok',s.local);document.getElementById('od').classList.toggle('ok',s.online);
 document.getElementById('lm').textContent=s.local_model+(s.local?' · reachable':' · not reachable');
 document.getElementById('om').textContent=s.online_model+(s.online?' · key set':' · GEMINI_API_KEY missing');
 document.getElementById('lb').textContent=s.provider==='local'?'active':'';document.getElementById('ob').textContent=s.provider==='online'?'active':'';}
async function pick(p){await fetch('/v1/provider',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({provider:p})});load();}
load();</script>"""


async def switch_page():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(_SWITCH_HTML)


app.add_api_route("/v1/provider", provider_get, methods=["GET"])
app.add_api_route("/v1/provider", provider_set, methods=["POST"])
app.add_api_route("/switch", switch_page, methods=["GET"])



@app.on_event("startup")
async def _startup():
    log("agent_started", version=__version__, model=config.MODEL,
        firefly_url=config.FIREFLY_URL, read_only=True)
