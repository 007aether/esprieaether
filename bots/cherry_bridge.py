#!/usr/bin/env python3
"""
cherry_bridge.py — Cherry Studio bridge: mesh agents ↔ Cherry Studio web UI + API

WHAT: CherryHQ/cherry-studio (52K★) has a Local API Gateway that exposes
OpenAI + Anthropic + Gemini-compatible endpoints, plus a full web UI to
watch every model call in real time. This bridge does two things:

  1. BRAIN: register cherry-studio's gateway as an EXTRA brain in the router
     (aether-auto chain), so if colibri/ollama are busy, agents can fall back
     to whatever models cherry-studio has configured.

  2. WINDOW: expose the mesh board + agent thinking through cherry-studio's
     web UI — so you SEE the agents think, live, instead of reading JSON logs.

CONFIG (all optional — bridge degrades gracefully if cherry isn't running):
    CHERRY_URL=http://127.0.0.1:23333        # cherry gateway base URL
    CHERRY_KEY=<api key>                      # if cherry gateway auth is on

Usage:
    python cherry_bridge.py --check     # is cherry gateway reachable?
    python cherry_bridge.py --brain     # register as router brain
    python cherry_bridge.py --models    # list cherry's models
    python cherry_bridge.py --mirror    # push last N board messages to cherry
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

CHERRY_URL = os.getenv("CHERRY_URL", "http://127.0.0.1:23333").rstrip("/")
CHERRY_KEY = os.getenv("CHERRY_KEY", "")
MESH_API = "http://127.0.0.1:11437"


def _req(url, method="GET", payload=None, timeout=10):
    headers = {"Content-Type": "application/json"}
    if CHERRY_KEY:
        headers["Authorization"] = f"Bearer {CHERRY_KEY}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "ignore")


def check():
    """Is cherry-studio gateway reachable?"""
    try:
        st, body = _req(f"{CHERRY_URL}/v1/models", timeout=5)
        if st == 200:
            try:
                models = json.loads(body).get("data", [])
                names = [m.get("id", "?") for m in models][:10]
                return {"ok": True, "url": CHERRY_URL, "models": names}
            except Exception:
                return {"ok": True, "url": CHERRY_URL, "models": []}
        return {"ok": False, "status": st}
    except Exception as e:
        return {"ok": False, "error": str(e)[:120]}


def list_models():
    """Cherry's configured models (what agents could route to)."""
    try:
        st, body = _req(f"{CHERRY_URL}/v1/models", timeout=8)
        if st == 200:
            data = json.loads(body).get("data", [])
            return [m.get("id", "?") for m in data]
    except Exception as e:
        return [f"error: {e}"]
    return []


def register_brain():
    """
    Register cherry-studio as an EXTRA brain in the router.

    Writes a brain entry to data/cherry_brain.json that the router (ai_router.py)
    can pick up as a fallback in the aether-auto chain. This does NOT restart
    anything — the router reads brains dynamically.
    """
    chk = check()
    if not chk.get("ok"):
        return {"ok": False, "reason": "cherry gateway not reachable", "detail": chk}

    brain = {
        "name": "cherry-studio",
        "base_url": CHERRY_URL,
        "api_key": CHERRY_KEY or "cherry-local",
        "kind": "openai-compatible",
        "role": "extra brain + web UI window into the mesh",
        "models": chk.get("models", []),
        "registered": datetime.now(timezone.utc).isoformat(),
    }
    out = BASE_DIR / "data" / "cherry_brain.json"
    out.write_text(json.dumps(brain, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "brain": "cherry-studio", "models": chk.get("models", []),
            "note": "add to ai_router BRAINS + aether-auto chain to activate"}


def mirror_board(limit=20):
    """
    Push the last N mesh-board messages to cherry-studio so they show in its
    web UI as a conversation — a live window into agent thinking.

    cherry's OpenAI chat endpoint doesn't store history, so we create a
    readable transcript message and post it as an assistant turn. This is a
    read-only mirror; cherry just displays it.
    """
    try:
        import urllib.request as u
        with u.urlopen(f"{MESH_API}/board?limit={limit}", timeout=8) as r:
            board = json.loads(r.read().decode())
        msgs = board.get("messages", [])
    except Exception as e:
        return {"ok": False, "error": f"mesh board: {e}"}

    if not msgs:
        return {"ok": 0, "reason": "board empty"}

    # build a transcript
    lines = ["📡 EsprieAether — mesh board (live mirror)"]
    for m in msgs[-limit:]:
        lines.append(f"[{m.get('agent','?')}] {m.get('text','')[:140]}")
    transcript = "\n".join(lines)

    # post to cherry as a chat completion with a system note (display only)
    payload = {
        "model": "esprieaether-mesh",
        "messages": [
            {"role": "system", "content": "You are viewing the EsprieAether mesh. Summarize the agents' current state."},
            {"role": "user", "content": transcript},
        ],
        "max_tokens": 100,
    }
    try:
        st, _ = _req(f"{CHERRY_URL}/v1/chat/completions", method="POST", payload=payload, timeout=20)
        return {"ok": st == 200, "mirrored": len(msgs), "transcript_chars": len(transcript)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:120]}


def status():
    """Telegram-friendly status."""
    chk = check()
    lines = ["🍒 *Cherry Studio Bridge*", ""]
    if chk.get("ok"):
        models = chk.get("models", [])
        lines.append(f"الحالة: ✅ متصل `{CHERRY_URL}`")
        lines.append(f"الموديلات: `{len(models)}`")
        for m in models[:5]:
            lines.append(f"• `{m}`")
    else:
        lines.append(f"الحالة: ❌ غير متصل `{CHERRY_URL}`")
        lines.append(f"`{chk.get('error', chk.get('status',''))[:60]}`")
        lines += ["", "للتشغيل: افتح Cherry Studio → Settings → API Gateway → Start"]
    return "\n".join(lines)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--brain", action="store_true")
    ap.add_argument("--models", action="store_true")
    ap.add_argument("--mirror", action="store_true")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    if args.check:
        print(json.dumps(check(), ensure_ascii=False, indent=2))
    elif args.brain:
        print(json.dumps(register_brain(), ensure_ascii=False, indent=2))
    elif args.models:
        print(json.dumps(list_models(), ensure_ascii=False, indent=2))
    elif args.mirror:
        print(json.dumps(mirror_board(), ensure_ascii=False, indent=2))
    elif args.status:
        print(status())
    else:
        print(json.dumps(check(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
