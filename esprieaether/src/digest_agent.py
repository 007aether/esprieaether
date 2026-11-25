#!/usr/bin/env python3
"""
digest_agent.py — observability digest: what the system DID, in one glance

WHAT: Collects the autonomous_loop's task results, the mesh board's latest
insights, the cloud status, and the service health sweep, and produces ONE
digest (markdown + Telegram format) of everything that happened in the last
N hours. This is the "what did my agents do while I slept" report.

WHY: with 30+ loop tasks, 7 mesh agents, and a cloud node, no one reads the
raw logs. This distills them into a single readable report — modeled on the
observability pattern (Langfuse-style traces) but zero-dependency.

Outputs:
  data/digest.md            — full markdown digest
  data/digest_last.json     — machine-readable last digest (for /digest)
"""

import json
import logging
import os
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DIGEST_FILE = BASE_DIR / "data" / "digest.md"
LAST_FILE = BASE_DIR / "data" / "digest_last.json"

logger = logging.getLogger("digest_agent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

SERVICES = {
    "router": ("11435", "/v1/models"),
    "mesh": ("11437", "/health"),
    "web": ("5000", "/health"),
    "cloud-desktop": ("5001", "/health"),
    "sunna": ("5100", "/health"),
    "integrations": ("5102", "/health"),
    "kanban": ("5103", "/health"),
    "homedock": ("5104", "/health"),
    "jarvis": ("8000", "/api/health"),
}


def http_json(port, path, timeout=5):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def service_health():
    """Sweep all services. Returns (up_count, total, rows)."""
    rows = []
    up = 0
    for name, (port, path) in SERVICES.items():
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=4) as r:
                code = r.status
        except Exception:
            code = 0
        alive = code > 0
        up += alive
        rows.append((name, port, code, alive))
    return up, len(SERVICES), rows


def board_insights(limit=10):
    """Latest mesh board messages."""
    data = http_json("11437", f"/board?limit={limit}")
    return data.get("messages", []) if data else []


def cloud_state():
    """Cloud node + PC last-seen."""
    f = BASE_DIR / "data" / "cloud_status.json"
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return {}


def memory_stats():
    """Vector memory stats."""
    db = BASE_DIR / "data" / "vector_memory.db"
    if not db.exists():
        return {"total": 0}
    try:
        import sqlite3
        conn = sqlite3.connect(str(db))
        total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        conn.close()
        return {"total": total}
    except Exception:
        return {"total": 0}


def proposed_tasks():
    """Mesh-proposed tasks awaiting action."""
    f = BASE_DIR / "data" / "agent_proposed_tasks.json"
    if not f.exists():
        return []
    try:
        return json.loads(f.read_text(encoding="utf-8"))[-5:]
    except Exception:
        return []


def build_digest():
    """Assemble the full digest."""
    now = datetime.now(timezone.utc)
    up, total, rows = service_health()
    board = board_insights(10)
    cloud = cloud_state()
    mem = memory_stats()
    tasks = proposed_tasks()

    lines = [
        f"# 📊 Aether Digest — {now.strftime('%Y-%m-%d %H:%M')} UTC",
        "",
        f"## 🖥️ Services: {up}/{total} up",
        "",
        "| service | port | status |",
        "|---|---|---|",
    ]
    for name, port, code, alive in rows:
        icon = "✅" if alive else "❌"
        lines.append(f"| {name} | :{port} | {icon} {code or '—'} |")

    lines += [
        "",
        f"## 🕸️ Mesh board ({len(board)} recent)",
        "",
    ]
    for m in board[-8:]:
        ts = m.get("ts", "")[11:16]
        lines.append(f"- `[{ts}] {m.get('agent','?')}`: {m.get('text','')[:100]}")

    lines += [
        "",
        f"## ☁️ Cloud",
        "",
        f"- PC last seen: `{cloud.get('pc_last_seen', '?')[:19]}`",
        f"- Cloud last run: `{cloud.get('cloud_last_run', '?')[:19]}`",
        "",
        f"## 🧠 Memory: {mem.get('total', 0)} memories",
        "",
    ]

    if tasks:
        lines += ["## 📋 Proposed tasks (from agents)", ""]
        for t in tasks:
            lines.append(f"- `{t.get('agent','?')}`: {t.get('title','')[:90]}")
        lines.append("")

    content = "\n".join(lines)
    DIGEST_FILE.parent.mkdir(exist_ok=True)
    DIGEST_FILE.write_text(content, encoding="utf-8")

    result = {
        "ts": now.isoformat(),
        "services_up": up,
        "services_total": total,
        "board_recent": len(board),
        "memory_total": mem.get("total", 0),
        "proposed_tasks": len(tasks),
        "digest_file": str(DIGEST_FILE),
    }
    LAST_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def format_telegram():
    """Compact Telegram digest."""
    up, total, rows = service_health()
    board = board_insights(5)
    cloud = cloud_state()
    mem = memory_stats()

    lines = [
        f"📊 *Digest* — {datetime.now(timezone.utc).strftime('%H:%M')} UTC",
        "",
        f"🖥️ Services: *{up}/{total}*",
    ]
    down = [n for n, _, _, alive in rows if not alive]
    if down:
        lines.append(f"❌ down: {', '.join(down)}")

    if board:
        lines += ["", "🕸️ آخر ما قال الوكلاء:"]
        for m in board[-3:]:
            lines.append(f"• `{m.get('agent','?')}`: {m.get('text','')[:60]}")

    pc = cloud.get("pc_last_seen", "?")[:16]
    lines += [
        "",
        f"☁️ PC: `{pc}` · 🧠 ذاكرة: `{mem.get('total', 0)}`",
    ]
    return "\n".join(lines)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--telegram", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.telegram:
        print(format_telegram())
    else:
        result = build_digest()
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"✅ digest → {result['digest_file']}")
            print(f"   services: {result['services_up']}/{result['services_total']}")
            print(f"   memory: {result['memory_total']} · proposed tasks: {result['proposed_tasks']}")


if __name__ == "__main__":
    main()
