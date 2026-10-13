#!/usr/bin/env python3
"""
dsh_bridge.py — DeepSeek Harness ⇄ EsprieAether bridge

DSH (DeepSeek Harness) is a Chromium app with browser permissions.
This bridge lets the EsprieAether router/orchestrator drive DSH for
web tasks (Netlify claim, GMB, Pinterest, etc.) without a human.

How DSH is driven:
  - DSH listens on port 19387 (CDP) when running.
  - We connect via CDP and evaluate JS / click / type.
  - Falls back to keyboard+window automation if CDP is blocked.

Endpoints this bridge exposes on port 5101:
  GET  /health        — bridge alive + DSH detected
  POST /open          — {"url": "..."} open a URL in DSH
  POST /click         — {"selector": "..."} click
  POST /type          — {"selector": "...", "text": "..."}
  GET  /state         — current page title/url/body-excerpt
"""

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = Flask(__name__)
PORT = int(os.getenv("DSH_BRIDGE_PORT", "5101"))
DSH_PORT = 19387
CDP_URL = f"http://127.0.0.1:{DSH_PORT}"


def _dsh_running() -> bool:
    try:
        with urllib.request.urlopen(CDP_URL + "/json/version", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def _cdp_targets() -> list:
    try:
        with urllib.request.urlopen(CDP_URL + "/json/list", timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception:
        return []


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "dsh_running": _dsh_running(),
        "dsh_cdp": CDP_URL,
        "targets": len(_cdp_targets()),
    })


@app.route("/state")
def state():
    targets = _cdp_targets()
    pages = [t for t in targets if t.get("type") == "page"]
    if not pages:
        return jsonify({"ok": False, "targets": targets})
    return jsonify({"ok": True, "pages": [{"url": p.get("url"), "title": p.get("title")} for p in pages]})


@app.route("/open", methods=["POST"])
def open_url():
    """Open a URL in DSH via Windows shell (DSH is the default for its app)."""
    url = (request.get_json(silent=True) or {}).get("url", "")
    if not url:
        return jsonify({"error": "need url"}), 400
    # Best: use CDP if a page target exists, else launch DSH with the URL
    if sys.platform == "win32":
        subprocess.Popen(["cmd", "/c", "start", url])
    else:
        subprocess.Popen(["xdg-open", url])
    return jsonify({"ok": True, "url": url, "note": "opened via default handler; use /click + /type once DSH shows it"})


@app.route("/click", methods=["POST"])
def click():
    sel = (request.get_json(silent=True) or {}).get("selector", "")
    return jsonify({"ok": False, "note": "CDP click not wired in this build; use DSH UI or Hermes browser", "selector": sel})


@app.route("/type", methods=["POST"])
def type_text():
    return jsonify({"ok": False, "note": "use Hermes browser_exec for typing; DSH has no REST type"})


if __name__ == "__main__":
    print(f"🌉 DSH bridge — DSH CDP {CDP_URL} (running={_dsh_running()}) — port {PORT}")
    app.run(host="127.0.0.1", port=PORT, threaded=True)
