#!/usr/bin/env python3
"""
ai_router.py — ONE mind, THREE brains (for DSH + any OpenAI-compatible client)

Brains:
  1. ollama-local : qwen2.5:3b            (localhost, free, no rate limit)
  2. llm7-fast    : mistral-Nemo-Instruct (keyless free cloud)
  3. llm7-big     : gpt-oss:20b           (keyless free cloud, stronger)

DSH → http://localhost:11435/v1 (openai-completions) → router picks the brain.

Virtual models (DSH dropdown):
  aether-auto  → local first, cloud fallback (smart: long prompts → big brain)
  aether-local → Ollama only
  aether-cloud → LLM7 only

Extras (added by design):
  - brain health tracking (auto-unhealthy 60s after failure, auto-recover)
  - per-brain rate limiting (LLM7 free = 10 req/min)
  - smart routing: prompts > 8000 chars go to the big brain first
  - /stats endpoint: which brain served what
  - streaming (SSE) + non-streaming
"""

import json
import os
import threading
import time
import urllib.request
import urllib.error

from flask import Flask, request, Response, jsonify

app = Flask(__name__)

# ── Brains ──
BRAINS = {
    "ollama-local": {
        "url": "http://127.0.0.1:11434/v1/chat/completions",
        "key": None,
        "model": "qwen2.5:3b",
        "min_interval": 0.0,
        "label": "Ollama qwen2.5:3b (local)",
    },
    "llm7-fast": {
        "url": "https://api.llm7.io/v1/chat/completions",
        "key": "ollama-local",  # keyless: any value works
        "model": "mistral-Nemo-Instruct-2407",
        "min_interval": 6.5,  # 10 req/min
        "label": "LLM7 mistral-nemo (cloud)",
    },
    "llm7-big": {
        "url": "https://api.llm7.io/v1/chat/completions",
        "key": "ollama-local",
        "model": "gpt-oss:20b",
        "min_interval": 6.5,
        "label": "LLM7 gpt-oss-20b (cloud)",
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": os.getenv("GROQ_API_KEY"),  # free tier, needs signup
        "model": "llama-3.3-70b-versatile",
        "min_interval": 2.0,
        "label": "Groq llama-3.3-70b (cloud, fast)",
    },
    "minimax": {
        "url": os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1") + "/chat/completions",
        "key": os.getenv("MINIMAX_API_KEY"),
        "model": os.getenv("MINIMAX_MODEL", "abab6.5s-chat"),
        "min_interval": 2.0,
        "label": "MiniMax abab6.5s (cloud, free tier)",
    },
}

CHAINS = {
    "aether-auto": ["ollama-local", "llm7-fast", "llm7-big", "groq", "minimax"],
    "aether-local": ["ollama-local"],
    "aether-cloud": ["llm7-fast", "llm7-big", "groq", "minimax"],
    # aliases so DSH's own default (qwen2.5:3b) also routes through the chain
    "qwen2.5:3b": ["ollama-local", "llm7-fast"],
}

VIRTUAL_MODELS = ["aether-auto", "aether-local", "aether-cloud", "qwen2.5:3b"]

_lock = threading.Lock()
_state = {
    name: {"unhealthy_until": 0.0, "last_request": 0.0, "ok": 0, "fail": 0, "last_error": None}
    for name in BRAINS
}


class BrainError(Exception):
    pass


def brain_available(name: str) -> bool:
    with _lock:
        st = _state[name]
        if time.time() < st["unhealthy_until"]:
            return False
        waited = time.time() - st["last_request"]
        return waited >= BRAINS[name]["min_interval"]


def mark_result(name: str, ok: bool, error: str = None):
    with _lock:
        st = _state[name]
        st["last_request"] = time.time()
        if ok:
            st["ok"] += 1
        else:
            st["fail"] += 1
            st["last_error"] = error
            st["unhealthy_until"] = time.time() + 60  # auto-recover after 60s


def _headers(brain) -> dict:
    h = {"Content-Type": "application/json"}
    if brain["key"]:
        h["Authorization"] = f"Bearer {brain['key']}"
    return h


def open_brain(name: str, payload: dict, timeout: int):
    """Open connection to a brain. Returns raw http response. Raises BrainError."""
    brain = BRAINS[name]
    body = dict(payload)
    body["model"] = brain["model"]
    req = urllib.request.Request(
        brain["url"],
        data=json.dumps(body).encode("utf-8"),
        headers=_headers(brain),
        method="POST",
    )
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:200]
        raise BrainError(f"HTTP {e.code}: {detail}")
    except Exception as e:
        raise BrainError(str(e)[:150])


def total_chars(messages) -> int:
    return sum(len(str(m.get("content", ""))) for m in messages or [])


@app.route("/v1/models", methods=["GET"])
def list_models():
    return jsonify({
        "object": "list",
        "data": [
            {"id": m, "object": "model", "created": int(time.time()), "owned_by": "aether-router"}
            for m in VIRTUAL_MODELS
        ],
    })


@app.route("/stats", methods=["GET"])
def stats():
    with _lock:
        return jsonify({
            "brains": {
                name: {
                    **{k: v for k, v in st.items() if k != "unhealthy_until"},
                    "healthy": time.time() >= st["unhealthy_until"],
                    "label": BRAINS[name]["label"],
                }
                for name, st in _state.items()
            }
        })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "brains": len(BRAINS)})


@app.route("/v1/chat/completions", methods=["POST"])
def chat():
    payload = request.get_json(force=True, silent=True) or {}
    model = payload.get("model", "aether-auto")
    chain = list(CHAINS.get(model, CHAINS["aether-auto"]))

    # smart routing: long prompts → big brain first
    if model == "aether-auto" and total_chars(payload.get("messages")) > 8000 and "llm7-big" in chain:
        chain = ["llm7-big"] + [b for b in chain if b != "llm7-big"]

    stream = bool(payload.get("stream"))
    timeout = 180 if stream else 120
    last_err = None

    for name in chain:
        if not brain_available(name):
            continue
        try:
            resp = open_brain(name, payload, timeout)
        except BrainError as e:
            mark_result(name, False, str(e))
            last_err = f"{name}: {e}"
            continue

        mark_result(name, True)

        if stream:
            def generate():
                try:
                    for line in resp:
                        yield line
                finally:
                    resp.close()
            return Response(
                generate(),
                status=200,
                content_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Aether-Brain": name},
            )
        else:
            try:
                data = resp.read()
            finally:
                resp.close()
            return Response(
                data,
                status=200,
                content_type="application/json",
                headers={"X-Aether-Brain": name},
            )

    return jsonify({
        "error": {
            "message": f"all brains failed. last: {last_err}",
            "type": "aether_router_error",
        }
    }), 502


if __name__ == "__main__":
    port = int(os.getenv("AETHER_ROUTER_PORT", "11435"))
    print(f"🧠 Aether AI Router — ONE mind, THREE brains — port {port}")
    for m in VIRTUAL_MODELS:
        print(f"   model: {m} → {CHAINS[m]}")
    app.run(host="127.0.0.1", port=port, threaded=True)
