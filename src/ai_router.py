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
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

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
        "key": os.getenv("GROQ_API_KEY"),  # free tier
        "model": "openai/gpt-oss-120b",  # strongest free groq model
        "min_interval": 2.0,
        "label": "Groq gpt-oss-120b (cloud, fast)",
    },
    "minimax": {
        "url": os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1") + "/chat/completions",
        "key": os.getenv("MINIMAX_API_KEY"),
        "model": os.getenv("MINIMAX_MODEL", "abab6.5s-chat"),
        "min_interval": 2.0,
        "label": "MiniMax abab6.5s (cloud, free tier)",
    },
    # JEV — TypeSafe System One decision brain (typed choices, not chat)
    # Exposed as a special virtual model; /decide endpoint uses it directly.
    "jev": {
        "url": "https://openrouter.ai/api/alpha/decisions",
        "key": os.getenv("OPENROUTER_API_KEY"),
        "model": os.getenv("JEV_MODEL", "~typesafe/jev-latest"),
        "min_interval": 0.0,
        "label": "JEV System One (typed decisions)",
    },
}

CHAINS = {
    "aether-auto": ["ollama-local", "llm7-fast", "llm7-big", "groq", "minimax"],
    "aether-local": ["ollama-local"],
    "aether-cloud": ["llm7-fast", "llm7-big", "groq", "minimax"],
    "aether-groq": ["groq", "llm7-big", "minimax"],
    # aliases so DSH's own default (qwen2.5:3b) also routes through the chain
    "qwen2.5:3b": ["ollama-local", "llm7-fast"],
}

# ── Agent routing (orchestrator merged into router) ──
# each agent model -> {system prompt, brain chain}
AGENT_MODELS = {
    "aether-security": {
        "system": "أنت وكيل أمن سيبراني. تستعمل hack-skills و claude-red و hexstrike للفحص الأمني.",
        "chain": ["ollama-local", "groq", "llm7-big"],
    },
    "aether-research": {
        "system": "أنت باحث. تحلل وتلخص المعلومات من مصادر متعددة.",
        "chain": ["ollama-local", "llm7-fast", "groq"],
    },
    "aether-apollo": {
        "system": (
            "أنت Apollo — deep research meta-agent (coordinateur). "
            "You break a complex query into fundamental sub-questions, "
            "delegate research to sub-agents, then synthesize a cited report. "
            "Think like Athena (research engine) + Hermes (analyzer). "
            "Always cite sources and structure the final answer."
        ),
        "chain": ["llm7-big", "groq", "ollama-local"],
    },
    "aether-market": {
        "system": "أنت محلل أسواق. تحلل البيانات المالية والأسهم.",
        "chain": ["groq", "ollama-local", "llm7-fast"],
    },
    "aether-redteam": {
        "system": "أنت مختبر اختراق. تختبر نقاط الضعف عبر promptfoo.",
        "chain": ["groq", "llm7-big", "ollama-local"],
    },
    "aether-evolve": {
        "system": "أنت محرك تطوير ذاتي. تحلل الأداء وتقترح تحسينات.",
        "chain": ["ollama-local", "llm7-fast"],
    },
    "aether-quality": {
        "system": "أنت مراقب جودة. تصفّي المخرجات وتحسّنها عبر antislop.",
        "chain": ["ollama-local", "llm7-fast"],
    },
    "aether-general": {
        "system": "أنت مساعد عام. تجيب على أي سؤال بوضوح.",
        "chain": ["ollama-local", "llm7-fast", "groq"],
    },
}

# ── Skill loading (hack-skills + claude-red + integrations) ──
# Loads skills from integrations/ so agents can reference them
INTEGRATIONS = Path(__file__).parent.parent / "integrations"
SKILLS_CACHE = {}  # skill_name -> {description, content_preview}


def load_skills():
    """Load skill metadata from integrations (hack-skills + claude-red)."""
    global SKILLS_CACHE
    if SKILLS_CACHE:
        return SKILLS_CACHE

    # hack-skills: site/data/skills.json
    hs = INTEGRATIONS / "hack-skills" / "site" / "data" / "skills.json"
    if hs.exists():
        try:
            data = json.loads(hs.read_text(encoding="utf-8"))
            for s in (data if isinstance(data, list) else data.get("skills", [])):
                name = s.get("name", "")
                if name:
                    SKILLS_CACHE[name] = {
                        "source": "hack-skills",
                        "description": s.get("description", "")[:200],
                    }
        except Exception:
            pass

    # claude-red: claude-skills.json
    cr = INTEGRATIONS / "claude-red" / "claude-skills.json"
    if cr.exists():
        try:
            data = json.loads(cr.read_text(encoding="utf-8"))
            for s in data.get("skills", []):
                name = s.get("name", "")
                if name:
                    SKILLS_CACHE[name] = {
                        "source": "claude-red",
                        "description": s.get("description", "")[:200],
                    }
        except Exception:
            pass

    return SKILLS_CACHE


def skills_for_agent(agent_name: str) -> str:
    """Return a formatted skill list to inject into an agent's system prompt."""
    skills = load_skills()
    if not skills:
        return ""

    # filter by agent domain
    domain_map = {
        "aether-security": ["offensive", "pentest", "ad-", "api-", "cloud", "container", "k8s", "jwt", "oauth", "crypto", "mobile"],
        "aether-redteam": ["offensive", "ai-security", "prompt", "jwt", "oauth", "cicd"],
        "aether-research": ["ai-ml", "research"],
        "aether-apollo": ["ai-ml", "research"],
        "aether-market": [],
        "aether-evolve": [],
        "aether-quality": [],
        "aether-general": [],
    }
    kws = domain_map.get(agent_name, [])
    matched = []
    for name, meta in skills.items():
        if any(kw in name for kw in kws):
            matched.append(f"- {name} ({meta['source']})")

    if not matched:
        return ""

    header = f"\n\nAvailable skills ({len(matched)}):"
    return header + "\n" + "\n".join(matched[:30]) + "\n"


# keyword -> agent (for auto-routing)
AGENT_ROUTES = {
    "aether-security": ["أمن", "اختراق", "ثغرة", "فحص", "pentest", "vuln", "exploit", "hack", "scan", "nmap", "sqlmap", "sécurité"],
    "aether-research": ["ابحث", "بحث", "لخص", "تلخيص", "research", "analyze", "summarize", "find", "cherche"],
    "aether-apollo": ["deep research", "تقرير مفصل", "بحث عميق", "apollo", "athena", "hermes", "comprehensive report", "cite", "synthesize"],
    "aether-market": ["سوق", "أسهم", "أسعار", "تداول", "stock", "market", "price", "crypto", "trading", "bourse"],
    "aether-redteam": ["اختبر", "اختبار", "red team", "promptfoo", "test security", "audit"],
    "aether-evolve": ["طور", "حسّن", "تطوير", "evolve", "improve", "optimize", "améliore"],
    "aether-quality": ["جودة", "راجع", "مراجعة", "quality", "review", "antislop", "check", "تصفية"],
}

VIRTUAL_MODELS = ["aether-auto", "aether-local", "aether-cloud", "aether-groq", "qwen2.5:3b", "aether-decide"] + list(AGENT_MODELS.keys())


def pick_agent(text: str) -> str:
    """Pick the best agent model for the task text."""
    text_lower = text.lower()
    for agent, keywords in AGENT_ROUTES.items():
        if any(kw in text_lower for kw in keywords):
            return agent
    return "aether-general"

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

    # agent model? inject system prompt + use agent chain
    if model in AGENT_MODELS:
        agent = AGENT_MODELS[model]
        messages = payload.get("messages", [])
        # inject system prompt if not present
        if not any(m.get("role") == "system" for m in messages):
            payload = {**payload, "messages": [{"role": "system", "content": agent["system"]}] + messages}
        chain = list(agent["chain"])
    else:
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
                headers={"Cache-Control": "no-cache", "X-Aether-Brain": name, "X-Aether-Model": model},
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
                headers={"X-Aether-Brain": name, "X-Aether-Model": model},
            )

    return jsonify({
        "error": {
            "message": f"all brains failed. last: {last_err}",
            "type": "aether_router_error",
        }
    }), 502


@app.route("/decide", methods=["POST"])
def decide():
    """JEV typed-decision endpoint — pass through to TypeSafe System One.

    Body: {"state": {...}, "questions": {name: {type: choice|noul|score, instructions, criteria}}}
    Returns the raw JEV answer (typed choices + probabilities + confidence).
    """
    if not BRAINS["jev"]["key"]:
        return jsonify({"error": {"message": "OPENROUTER_API_KEY not set", "type": "aether_router_error"}}), 503

    payload = request.get_json(force=True, silent=True) or {}
    state = payload.get("state")
    questions = payload.get("questions")
    if not isinstance(state, dict) or not isinstance(questions, dict):
        return jsonify({"error": {"message": "state and questions must be objects", "type": "bad_request"}}), 400

    body = {
        "model": payload.get("model", BRAINS["jev"]["model"]),
        "state": state,
        "questions": questions,
    }
    try:
        resp = open_brain("jev", body, 30)
    except BrainError as e:
        mark_result("jev", False, str(e))
        return jsonify({"error": {"message": str(e), "type": "aether_router_error"}}), 502

    mark_result("jev", True)
    try:
        data = resp.read()
    finally:
        resp.close()
    return Response(data, status=200, content_type="application/json",
                    headers={"X-Aether-Brain": "jev", "X-Aether-Model": body["model"]})


if __name__ == "__main__":
    port = int(os.getenv("AETHER_ROUTER_PORT", "11435"))
    print(f"🧠 Aether AI Router — {len(BRAINS)} brains, {len(AGENT_MODELS)} agents — port {port}")
    for m in VIRTUAL_MODELS:
        if m in AGENT_MODELS:
            print(f"   agent: {m} → {AGENT_MODELS[m]['chain']}")
        elif m in CHAINS:
            print(f"   model: {m} → {CHAINS[m]}")
        else:
            print(f"   model: {m} → (direct brain)")
    app.run(host="127.0.0.1", port=port, threaded=True)
