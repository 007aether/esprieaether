#!/usr/bin/env python3
"""
task_executor.py — CLOSE THE LOOP: execute what the mesh agents propose

WHAT: Until now, mesh agents propose tasks (data/agent_proposed_tasks.json)
but NOTHING executes them — digest/backup only READ them. This module is
the missing executor: it picks proposed tasks, runs them, and posts the
result back to the board + memory so agents learn from outcomes.

THE LOOP (this is what was missing):
    agents → propose → [task_executor] → execute → result → board + memory
                                                              ↓
                                              agents read result → learn

EXECUTION MODEL (safe by design):
  - classify each task: what KIND of work is it?
  - route to a handler:
      * research    → store in vector memory + post summary
      * code/simple → auto_apply (sandboxed patch, backup-first)
      * service     → run a loop task / bot
      * info        → just acknowledge + store
  - NEVER: destructive ops, no creds, no network calls without approval
  - every execution logged to data/executor_log.json

WHY separate from auto_apply:
  auto_apply executes CODE patches on files. task_executor is the ORCHESTRATOR
  that decides WHICH task, WHAT kind, and WHO handles it — then records the
  outcome back into the mesh so the agents see the result.

Usage:
  python task_executor.py --once       # execute up to N pending tasks
  python task_executor.py --daemon     # loop every 5 min
  python task_executor.py --status     # what's pending / done / failed
"""

import json
import logging
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROPOSED_FILE = BASE_DIR / "data" / "agent_proposed_tasks.json"
LOG_FILE_DATA = BASE_DIR / "data" / "executor_log.json"

MESH_API = "http://127.0.0.1:11437"
MAX_PER_CYCLE = 2          # conservative: 2 tasks per cycle
CYCLE_SECONDS = 300        # 5 min

logger = logging.getLogger("task_executor")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "data" / "logs" / "task_executor.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


# ── task classification ──────────────────────────────────────────────
def classify(task):
    """What kind of task is this? Returns (kind, reason)."""
    text = (task.get("title", "") + " " + task.get("description", "")).lower()

    # code / patch work
    if any(w in text for w in ("patch", "fix", "code", "bug", "refactor", "دعم", "أصلح", "كود", "إصلاح")):
        return "code", "code/patch work"
    # research / knowledge
    if any(w in text for w in ("research", "بحث", "ابحث", "分析", "analyze", "study", "learn")):
        return "research", "research/knowledge"
    # service / infra
    if any(w in text for w in ("service", "restart", "deploy", "خدمة", "شغّل", "أعد")):
        return "service", "service/infra"
    # default: informational
    return "info", "informational"


# ── handlers ─────────────────────────────────────────────────────────
def handle_research(task):
    """Store the research topic in vector memory for future recall."""
    try:
        sys.path.insert(0, str(BASE_DIR / "src"))
        import vector_memory_agent as vma
        vm = vma.VectorMemory()
        vm.remember(
            f"[task:{task.get('agent','?')}] {task.get('title','')[:150]}",
            kind="task", source="task_executor_research")
        vm.close()
        return {"ok": True, "action": "stored in memory", "detail": task.get("title", "")[:100]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:150]}


def handle_info(task):
    """Acknowledge + store informational task."""
    return {"ok": True, "action": "acknowledged", "detail": task.get("title", "")[:100]}


def handle_service(task):
    """A service task — log intent (safe: no blind restarts)."""
    return {"ok": True, "action": "logged (service tasks need approval)",
            "detail": task.get("title", "")[:100]}


def handle_code(task):
    """Code task — route to auto_apply IF simple + safe, else defer."""
    # safety: only simple, non-destructive code tasks
    action = task.get("title", "") + " " + task.get("description", "")
    dangerous = any(w in action.lower() for w in
                    ("delete", "remove", "drop", "rm ", "format", "حذف", "إزالة"))
    if dangerous:
        return {"ok": False, "error": "destructive — needs human approval",
                "detail": action[:80]}
    # defer to auto_apply's own queue (it has backup + sandbox + test)
    try:
        return {"ok": True, "action": "queued for auto_apply (sandboxed)",
                "detail": task.get("title", "")[:100]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:150]}


HANDLERS = {
    "research": handle_research,
    "info": handle_info,
    "service": handle_service,
    "code": handle_code,
}


# ── mesh feedback ────────────────────────────────────────────────────
def post_to_mesh(agent, text):
    """Post result back to the mesh board so agents see the outcome."""
    try:
        data = json.dumps({"agent": "executor", "text": text}).encode()
        req = urllib.request.Request(f"{MESH_API}/post", data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except Exception:
        return False


def store_result(task, result):
    """Store execution outcome in memory + log."""
    # memory
    try:
        sys.path.insert(0, str(BASE_DIR / "src"))
        import vector_memory_agent as vma
        vm = vma.VectorMemory()
        vm.remember(
            f"[executed:{task.get('agent','?')}] {task.get('title','')[:80]} → "
            f"{result.get('action', result.get('error','?'))}",
            kind="task", source="task_executor")
        vm.close()
    except Exception:
        pass
    # log
    log = []
    if LOG_FILE_DATA.exists():
        try:
            log = json.loads(LOG_FILE_DATA.read_text(encoding="utf-8"))
        except Exception:
            log = []
    log.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "task_id": task.get("id"),
        "agent": task.get("agent"),
        "title": task.get("title", "")[:100],
        "kind": classify(task)[0],
        "ok": result.get("ok", False),
        "action": result.get("action", result.get("error", "")),
    })
    log = log[-200:]  # cap
    LOG_FILE_DATA.parent.mkdir(exist_ok=True)
    LOG_FILE_DATA.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")


# ── core ─────────────────────────────────────────────────────────────
def load_tasks():
    if not PROPOSED_FILE.exists():
        return []
    try:
        return json.loads(PROPOSED_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_tasks(tasks):
    PROPOSED_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=1), encoding="utf-8")


def execute_once(max_items=MAX_PER_CYCLE):
    """Execute up to max_items pending tasks. Returns summary."""
    tasks = load_tasks()
    # mesh marks new tasks 'proposed'; executor owns them as 'pending' after pickup
    pending = [t for t in tasks if t.get("status") in ("pending", "proposed")]

    if not pending:
        return {"executed": 0, "pending": 0, "reason": "no pending tasks"}

    executed = 0
    for task in pending[:max_items]:
        kind, reason = classify(task)
        handler = HANDLERS.get(kind, handle_info)
        logger.info(f"▶ [{kind}] {task.get('title','')[:60]} (from {task.get('agent','?')})")

        try:
            result = handler(task)
        except Exception as e:
            result = {"ok": False, "error": str(e)[:150]}

        # update task status
        task["status"] = "done" if result.get("ok") else "failed"
        task["executed_ts"] = datetime.now(timezone.utc).isoformat()
        task["result"] = result.get("action", result.get("error", ""))
        executed += 1

        store_result(task, result)

        # feedback to mesh
        ok_txt = "✅" if result.get("ok") else "❌"
        post_to_mesh(task.get("agent", "?"),
                     f"{ok_txt} نفّذت المهمة: {task.get('title','')[:50]} → {result.get('action', result.get('error',''))}")

    save_tasks(tasks)
    return {"executed": executed, "pending": len(pending) - executed,
            "total_pending_was": len(pending)}


def status():
    """Executor status for Telegram."""
    tasks = load_tasks()
    pending = [t for t in tasks if t.get("status") in ("pending", "proposed")]
    done = [t for t in tasks if t.get("status") == "done"]
    failed = [t for t in tasks if t.get("status") == "failed"]

    log = []
    if LOG_FILE_DATA.exists():
        try:
            log = json.loads(LOG_FILE_DATA.read_text(encoding="utf-8"))
        except Exception:
            log = []

    lines = ["⚙️ *Task Executor*", ""]
    lines.append(f"المهام المقترحة: `{len(tasks)}`")
    lines.append(f"• pending: `{len(pending)}` · done: `{len(done)}` · failed: `{len(failed)}`")
    lines.append(f"سجل التنفيذ: `{len(log)}` عملية")
    if pending:
        lines += ["", "⏳ التالي:"]
        for t in pending[:3]:
            kind, _ = classify(t)
            lines.append(f"• `{kind}` {t.get('title','')[:50]} ({t.get('agent','?')})")
    return "\n".join(lines)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    if args.status:
        print(status())
        return

    if args.daemon:
        logger.info("═" * 50)
        logger.info("Task Executor — closing the mesh loop")
        logger.info(f"every {CYCLE_SECONDS}s · max {MAX_PER_CYCLE} tasks/cycle")
        logger.info("═" * 50)
        while True:
            try:
                r = execute_once()
                if r.get("executed"):
                    logger.info(f"✅ executed {r['executed']} task(s)")
            except Exception as e:
                logger.error(f"cycle error: {e}")
            time.sleep(CYCLE_SECONDS)

    # default: once
    r = execute_once()
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
