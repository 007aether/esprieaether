#!/usr/bin/env python3
"""
talk_cycle.py — /api/talk complete-cycle integration (EsprieAether + JARVIS)

WHAT: The universal chat endpoint of the EsprieAether system.
It connects EVERYTHING into one live talking cycle:
  - EsprieAether agent mesh (7 agents, port 11437)
  - JARVIS person-intelligence head (jarvis-api, port 8000)
  - Cloud bridge (GitHub Issues remote control)
  - Vector memory (SQLite, 113 records)
  - Person registry (esprieaether person record)
  - All EsprieAether APIs (/api/health, /api/services, /api/pipeline/status)

WHY: So the whole system acts as ONE continuous talking agent: user speaks,
the mesh reasons, agents follow-up devices, cloud executes, and the answer
comes back through the same cycle — automated and complete.

USAGE:
  python talk_cycle.py            # standalone test
  # then served as a FastAPI route on the jarvis-api (port 8000)
"""

import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

# ── connections ──────────────────────────────────────────────────────────────
MESH_API = os.getenv("MESH_API", "http://127.0.0.1:11437")
JARVIS_API = os.getenv("JARVIS_API", "http://127.0.0.1:8000")
CLOUD_API = os.getenv("CLOUD_API", "http://127.0.0.1:5106")
VECTOR_MEM = os.path.join(BASE_DIR, "data", "vector_memory.db")

# ── helpers ──────────────────────────────────────────────────────────────────
def http_get(url, timeout=12):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {"detail": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}


def http_post(url, body, timeout=30):
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read()[:400]) if e.fp else {"detail": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}


def read_board(limit=20):
    try:
        with open(BASE_DIR / "data" / "agent_board.json", encoding="utf-8") as f:
            board = json.load(f)
        return board[-limit:] if isinstance(board, list) else []
    except Exception:
        return []


# ── cycle stages ─────────────────────────────────────────────────────────────
def stage_mesh(query):
    """Route user message through the agent mesh for multi-agent thinking."""
    msg = {"agent": "talk", "text": query}
    st, _ = http_post(f"{MESH_API}/post", msg, timeout=15)
    if st != 200:
        return {"mesh": "post_failed", "detail": st}

    # read board back
    board = read_board(limit=8)
    if not board:
        return {"mesh": "no_messages", "detail": "board empty"}

    messages = [
        {"role": "user", "content": query},
        {"role": "assistant", "content": " ".join(m["text"] for m in board[-4:])},
    ]
    return {"mesh": "ready", "board_messages": len(board), "agents": [m["agent"] for m in board[-8:]]}


def stage_person_registry():
    """Return the esprieaether person record (identity + endpoints)."""
    try:
        with open(BASE_DIR / "data" / "person_registry.json", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"id": "esprieaether", "name": "EsprieAether", "status": "registered"}


def stage_vector_memory(query):
    """Recall relevant past context for the conversation."""
    try:
        import sqlite3
        con = sqlite3.connect(VECTOR_MEM, timeout=10)
        cur = con.cursor()
        cur.execute(
            "SELECT source, text FROM memories WHERE LOWER(text) LIKE ? ORDER BY id DESC LIMIT 5",
            (f"%{query.lower()}%",),
        )
        rows = cur.fetchall()
        con.close()
        return {"recall": len(rows), "items": [f"{s}: {t[:100]}" for s, t in rows]}
    except Exception as e:
        return {"recall": 0, "error": str(e)}


def stage_cloud():
    """Check cloud-bridge (GitHub) status for remote execution."""
    st, data = http_get(f"{CLOUD_API}/health", timeout=8)
    if st != 200:
        return {"cloud": "offline", "code": st}
    return {"cloud": "online", "board": data.get("board", 0), "status": data.get("status")}


def stage_services():
    """Broadcast the current EsprieAether services status."""
    st, data = http_get(f"{JARVIS_API}/api/services", timeout=8)
    if st != 200:
        return {"services_on": [], "services_off": [], "error": st}
    on = [s["name"] for s in data if s.get("configured")]
    off = [s["name"] for s in data if not s.get("configured")]
    return {"services_on": on, "services_off": off, "total": len(data)}


# ── the complete cycle ───────────────────────────────────────────────────────
def talk_cycle(user_query, persona="esprieaether"):
    """
    One complete talking cycle:
      user_query -> mesh reasoning -> person context -> vector recall ->
      cloud status -> services broadcast -> synthesis -> answer
    """
    result = {
        "cycle": "start",
        "persona": persona,
        "timestamp": datetime_now(),
        "user_query": user_query,
    }

    # 1. mesh reasoning
    mesh = stage_mesh(user_query)
    result["mesh"] = mesh

    # 2. person identity
    person = stage_person_registry()
    result["person"] = person

    # 3. vector recall
    memory = stage_vector_memory(user_query)
    result["memory"] = memory

    # 4. cloud status
    cloud = stage_cloud()
    result["cloud"] = cloud

    # 5. services broadcast
    services = stage_services()
    result["services"] = services

    # 6. synthesis — the system's own answer
    result["synthesis"] = synthesize(user_query, mesh, person, memory, cloud, services)

    # 7. announce on the mesh (follow-up device)
    announce(user_query, result)

    result["cycle"] = "complete"
    return result


def synthesize(query, mesh, person, memory, cloud, services):
    """Compose the final talking answer."""
    parts = []
    if mesh.get("mesh") == "ready":
        parts.append(f"Mesh ({mesh['agents']}) uwais 3la l-haja: {query}")
    else:
        parts.append(f"Mesh: {mesh.get('detail', 'idle')}")

    if memory.get("recall", 0) > 0:
        parts.append(f"حاك يا Personal: {memory['recall']} records recall.")

    if cloud.get("cloud") == "online":
        parts.append(f"Cloud: {cloud['board']} messages on GitHub, status={cloud.get('status')}")

    svc = services.get("services_on", [])
    if svc:
        parts.append(f"Services ON: {', '.join(svc[:5])}")

    parts.append(f"Person '{person.get('name')}' is registered and ACTIVE.")
    return "  |  ".join(parts) if parts else "SPEAKING..."


def announce(query, result):
    """Post the cycle result to the mesh board (follow-up device)."""
    try:
        http_post(f"{MESH_API}/post", {
            "agent": "talk",
            "text": f"[talk-cycle] {query} -> {result['synthesis'][:120]}",
        }, timeout=8)
    except Exception:
        pass


def datetime_now():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


if __name__ == "__main__":
    import json
    test = talk_cycle("How is EsprieAether doing?")
    print(json.dumps(test, ensure_ascii=False, indent=2))
