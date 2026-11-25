#!/usr/bin/env python3
"""
self_improve.py — LEARN FROM ERRORS: turn failures into fixes

WHAT: The system produces errors (logs, executor failures, service crashes,
router timeouts). Today those errors are written and forgotten. self_improve
CLOSES the learning loop: it harvests errors from logs, stores them in vector
memory, asks the router to diagnose root cause + propose a fix, and files the
fix as a task the mesh agents / task_executor can act on.

THE LOOP (self-improvement):
    logs/errors → [self_improve] → diagnose (router) → root cause + fix
        → vector memory (remember) → task_executor (propose fix) → mesh learns

WHY this matters: every daemon that crashes at 3am teaches the system once.
Without this loop, the same bug comes back. With it, memory + diagnosis
accumulate and the next failure is faster to fix — and agents recall past
fixes before proposing new ones (mesh memory already wired).

Usage:
    python self_improve.py --once          # scan recent errors, diagnose 1-3
    python self_improve.py --daemon        # loop every 30 min
    python self_improve.py --status        # errors found / diagnosed / lessons
"""

import json
import logging
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "data" / "logs"
LESSONS_FILE = BASE_DIR / "data" / "lessons.json"
PROPOSED_FILE = BASE_DIR / "data" / "agent_proposed_tasks.json"
ROUTER_URL = os.getenv("AETHER_ROUTER_URL", "http://127.0.0.1:11435")

MAX_PER_CYCLE = 3
CYCLE_SECONDS = 30 * 60
# how far back to scan logs
SCAN_MINUTES = 60

logger = logging.getLogger("self_improve")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "data" / "logs" / "self_improve.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

ERROR_PAT = re.compile(r"(ERROR|CRITICAL|Traceback|Exception|failed|FAIL|error:|Error)", re.IGNORECASE)


def scan_recent_errors():
    """Read recent error lines from service logs. Returns list of (source, line)."""
    errors = []
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=SCAN_MINUTES)
    if not LOGS_DIR.exists():
        return errors

    for log_file in LOGS_DIR.glob("*.err"):
        try:
            # only recent files
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime, timezone.utc)
            if mtime < cutoff:
                continue
            for line in log_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                if ERROR_PAT.search(line) and len(line.strip()) > 10:
                    errors.append((log_file.name, line.strip()[:300]))
        except Exception:
            continue
    return errors[-20:]  # cap


def dedupe(errors, seen):
    """Skip errors we've already diagnosed."""
    fresh = []
    for src, line in errors:
        # crude dedupe key: normalized error text
        key = re.sub(r"\d+", "#", line)[:120]
        if key not in seen:
            fresh.append((src, line))
            seen.add(key)
    return fresh


def ask_router(prompt):
    messages = [
        {"role": "system", "content":
         "You are JARVIS diagnosing an autonomous-system error. Reply with a short Arabic "
         "diagnosis: (1) السبب الجذري (2) الإصلاح المقترح (3) هل هو خطر؟ Be concise, 3 lines max."},
        {"role": "user", "content": prompt},
    ]
    try:
        data = json.dumps({"model": "aether-auto", "messages": messages, "max_tokens": 400}).encode()
        req = urllib.request.Request(f"{ROUTER_URL}/v1/chat/completions", data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=60) as r:
            result = json.loads(r.read().decode())
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"router error: {e}")
        return None


def remember(source, text):
    """Store in vector memory."""
    try:
        sys.path.insert(0, str(BASE_DIR / "src"))
        import vector_memory_agent as vma
        vm = vma.VectorMemory()
        vm.remember(f"[error:{source}] {text[:250]}", kind="error", source="self_improve")
        vm.close()
    except Exception:
        pass


def propose_fix(source, diagnosis):
    """File a fix task so task_executor / mesh can act on it."""
    try:
        tasks = []
        if PROPOSED_FILE.exists():
            tasks = json.loads(PROPOSED_FILE.read_text(encoding="utf-8"))
        tasks.append({
            "id": f"fix-{int(time.time()*1000)}",
            "agent": "self_improve",
            "title": f"إصلاح خطأ في {source}",
            "description": diagnosis[:300],
            "status": "proposed",
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        tasks = tasks[-50:]
        PROPOSED_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception as e:
        logger.error(f"propose failed: {e}")


def load_lessons():
    if LESSONS_FILE.exists():
        try:
            return json.loads(LESSONS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"seen": [], "diagnosed": 0, "fixes_proposed": 0}
    return {"seen": [], "diagnosed": 0, "fixes_proposed": 0}


def save_lessons(l):
    LESSONS_FILE.parent.mkdir(exist_ok=True)
    LESSONS_FILE.write_text(json.dumps(l, ensure_ascii=False, indent=1), encoding="utf-8")


def improve_once(max_items=MAX_PER_CYCLE):
    """Scan errors, diagnose, remember, propose fixes. Returns summary."""
    lessons = load_lessons()
    seen = set(lessons.get("seen", []))

    errors = scan_recent_errors()
    fresh = dedupe(errors, seen)

    if not fresh:
        return {"scanned": len(errors), "new": 0, "reason": "no new errors"}

    diagnosed = 0
    for src, line in fresh[:max_items]:
        logger.info(f"🔍 diagnosing [{src}]: {line[:70]}")
        diagnosis = ask_router(f"خطأ من {src}:\n{line}")
        if not diagnosis:
            continue
        remember(src, f"{line}\n→ {diagnosis}")
        propose_fix(src, diagnosis)
        diagnosed += 1
        key = re.sub(r"\d+", "#", line)[:120]
        seen.add(key)

    lessons["seen"] = list(seen)[-200:]
    lessons["diagnosed"] = lessons.get("diagnosed", 0) + diagnosed
    lessons["fixes_proposed"] = lessons.get("fixes_proposed", 0) + diagnosed
    lessons["last_run"] = datetime.now(timezone.utc).isoformat()
    save_lessons(lessons)

    return {"scanned": len(errors), "new": len(fresh), "diagnosed": diagnosed}


def status():
    lessons = load_lessons()
    lines = ["🧪 *Self-Improve*", ""]
    lines.append(f"أخطاء شُخّصت: `{lessons.get('diagnosed', 0)}`")
    lines.append(f"إصلاحات مقترحة: `{lessons.get('fixes_proposed', 0)}`")
    lines.append(f"بصمات معروفة: `{len(lessons.get('seen', []))}`")
    if lessons.get("last_run"):
        lines.append(f"آخر تشغيل: `{lessons['last_run'][:19]}`")
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
        logger.info("Self-Improve — learning from errors")
        logger.info(f"every {CYCLE_SECONDS}s · scan {SCAN_MINUTES}min of logs")
        logger.info("═" * 50)
        while True:
            try:
                r = improve_once()
                if r.get("diagnosed"):
                    logger.info(f"🧪 diagnosed {r['diagnosed']} error(s)")
            except Exception as e:
                logger.error(f"cycle error: {e}")
            time.sleep(CYCLE_SECONDS)
    r = improve_once()
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
