#!/usr/bin/env python3
"""
jarvis_intel_bridge.py — bridge EsprieAether mesh ↔ JARVIS person-intelligence

WHAT: Connects the EsprieAether agent mesh (7 agents, port 11437) to the
JARVIS person-intelligence platform (FastAPI backend, port 8000).

NOTE: jarvis_bridge.py (separate file) is the Ollama LLM bridge.
This file bridges the JARVIS *intelligence platform* (capture/identify/
research). Two different bridges, two different purposes.

JARVIS capabilities (from its openapi, 14 endpoints):
  - POST /api/capture/*            — image/frame/url capture + face identification
  - POST /api/agents/research      — multi-agent research on a person
  - GET  /api/agents/sessions/{id} — research session status
  - GET  /api/person/{person_id}   — person dossier
  - GET  /api/pipeline/status      — pipeline health
  - GET  /api/services             — which LLM services are configured
  - GET  /api/health               — backend health

Mesh integration:
  - /jarvis Telegram command shows JARVIS status + mesh link
  - /jarvis <name> runs research, stores result in vector memory
  - every finding announced on the mesh board

Usage:
  python jarvis_intel_bridge.py --status           # JARVIS + mesh health
  python jarvis_intel_bridge.py --research <name>  # run research, store in memory
"""

import json
import logging
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = BASE_DIR / "data" / "jarvis_intel_state.json"

JARVIS_API = "http://127.0.0.1:8000"
MESH_API = "http://127.0.0.1:11437"
JARVIS_UI = "http://192.168.0.113:3000"

logger = logging.getLogger("jarvis_intel_bridge")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


def http_get(url, timeout=10):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200]
    except Exception as e:
        return 0, str(e)


def http_post(url, body, timeout=30):
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300]
    except Exception as e:
        return 0, str(e)


def jarvis_status():
    """JARVIS backend health + configured services."""
    st, health = http_get(f"{JARVIS_API}/api/health")
    if st != 200:
        return {"jarvis_online": False, "status": st}
    st2, services = http_get(f"{JARVIS_API}/api/services")
    svc_list = services if isinstance(services, list) else []
    return {
        "jarvis_online": True,
        "env": health.get("environment"),
        "services": health.get("services", {}),
        "services_on": [k for k, v in health.get("services", {}).items() if v],
        "services_off": [k for k, v in health.get("services", {}).items() if not v],
        "configured": [s.get("name") for s in svc_list if s.get("configured")],
    }


def mesh_status():
    st, data = http_get(f"{MESH_API}/health")
    if st != 200:
        return {"mesh_online": False}
    return {"mesh_online": True,
            "agents": data.get("agents"),
            "board": data.get("board")}


def store_in_memory(text, source="jarvis", meta=None):
    """Push a finding into the vector memory (best-effort)."""
    try:
        sys.path.insert(0, str(BASE_DIR / "src"))
        import vector_memory_agent as vma
        vma.add(text, source=source, meta=meta or {})
        return True
    except Exception as e:
        logger.warning(f"memory store failed: {e}")
        return False


def announce_to_mesh(text, agent="jarvis"):
    """Post a message on the mesh board (best-effort)."""
    try:
        st, r = http_post(f"{MESH_API}/board", {"agent": agent, "text": text})
        return st == 200
    except Exception:
        return False


def research(person_name):
    """Run JARVIS multi-agent research on a person, store result in memory."""
    st, resp = http_post(f"{JARVIS_API}/api/agents/research",
                         {"person_name": person_name}, timeout=120)
    if st != 200:
        return {"status": "error", "code": st, "detail": str(resp)[:200]}

    session = resp.get("session_id") or resp.get("task_id") or resp.get("id")
    result = {"status": "started", "session": session, "person": person_name}

    if session:
        for _ in range(20):
            time.sleep(3)
            st2, s = http_get(f"{JARVIS_API}/api/agents/sessions/{session}", timeout=10)
            if st2 == 200 and isinstance(s, dict):
                state = s.get("status") or s.get("state")
                if state in ("complete", "completed", "done", "ready"):
                    result["status"] = "complete"
                    result["dossier"] = s
                    break
                if state in ("failed", "error"):
                    result["status"] = "failed"
                    break
            result["status"] = state or "running"

    if result["status"] in ("complete", "started"):
        mem_text = f"JARVIS research on {person_name}: status={result['status']}"
        if result.get("dossier"):
            mem_text += f" | dossier: {json.dumps(result['dossier'])[:500]}"
        store_in_memory(mem_text, source="jarvis_research",
                        meta={"person": person_name, "session": session})
        announce_to_mesh(f"JARVIS: بحث على {person_name} → {result['status']}")

    save_state(person=person_name, **result)
    return result


def save_state(**kw):
    STATE_FILE.parent.mkdir(exist_ok=True)
    existing = {}
    if STATE_FILE.exists():
        try:
            existing = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    existing.update(kw)
    STATE_FILE.write_text(json.dumps(existing, ensure_ascii=False, indent=2),
                          encoding="utf-8")


def status_report():
    """Full bridge status for Telegram."""
    j = jarvis_status()
    m = mesh_status()
    lines = ["🧠 *JARVIS Intel Bridge*", ""]
    lines.append(f"JARVIS: {'🟢 online' if j.get('jarvis_online') else '🔴 offline'}")
    if j.get("jarvis_online"):
        lines.append(f"• env: `{j.get('env')}`")
        on = j.get("services_on", [])
        lines.append(f"• services on ({len(on)}): `{', '.join(on) if on else '—'}`")
        off = j.get("services_off", [])
        if off:
            lines.append(f"• off: `{', '.join(off[:8])}`")
    lines.append("")
    lines.append(f"Mesh: {'🟢 online' if m.get('mesh_online') else '🔴 offline'}")
    if m.get("mesh_online"):
        lines.append(f"• agents: `{m.get('agents')}` · board: `{m.get('board')}`")
    lines.append("")
    lines.append(f"UI: {JARVIS_UI}")
    lines.append(f"API: {JARVIS_API}")
    return "\n".join(lines)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--research", metavar="PERSON")
    args = ap.parse_args()

    if args.research:
        r = research(args.research)
        print(json.dumps(r, ensure_ascii=False, indent=2)[:1000])
        return

    print(status_report())


if __name__ == "__main__":
    main()
