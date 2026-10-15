#!/usr/bin/env python3
"""
rea_agent.py — REA (Reverse Engineer Anything) integration for EsprieAether

WHAT: Wraps the REA CLI (`npx rea-agents`) so the EsprieAether mesh can
reverse-engineer binaries, JS/Electron apps, and websites WITHOUT every
agent needing to know REA's internals.

REA is an MCP-based RE tool (github.com/morluto/rea, 226k★). On Windows
it supports native PE analysis via Ghidra (experimental P0) + JS/Electron
+ website observation. macOS/Linux get the full Hopper/Ghidra stack.

This module gives EsprieAether:
  1. A mesh agent 'rea' — handles "understand how X works" requests
  2. CLI wrappers: analyze / doctor / inventory — JSON in, JSON out
  3. Results stored in vector memory (recallable later)
  4. Findings announced on the mesh board

Usage (CLI):
  python rea_agent.py --doctor           # REA health on this host
  python rea_agent.py --analyze <path>   # analyze a binary/app
  python rea_agent.py --status           # mesh + REA status (Telegram)

Usage (from mesh / bot):
  from rea_agent import analyze, doctor, status_report
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = BASE_DIR / "data" / "rea_state.json"
LOG_FILE = BASE_DIR / "data" / "logs" / "rea_agent.log"

MESH_API = "http://127.0.0.1:11437"
REA_CMD_TIMEOUT = 600  # binary analysis can take a while

logger = logging.getLogger("rea_agent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


# ── REA CLI runner ───────────────────────────────────────────────────
def _rea_available():
    """Is the rea CLI callable? (global install or npx fallback)."""
    # check PATH
    found = shutil.which("rea")
    if found:
        return [found]
    # Hermes-managed node dir (where npm --global installed it)
    node_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / "tools" / "node-26.7.0-win32-x64"
    rea_bat = node_dir / "rea.cmd"
    rea_exe = node_dir / "rea"
    for p in (rea_exe, rea_bat):
        if p.exists():
            return [str(p)]
    # npx fallback (slower but always works if npm present)
    if shutil.which("npx"):
        return ["npx", "--yes", "rea-agents@latest"]
    return None


def run_rea(args, timeout=REA_CMD_TIMEOUT):
    """Run a rea command. Returns (returncode, stdout, stderr)."""
    cmd = _rea_available()
    if not cmd:
        return -1, "", "rea/npx not found — install: npm i -g rea-agents"
    full = cmd + args
    logger.info(f"$ {' '.join(full)}")
    try:
        r = subprocess.run(full, capture_output=True, text=True,
                           timeout=timeout, cwd=str(BASE_DIR))
        return r.returncode, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", f"timeout after {timeout}s"
    except Exception as e:
        return -1, "", str(e)


# ── REA operations ───────────────────────────────────────────────────
def doctor():
    """REA health check (read-only). Returns parsed dict."""
    rc, out, err = run_rea(["doctor", "--json"], timeout=60)
    if rc != 0:
        return {"ok": False, "error": (err or out)[:300]}
    try:
        # doctor --json may emit non-JSON preamble; find the JSON blob
        start = out.find("{")
        data = json.loads(out[start:]) if start >= 0 else {}
        return {"ok": True, "checks": data}
    except json.JSONDecodeError:
        return {"ok": True, "raw": out[:500]}


def analyze(target, timeout=REA_CMD_TIMEOUT):
    """Analyze a binary/app/website. Returns parsed result."""
    if not Path(target).exists():
        return {"ok": False, "error": f"target not found: {target}"}
    rc, out, err = run_rea(["analyze", target, "--json"], timeout=timeout)
    if rc != 0:
        return {"ok": False, "error": (err or out)[:300], "target": target}
    try:
        start = out.find("{")
        data = json.loads(out[start:]) if start >= 0 else {"raw": out[:1000]}
        return {"ok": True, "target": target, "result": data}
    except json.JSONDecodeError:
        return {"ok": True, "target": target, "raw": out[:1000]}


def inventory(target, timeout=120):
    """Quick artifact inventory (strings/symbols) without deep analysis."""
    if not Path(target).exists():
        return {"ok": False, "error": f"target not found: {target}"}
    rc, out, err = run_rea(["inspect-artifact", target, "--json"], timeout=timeout)
    if rc != 0:
        return {"ok": False, "error": (err or out)[:300]}
    try:
        start = out.find("{")
        data = json.loads(out[start:]) if start >= 0 else {}
        return {"ok": True, "target": target, "result": data}
    except json.JSONDecodeError:
        return {"ok": True, "target": target, "raw": out[:500]}


# ── memory + mesh integration ────────────────────────────────────────
def store_in_memory(text, source="rea", meta=None):
    try:
        sys.path.insert(0, str(BASE_DIR / "src"))
        import vector_memory_agent as vma
        vma.add(text, source=source, meta=meta or {})
        return True
    except Exception as e:
        logger.warning(f"memory store failed: {e}")
        return False


def announce_to_mesh(text, agent="rea"):
    try:
        import urllib.request
        data = json.dumps({"agent": agent, "text": text}).encode()
        req = urllib.request.Request(f"{MESH_API}/board", data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except Exception:
        return False


def investigate(target):
    """Full mesh-facing flow: analyze + store + announce."""
    result = analyze(target)
    if result.get("ok"):
        summary = f"REA analyzed {target}: {json.dumps(result.get('result', result.get('raw','')))[:400]}"
        store_in_memory(summary, source="rea_analysis", meta={"target": target})
        announce_to_mesh(f"REA: حللت {Path(target).name} — النتائج فالذاكرة")
    else:
        announce_to_mesh(f"REA: فشل تحليل {Path(target).name} — {result.get('error','?')[:80]}")
    save_state(last_target=target, last_result=result.get("ok"),
               ts=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    return result


# ── state ────────────────────────────────────────────────────────────
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
    """Telegram status."""
    d = doctor()
    cmd = _rea_available()
    lines = ["🔬 *REA — Reverse Engineer Anything*", ""]
    lines.append(f"CLI: {'🟢 `' + ' '.join(cmd) + '`' if cmd else '🔴 not installed'}")
    if d.get("ok"):
        lines.append("Doctor: 🟢 healthy")
        checks = d.get("checks", {})
        if isinstance(checks, dict):
            healthy = sum(1 for v in checks.values() if v in (True, "ok", "healthy"))
            lines.append(f"• checks: `{healthy}` healthy")
    else:
        lines.append(f"Doctor: 🔴 {d.get('error', '?')[:60]}")
    lines += [
        "",
        "Host: Windows x64 — native PE via Ghidra (experimental)",
        "JS/Electron + website observation: ✅ supported",
        "",
        "الأمر: `/rea <path>` للتحليل",
    ]
    return "\n".join(lines)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--doctor", action="store_true")
    ap.add_argument("--analyze", metavar="TARGET")
    ap.add_argument("--inventory", metavar="TARGET")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    if args.status:
        print(status_report())
        return
    if args.doctor:
        print(json.dumps(doctor(), ensure_ascii=False, indent=2))
        return
    if args.analyze:
        print(json.dumps(investigate(args.analyze), ensure_ascii=False, indent=2)[:1500])
        return
    if args.inventory:
        print(json.dumps(inventory(args.inventory), ensure_ascii=False, indent=2)[:1000])
        return
    print(status_report())


if __name__ == "__main__":
    main()
