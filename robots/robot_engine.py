#!/usr/bin/env python3
"""
ESPRIEAETHER ROBOT ENGINE
محرك تنفيذ الروبوتات — scheduler + task queue + role handlers.

كل robot عندو role (وظيفة). المحرك كيربط الـ role بـ handler حقيقي،
وكيديرها ف loop مستمر (idle → active → done → idle).

الواجهة:
  engine = RobotEngine()
  engine.run_once()      # دورة واحدة (كل robots)
  engine.start()         # loop مستمر (thread)
  engine.get_stats()     # حالة كل robot
"""

import os
import sys
import time
import json
import sqlite3
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

# ─── Paths ───
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "src"))

DB = os.path.expanduser("~/ESPRIEAETHER/data/esprieaether.db")
LOG_FILE = BASE_DIR / "robot_engine.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("robot-engine")


# ═══════════════════════════════════════════════════════════════
#  DB Schema
# ═══════════════════════════════════════════════════════════════

def init_engine_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS robot_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            robot_id TEXT,
            action TEXT,
            payload TEXT,
            status TEXT DEFAULT 'pending',
            result TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            started_at DATETIME,
            completed_at DATETIME
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS robot_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            robot_id TEXT,
            role TEXT,
            status TEXT,
            summary TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS robots (
            id TEXT PRIMARY KEY,
            name TEXT,
            system TEXT,
            role TEXT,
            status TEXT DEFAULT 'idle',
            tasks_completed INTEGER DEFAULT 0,
            last_active DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════
#  Role Handlers
# ═══════════════════════════════════════════════════════════════

def _get_robot_info(robot_id: str) -> dict:
    conn = sqlite3.connect(DB)
    r = conn.execute("SELECT id, name, system, role, status FROM robots WHERE id=?", (robot_id,)).fetchone()
    conn.close()
    return {"id": r[0], "name": r[1], "system": r[2], "role": r[3], "status": r[4]} if r else {}


def h_health_check(robot_id: str) -> dict:
    """فحص صحة النظام"""
    try:
        import psutil
        return {
            "ok": True,
            "summary": f"cpu={psutil.cpu_percent()}% mem={psutil.virtual_memory().percent}% disk={psutil.disk_usage('/').percent}%",
        }
    except Exception as e:
        return {"ok": False, "summary": str(e)}


def h_log_scan(robot_id: str) -> dict:
    """فحص السجلات للأخطاء"""
    try:
        conn = sqlite3.connect(DB)
        rows = conn.execute("SELECT COUNT(*) FROM robot_results WHERE status='error'").fetchone()
        conn.close()
        return {"ok": True, "summary": f"robot_errors={rows[0]}"}
    except Exception as e:
        return {"ok": False, "summary": str(e)}


def h_ai_think(robot_id: str) -> dict:
    """فكر عبر المحرك المحلي (Ollama) — بلا limit (LLM7 429)"""
    try:
        import urllib.request
        host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        # Ollama مباشرة — بلا LLM7 (free tier محدود 10 req/min)
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": "أنت JARVIS، مساعد EsprieAether. أجب باختصار."},
                {"role": "user", "content": "قل OK فقط"},
            ],
            "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{host}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        text = data.get("message", {}).get("content", "").strip()
        return {"ok": True, "summary": f"engine=ollama reply={text[:40]}"}
    except Exception as e:
        # Ollama offline — fallback LLM7 (بما أن الباقي services كتحتاجو)
        try:
            from src.hermes_bridge import HermesBridge
            hb = HermesBridge()
            r = hb.ask("قل OK فقط")
            return {"ok": True, "summary": f"engine=llm7 reply={r[:40]}"}
        except Exception:
            return {"ok": False, "summary": f"no engine: {str(e)[:60]}"}


def h_git_status(robot_id: str) -> dict:
    """حالة git"""
    try:
        import subprocess
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(BASE_DIR), capture_output=True, text=True, timeout=10
        )
        changes = len([l for l in (r.stdout or "").splitlines() if l.strip()])
        return {"ok": True, "summary": f"pending_changes={changes}"}
    except Exception as e:
        return {"ok": False, "summary": str(e)}


def h_stats(robot_id: str) -> dict:
    """إحصائيات عامة"""
    try:
        conn = sqlite3.connect(DB)
        total = conn.execute("SELECT COUNT(*) FROM robots").fetchone()[0]
        done = conn.execute("SELECT COUNT(*) FROM robot_results WHERE status='ok'").fetchone()[0]
        conn.close()
        return {"ok": True, "summary": f"robots={total} completed={done}"}
    except Exception as e:
        return {"ok": False, "summary": str(e)}


def h_news_scan(robot_id: str) -> dict:
    """EXT_04 NEWS_SCANNER — فحص الأخبار (RSS)"""
    try:
        from scanners.news_scanner import NewsScanner
        ns = NewsScanner()
        ns.scan_all()  # كيمسح كل الـ RSS feeds
        return {"ok": True, "summary": "news scan done"}
    except Exception as e:
        return {"ok": False, "summary": str(e)[:100]}


def h_market_scan(robot_id: str) -> dict:
    """EXT_02 CRYPTO_TRADER / EXT_03 STOCK_ANALYZER — أسعار السوق"""
    try:
        from src.market_watcher import MarketWatcher
        mw = MarketWatcher()
        prices = mw.fetch_prices()  # dict
        return {"ok": True, "summary": f"coins={len(prices) if isinstance(prices, dict) else 0}"}
    except Exception as e:
        return {"ok": False, "summary": str(e)[:100]}


def h_embed(robot_id: str) -> dict:
    """AI_05 EMBEDDER — embedding عبر المحرك المحلي"""
    try:
        import urllib.request
        host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        payload = json.dumps({"model": model, "prompt": "test embedding"}).encode()
        req = urllib.request.Request(
            f"{host}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        emb = data.get("embedding", [])
        if emb:
            return {"ok": True, "summary": f"embed_dim={len(emb)}"}
        # Ollama شغال بلا embeddings — fallback (ماشي error)
        return {"ok": True, "summary": "embed unavailable (server no --embeddings)"}
    except urllib.error.HTTPError as e:
        # الموديل ما يدعمش embeddings — نعتبره "idle" ماشي error
        return {"ok": True, "summary": f"embed unsupported (model, http {e.code})"}
    except Exception as e:
        return {"ok": False, "summary": str(e)[:100]}


def h_noop(robot_id: str) -> dict:
    """robots بدون handler حقيقي"""
    return {"ok": True, "summary": "idle (no handler)"}


# role → handler mapping
ROLE_HANDLERS: dict = {
    # Immune / monitoring
    "defense": h_health_check,
    "cleanup": h_log_scan,
    "filter": h_log_scan,
    "monitoring": h_health_check,
    "perf": h_health_check,
    # Analysis / reports
    "logs": h_log_scan,
    "analysis": h_log_scan,
    "reports": h_stats,
    # AI
    "hermes_bridge": h_ai_think,
    "prompt_craft": h_ai_think,
    "decision_making": h_ai_think,
    "quick_response": h_ai_think,
    "model_eval": h_ai_think,
    "knowledge_base": h_ai_think,
    # Embeddings
    "embeddings": h_embed,
    # Backup / storage
    "backup": h_git_status,
    "buffer": h_git_status,
    # External (real handlers now)
    "news": h_news_scan,
    "trading": h_market_scan,
    "stocks": h_market_scan,
    # Meta
    "schedule": h_stats,
    "optimize": h_stats,
}


# ═══════════════════════════════════════════════════════════════
#  Robot Engine
# ═══════════════════════════════════════════════════════════════

class RobotEngine:
    def __init__(self, interval: float = 30.0):
        self.interval = interval
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.cycles = 0
        init_engine_db()

    # ─── DB helpers ───

    def _set_status(self, robot_id: str, status: str):
        conn = sqlite3.connect(DB)
        conn.execute(
            "UPDATE robots SET status=?, last_active=? WHERE id=?",
            (status, datetime.now().isoformat(), robot_id),
        )
        conn.commit()
        conn.close()

    def _record_result(self, robot_id: str, role: str, status: str, summary: str):
        conn = sqlite3.connect(DB)
        conn.execute(
            "INSERT INTO robot_results (robot_id, role, status, summary) VALUES (?,?,?,?)",
            (robot_id, role, status, summary[:500]),
        )
        if status == "ok":
            conn.execute(
                "UPDATE robots SET tasks_completed = tasks_completed + 1 WHERE id=?",
                (robot_id,),
            )
        conn.commit()
        conn.close()

    # ─── Execution ───

    def run_robot(self, robot_id: str, keep_active: bool = False) -> dict:
        """ينفّذ robot واحد حسب الـ role.
        keep_active=True: يحافظ status='active' من بعد (للـ loop)."""
        info = _get_robot_info(robot_id)
        if not info:
            return {"robot_id": robot_id, "status": "error", "summary": "unknown robot"}

        role = info["role"]
        handler = ROLE_HANDLERS.get(role, h_noop)

        self._set_status(robot_id, "active")
        try:
            result = handler(robot_id)
            status = "ok" if result.get("ok") else "error"
            summary = result.get("summary", "")
        except Exception as e:
            status = "error"
            summary = str(e)[:200]

        self._record_result(robot_id, role, status, summary)
        # loop: نرجعو active باش يدوز ف الدورة الجاية
        # manual: نرجعو idle
        self._set_status(robot_id, "active" if keep_active else "idle")
        return {"robot_id": robot_id, "name": info["name"], "role": role, "status": status, "summary": summary}

    def run_once(self, system: str = None) -> dict:
        """دورة واحدة — كل robots (أو نظام واحد)"""
        conn = sqlite3.connect(DB)
        if system:
            rows = conn.execute("SELECT id, role FROM robots WHERE system=?", (system,)).fetchall()
        else:
            rows = conn.execute("SELECT id, role FROM robots").fetchall()
        conn.close()

        results = []
        for robot_id, role in rows:
            results.append(self.run_robot(robot_id))

        self.cycles += 1
        ok = sum(1 for r in results if r["status"] == "ok")
        err = sum(1 for r in results if r["status"] == "error")
        logger.info(f"cycle #{self.cycles}: {len(results)} robots, {ok} ok, {err} error")
        return {"cycle": self.cycles, "total": len(results), "ok": ok, "error": err, "results": results}

    def run_active(self) -> dict:
        """غير robots المفعّلين (status='active') — يحافظ active للدورة الجاية"""
        conn = sqlite3.connect(DB)
        rows = conn.execute("SELECT id, role FROM robots WHERE status='active'").fetchall()
        conn.close()
        results = []
        for robot_id, role in rows:
            results.append(self.run_robot(robot_id, keep_active=True))
        if results:
            self.cycles += 1
            logger.info(f"cycle #{self.cycles}: {len(results)} active robots ran")
        return {"cycle": self.cycles, "ran": len(results), "results": results}

    # ─── Activation ───

    def activate(self, robot_id: str = None, system: str = None):
        conn = sqlite3.connect(DB)
        if robot_id:
            conn.execute("UPDATE robots SET status='active' WHERE id=?", (robot_id,))
        elif system:
            conn.execute("UPDATE robots SET status='active' WHERE system=?", (system,))
        conn.commit()
        conn.close()

    def deactivate(self, robot_id: str = None, system: str = None):
        conn = sqlite3.connect(DB)
        if robot_id:
            conn.execute("UPDATE robots SET status='idle' WHERE id=?", (robot_id,))
        elif system:
            conn.execute("UPDATE robots SET status='idle' WHERE system=?", (system,))
        conn.commit()
        conn.close()

    def deactivate_all(self):
        conn = sqlite3.connect(DB)
        conn.execute("UPDATE robots SET status='idle'")
        conn.commit()
        conn.close()

    # ─── Loop ───

    def _loop(self):
        logger.info(f"robot engine loop started (interval={self.interval}s)")
        while not self._stop.is_set():
            try:
                self.run_active()
            except Exception as e:
                logger.error(f"loop error: {e}")
            self._stop.wait(self.interval)
        logger.info("robot engine loop stopped")

    def start(self):
        if self._thread and self._thread.is_alive():
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    # ─── Stats ───

    def get_stats(self) -> dict:
        conn = sqlite3.connect(DB)
        by_status = dict(conn.execute("SELECT status, COUNT(*) FROM robots GROUP BY status").fetchall())
        results = dict(conn.execute("SELECT status, COUNT(*) FROM robot_results GROUP BY status").fetchall())
        recent = conn.execute(
            "SELECT robot_id, role, status, summary, created_at FROM robot_results ORDER BY id DESC LIMIT 10"
        ).fetchall()
        conn.close()
        return {
            "cycles": self.cycles,
            "robots_by_status": by_status,
            "results_by_status": results,
            "recent": [
                {"robot_id": r[0], "role": r[1], "status": r[2], "summary": r[3], "at": r[4]}
                for r in recent
            ],
        }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true", help="run one cycle")
    p.add_argument("--system", default=None, help="filter by system")
    p.add_argument("--activate", default=None, help="activate system")
    p.add_argument("--deactivate-all", action="store_true")
    p.add_argument("--stats", action="store_true")
    p.add_argument("--loop", action="store_true")
    args = p.parse_args()

    eng = RobotEngine()

    if args.activate:
        eng.activate(system=args.activate)
        print(f"activated system: {args.activate}")
    elif args.deactivate_all:
        eng.deactivate_all()
        print("all robots deactivated")
    elif args.stats:
        print(json.dumps(eng.get_stats(), ensure_ascii=False, indent=2))
    elif args.once:
        print(json.dumps(eng.run_once(system=args.system), ensure_ascii=False, indent=2))
    elif args.loop:
        try:
            eng.start()
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            eng.stop()
    else:
        p.print_help()
