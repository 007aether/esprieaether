#!/usr/bin/env python3
"""
orchestrator.py — ONE brain, 11 agents, 5 AI models (DSH ↔ EsprieAether bridge)

DSH (DeepSeek Harness) asks for a "team" → this orchestrator:
  1. picks the right agent(s) for the task
  2. routes through the AI router (5 brains: ollama, llm7-fast, llm7-big, groq, minimax)
  3. returns the result in OpenAI-compatible format (so DSH sees it as one model)

The 11 agents (from GitHub integrations):
  1. hack-skills      (yaklang)      — offensive security skills
  2. claude-red       (SnailSploit)  — red team library
  3. antislop         (sam-paech)    — output quality filter
  4. openclaude       (Twigpine)     — portable runtime
  5. openresearch     (alphaXiv)     — research mode
  6. openstock        (Open-Dev-Soc) — market analysis
  7. pwnproxy         (ericmtzmtz)   — local-first pentest
  8. promptfoo        (promptfoo)    — agent red-teaming
  9. hexstrike        (0x4m4)        — security MCP (143 endpoints)
 10. self-evolve      (built-in)     — self-improvement
 11. router           (built-in)     — 5-brain AI routing

Endpoint: http://127.0.0.1:11436/v1/chat/completions
DSH: custom provider → baseURL http://localhost:11436/v1
"""

import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path

from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

app = Flask(__name__)

# ── CORS: /control page fetches cross-origin ──
@app.after_request
def _cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return resp

ROUTER_URL = os.getenv("AETHER_ROUTER_URL", "http://127.0.0.1:11435")

# ── Agent registry ──
# each agent: name -> {skill, system_prompt, brain_pref}
AGENTS = {
    "security": {
        "skill": "hack-skills + claude-red + hexstrike + pwnproxy",
        "system": "أنت وكيل أمن سيبراني. تستعمل hack-skills و hexstrike للفحص الأمني.",
        "brain": "aether-auto",
    },
    "research": {
        "skill": "openresearch",
        "system": "أنت باحث. تحلل وتلخص المعلومات من مصادر متعددة.",
        "brain": "aether-auto",
    },
    "market": {
        "skill": "openstock",
        "system": "أنت محلل أسواق. تحلل البيانات المالية والأسهم.",
        "brain": "aether-auto",
    },
    "quality": {
        "skill": "antislop",
        "system": "أنت مراقب جودة. تصفّي المخرجات وتحسّنها.",
        "brain": "aether-local",
    },
    "redteam": {
        "skill": "promptfoo + claude-red",
        "system": "أنت مختبر اختراق. تختبر نقاط الضعف.",
        "brain": "aether-cloud",
    },
    "evolve": {
        "skill": "self-evolve",
        "system": "أنت محرك تطوير ذاتي. تحلل الأداء وتقترح تحسينات.",
        "brain": "aether-local",
    },
    "general": {
        "skill": "openclaude",
        "system": "أنت مساعد عام. تجيب على أي سؤال.",
        "brain": "aether-auto",
    },
}

# keyword → agent routing
ROUTES = {
    "security": ["أمن", "اختراق", "ثغرة", "فحص", "pentest", "vuln", "exploit", "hack", "scan", "nmap", "sqlmap"],
    "research": ["ابحث", "بحث", "لخص", "تلخيص", " research", "analyze", "summarize", "find"],
    "market": ["سوق", "أسهم", "أسعار", "تداول", "stock", "market", "price", "crypto", "trading"],
    "redteam": ["اختبر", "اختبار", "red team", "promptfoo", "test security"],
    "evolve": ["طور", "حسّن", "تطوير", "evolve", "improve", "optimize"],
}


def pick_agent(text: str) -> str:
    """Pick the best agent for the task."""
    text_lower = text.lower()
    for agent, keywords in ROUTES.items():
        if any(kw in text_lower for kw in keywords):
            return agent
    return "general"


def call_router(model: str, messages: list, timeout: int = 180) -> dict:
    """Call the AI router (5 brains)."""
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{ROUTER_URL}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": f"router HTTP {e.code}: {e.read().decode('utf-8','replace')[:200]}"}
    except Exception as e:
        return {"error": f"router: {str(e)[:150]}"}


@app.route("/v1/models", methods=["GET"])
def list_models():
    return jsonify({
        "object": "list",
        "data": [
            {"id": f"aether-{name}", "object": "model", "created": int(time.time()), "owned_by": "aether-orchestrator"}
            for name in list(AGENTS.keys()) + ["auto"]
        ],
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "agents": len(AGENTS),
        "router": ROUTER_URL,
    })


@app.route("/v1/chat/completions", methods=["POST"])
def chat():
    payload = request.get_json(force=True, silent=True) or {}
    model = payload.get("model", "aether-auto")
    messages = payload.get("messages", [])
    user_text = ""
    for m in messages:
        if m.get("role") == "user":
            user_text = m.get("content", "")
            break

    # pick agent
    if model.startswith("aether-"):
        agent_name = model.replace("aether-", "")
        if agent_name not in AGENTS:
            agent_name = pick_agent(user_text)
    else:
        agent_name = pick_agent(user_text)

    agent = AGENTS[agent_name]

    # inject system prompt
    full_messages = [{"role": "system", "content": agent["system"]}] + messages

    # call router with agent's preferred brain
    result = call_router(agent["brain"], full_messages)

    if "error" in result:
        return jsonify({"error": {"message": result["error"], "type": "orchestrator_error"}}), 502

    # tag which agent + brain served
    result["agent"] = agent_name
    result["skill"] = agent["skill"]
    return jsonify(result)


@app.route("/")
def index():
    """Root: show agent list + endpoints."""
    return jsonify({
        "service": "Aether Orchestrator",
        "agents": list(AGENTS.keys()),
        "brains": ["ollama-local", "llm7-fast", "llm7-big", "groq", "minimax"],
        "endpoints": {
            "/health": "health check",
            "/v1/models": "list agent models",
            "/v1/chat/completions": "chat (POST)",
            "/group": "group members",
            "/agents": "agent registry",
        },
        "dsh": "baseURL http://localhost:11436/v1",
    })


@app.route("/agents")
def agents():
    """Agent registry with skills."""
    return jsonify({name: {"skill": a["skill"], "brain": a["brain"]} for name, a in AGENTS.items()})


@app.route("/group")
def group():
    """Group members (from cloud desktop agent)."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:5001/group", timeout=4) as r:
            return jsonify(json.loads(r.read()))
    except Exception:
        return jsonify({"members": [], "note": "cloud desktop offline"})


if __name__ == "__main__":
    port = int(os.getenv("AETHER_ORCH_PORT", "11436"))
    print(f"🎯 Aether Orchestrator — {len(AGENTS)} agents, 5 brains — port {port}")
    for name, a in AGENTS.items():
        print(f"   aether-{name}: {a['skill']}")
    app.run(host="127.0.0.1", port=port, threaded=True)
