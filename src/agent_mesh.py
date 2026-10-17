#!/usr/bin/env python3
"""
agent_mesh.py — Local agent-to-agent communication bus

WHAT: Agents currently only respond to user requests. This module makes them
talk to EACH OTHER autonomously: each agent posts insights/improvements/ideas
to a shared board, and other agents can read + build on them. This is how the
system evolves without waiting for a user prompt.

WHY: The router (11435) + orchestrator (11436) are REQUEST-RESPONSE only.
The autonomous_loop runs tasks on a schedule, but tasks are fixed.
A message board + agent reflection loop turns 7 agents into a self-organizing
system: each cycle, an agent reads the board, reacts to what others said,
and posts its own contribution.

HOW:
  1. Shared message board: data/agent_board.json (JSON list, capped at 200 msgs)
  2. Agent persona loop: each agent gets a turn — reads last N messages,
     generates a reaction via the router (aether-<agent>), posts result
  3. Task generation: agents can propose tasks; autonomous_loop picks them up
  4. HTTP API: /board (read), /post (write), /think (force one agent cycle),
     /agents, /health

Port: 11437 (after router 11435 + orchestrator 11436)
"""

import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
BOARD_FILE = BASE_DIR / "data" / "agent_board.json"
PROPOSED_FILE = BASE_DIR / "data" / "agent_proposed_tasks.json"

ROUTER_URL = os.getenv("AETHER_ROUTER_URL", "http://127.0.0.1:11435")

MAX_MESSAGES = 200
MAX_TASKS = 50

# ── Agent personas (aligned with orchestrator AGENTS) ──
AGENTS = {
    "security": {
        "role": "وكيل الأمن",
        "prompt": "أنت وكيل أمن سيبراني في نظام EsprieAether المحلي. راجع آخر ما قاله الوكلاء الآخرون واقترح تحسينات أمنية أو تحذيرات. كن موجزاً (3 جمل).",
        "tags": ["security", "audit", "vuln"],
    },
    "research": {
        "role": "وكيل البحث",
        "prompt": "أنت باحث في نظام EsprieAether. اقرأ أفكار الوكلاء الآخرين واقترح موضوع بحث أو معلومة جديدة تفيد النظام. كن موجزاً (3 جمل).",
        "tags": ["research", "knowledge", "idea"],
    },
    "market": {
        "role": "وكيل الأسواق",
        "prompt": "أنت محلل أسواق في نظام EsprieAether. علّق على فرص الربح أو البيانات المالية التي ذكرها الآخرون. كن موجزاً (3 جمل).",
        "tags": ["market", "revenue", "opportunity"],
    },
    "quality": {
        "role": "وكيل الجودة",
        "prompt": "أنت مراقب جودة في نظام EsprieAether. راجع ما قاله الآخرون واقترح كيف نرفع جودة المخرجات. كن موجزاً (3 جمل).",
        "tags": ["quality", "improve", "review"],
    },
    "redteam": {
        "role": "وكيل الاختبار",
        "prompt": "أنت مختبر في نظام EsprieAether. ابحث عن ثغرات في أفكار الآخرون واختبرها بذكاء. كن موجزاً (3 جمل).",
        "tags": ["test", "challenge", "verify"],
    },
    "evolve": {
        "role": "وكيل التطوير",
        "prompt": "أنت محرك التطوير الذاتي لنظام EsprieAether. اقرأ كل الرسائل واستنتج مهمة واحدة قابلة للتنفيذ لتحسين النظام. كن موجزاً (3 جمل).",
        "tags": ["evolve", "task", "improve"],
    },
    "general": {
        "role": "المساعد العام",
        "prompt": "أنت المساعد العام لنظام EsprieAether. لخّص ما دار بين الوكلاء واذكر الخطوة القادمة الأهم. كن موجزاً (3 جمل).",
        "tags": ["summary", "next", "coordination"],
    },
    "rea": {
        "role": "وكيل الهندسة العكسية",
        "prompt": "أنت وكيل الهندسة العكسية (REA) في نظام EsprieAether. عندك أداة rea_agent.py كتحلل binaries و apps و مواقع. اقرأ أفكار الوكلاء واقترح هدف يستحق التحليل (تطبيق، ميزة، منافس) مع السبب. كن موجزاً (3 جمل).",
        "tags": ["reverse", "analyze", "understand", "rea"],
    },
}


# ── Board persistence ──
def load_board():
    if BOARD_FILE.exists():
        try:
            return json.loads(BOARD_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_board(board):
    BOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    # keep last MAX_MESSAGES
    if len(board) > MAX_MESSAGES:
        board = board[-MAX_MESSAGES:]
    BOARD_FILE.write_text(json.dumps(board, ensure_ascii=False, indent=2), encoding="utf-8")


def load_tasks():
    if PROPOSED_FILE.exists():
        try:
            return json.loads(PROPOSED_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_tasks(tasks):
    PROPOSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    if len(tasks) > MAX_TASKS:
        tasks = tasks[-MAX_TASKS:]
    PROPOSED_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def post_message(agent, text, tags=None):
    board = load_board()
    msg = {
        "id": f"{int(time.time()*1000)}-{agent}",
        "agent": agent,
        "text": text,
        "tags": tags or [],
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    board.append(msg)
    save_board(board)
    return msg


def propose_task(agent, title, description):
    tasks = load_tasks()
    task = {
        "id": f"task-{int(time.time()*1000)}",
        "agent": agent,
        "title": title,
        "description": description,
        "status": "proposed",
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    tasks.append(task)
    save_tasks(tasks)
    return task


# ── Router call ──
def call_router(model, messages, timeout=90):
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


def agent_think(agent_name, last_n=8):
    """One agent reads the board + recalls memory and posts its reaction."""
    if agent_name not in AGENTS:
        return {"error": f"unknown agent: {agent_name}"}

    board = load_board()
    recent = board[-last_n:] if board else []

    # ── recall relevant memories (vector memory) ──
    memory_context = ""
    try:
        import vector_memory_agent as vma
        vm = vma.VectorMemory()
        # build a query from the agent's role + recent board
        query = f"{AGENTS[agent_name]['role']} {' '.join(m['text'][:50] for m in recent[-3:])}"
        hits = vm.recall(query, limit=3)
        vm.close()
        if hits:
            memory_context = "\n".join(
                f"- [{h.get('source','?')}] {h.get('text','')[:120]}" for h in hits
            )
    except Exception:
        pass  # memory optional — never block the agent

    # build context from board + memory
    parts = []
    if recent:
        parts.append("آخر ما قاله الوكلاء:\n" + "\n".join(f"[{m['agent']}]: {m['text']}" for m in recent))
    if memory_context:
        parts.append("ما نتذكره من الذاكرة:\n" + memory_context)
    parts.append(AGENTS[agent_name]["prompt"])
    user_msg = "\n\n".join(parts)

    messages = [
        {"role": "system", "content": f"أنت {AGENTS[agent_name]['role']} في نظام EsprieAether متعدد الوكلاء. أجيب بالعربية أو الدارجة، موجز."},
        {"role": "user", "content": user_msg},
    ]

    result = call_router(f"aether-{agent_name}", messages)
    if "error" in result:
        return result

    text = ""
    try:
        text = result["choices"][0]["message"]["content"]
    except Exception:
        text = str(result)[:300]

    if not text.strip():
        return {"error": "empty response from router"}

    # ── store the thought in memory ──
    try:
        import vector_memory_agent as vma
        vm = vma.VectorMemory()
        vm.remember(f"[{agent_name}] {text.strip()[:200]}", source=f"mesh_{agent_name}")
        vm.close()
    except Exception:
        pass

    msg = post_message(agent_name, text.strip(), AGENTS[agent_name]["tags"])

    # evolve agent may propose a task
    task = None
    if agent_name == "evolve" and len(text) > 20:
        first_line = text.split("\n")[0][:100]
        task = propose_task(agent_name, first_line, text[:500])

    return {"posted": msg, "task": task, "agent": agent_name}


def mesh_cycle(rounds=2):
    """Full mesh cycle: each agent thinks once, in order."""
    results = []
    order = ["evolve", "security", "research", "market", "quality", "redteam", "general"]
    for r in range(rounds):
        for agent in order:
            res = agent_think(agent)
            results.append({
                "agent": agent,
                "ok": "posted" in res,
                "text": res.get("posted", {}).get("text", res.get("error", ""))[:120],
                "task": res.get("task"),
            })
            time.sleep(2)  # avoid hammering the router
    return results


# ── HTTP API ──
@app.route("/")
def index():
    board = load_board()
    tasks = load_tasks()
    return jsonify({
        "service": "Aether Agent Mesh",
        "agents": list(AGENTS.keys()),
        "board_messages": len(board),
        "proposed_tasks": len(tasks),
        "endpoints": {
            "/board": "read messages (GET, ?limit=N&agent=X)",
            "/post": "post a message (POST {agent, text, tags})",
            "/think": "force one agent to think (POST {agent})",
            "/cycle": "run a full mesh cycle (POST {rounds})",
            "/tasks": "proposed tasks (GET)",
            "/agents": "agent registry",
            "/health": "health check",
        },
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "router": ROUTER_URL,
        "board": len(load_board()),
        "agents": len(AGENTS),
    })


@app.route("/board")
def board_get():
    limit = int(request.args.get("limit", 50))
    agent = request.args.get("agent")
    board = load_board()
    if agent:
        board = [m for m in board if m.get("agent") == agent]
    return jsonify({"messages": board[-limit:], "total": len(board)})


@app.route("/post", methods=["POST"])
def board_post():
    data = request.get_json(force=True, silent=True) or {}
    agent = data.get("agent", "general")
    text = data.get("text", "")
    tags = data.get("tags", [])
    if not text:
        return jsonify({"error": "text required"}), 400
    msg = post_message(agent, text, tags)
    return jsonify({"posted": msg})


@app.route("/think", methods=["POST"])
def think():
    data = request.get_json(force=True, silent=True) or {}
    agent = data.get("agent", "general")
    result = agent_think(agent)
    return jsonify(result)


@app.route("/cycle", methods=["POST"])
def cycle():
    data = request.get_json(force=True, silent=True) or {}
    rounds = int(data.get("rounds", 1))
    rounds = max(1, min(rounds, 5))
    results = mesh_cycle(rounds=rounds)
    return jsonify({
        "cycle": "done",
        "rounds": rounds,
        "agents_thought": len(results),
        "results": results,
        "board_total": len(load_board()),
    })


@app.route("/tasks")
def tasks_get():
    return jsonify({"tasks": load_tasks()})


@app.route("/agents")
def agents_get():
    return jsonify({
        name: {"role": a["role"], "tags": a["tags"]}
        for name, a in AGENTS.items()
    })


if __name__ == "__main__":
    port = int(os.getenv("AETHER_MESH_PORT", "11437"))
    print(f"🕸️  Aether Agent Mesh — {len(AGENTS)} agents — port {port}")
    for name, a in AGENTS.items():
        print(f"   {name}: {a['role']}")
    app.run(host="0.0.0.0", port=port, threaded=True)
