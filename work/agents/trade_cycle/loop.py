"""Trade Cycle — orchestration (loop driver)

يدير دورة العمل للوكلاء الستة في trade_cycle:
  1. research --> 2. risk     --> 3. trading
  4. records  --> 5. ceo      --> 6. feedback

كلogenes يقرأ ويكتب نفس قاعدة SQLite trade_cycle.db.
يُنفّذ دورة واحدة عبر `loop.py --once`.
"""

import argparse
import json
import sys
import os
import sqlite3
from datetime import datetime, timezone
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TC_DIR = BASE_DIR / "work" / "agents" / "trade_cycle"
sys.path.insert(0, str(TC_DIR))

from config import PAPER_ONLY, TRADING_DAYS, DAILY_REPORT_TO_TELEGRAM, TRADE_ONLY_MARK  # noqa: E402
from database import get_conn, init_db  # noqa: E402

AGENTS = {
    "research": "agents.research",
    "risk": "agents.risk",
    "trading": "agents.trading",
    "records": "agents.records",
    "ceo": "agents.ceo",
    "feedback": "agents.feedback",
}
LOGS = BASE_DIR / "data" / "logs" / "trade_cycle"
LOGS.mkdir(parents=True, exist_ok=True)


def _log(step: str, msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {step.upper()} | {msg}")


def _next_run_id() -> int:
    conn = get_conn()
    # نبحث عن آخر دورة حالية (بغض النظر عن الحالة) لتحديد التسلسل المستمر
    row = conn.execute("SELECT COALESCE(MAX(id), 0) AS m FROM cycle_runs").fetchone()
    conn.close()
    val = row["m"] if row and row["m"] is not None else 0
    return int(val)


def _new_run(phase: str, status: str, summary: str = "") -> int:
    next_id = _next_run_id()
    if next_id > 0:
        conn = get_conn()
        row = conn.execute("SELECT id FROM cycle_runs WHERE id=?", (next_id,)).fetchone()
        conn.close()
        return int(row["id"]) if row else int(next_id)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO cycle_runs (started_at, phase, status, summary) VALUES (?,?,?,?)",
        (datetime.now(timezone.utc).isoformat(), phase, status, summary),
    )
    rid = cur.lastrowid
    conn.commit()
    conn.close()
    return int(rid)


def _mark_run(rid: int, phase: str, status: str, summary: str = ""):
    conn = get_conn()
    conn.execute(
        "UPDATE cycle_runs SET phase=?, status=?, summary=? WHERE id=?",
        (phase, status, summary, rid),
    )
    conn.commit()
    conn.close()


def _send_telegram(text: str):
    """رسل تقرير نهاية الدورة إلى Telegram (عند تفعيله في .env)."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat:
        _log("telegram", "لا يوجد رابط للتقارير (token/chat غير مملوء)")
        return
    try:
        import requests
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat, "text": text, "parse_mode": "Markdown"}
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code == 200:
            _log("telegram", "تم إرسال التقرير")
        else:
            _log("telegram", f"فشل الإرسال: {r.text[:80]}")
    except Exception as e:
        _log("telegram", f"خطأ: {e}")


def run_once():
    """تشغيل دورة كاملة وواحدة."""
    import database as db_mod
    print("[DEBUG LOOP] DB_PATH:", db_mod.DB_PATH, "exists:", db_mod.DB_PATH.exists())
    init_db()  # تأكد من إنشاء الجداول
    import database as db_mod
    print("[DEBUG] DB:", db_mod.DB_PATH, "exists:", db_mod.DB_PATH.exists())
    conn = db_mod.get_conn()
    tabs = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print("[DEBUG] Tables:", tabs)
    conn.close()
    run_id = _next_run_id()
    print("[DEBUG] next_run_id:", run_id, "type:", type(run_id))
    if run_id == 0:
        run_id = _new_run("start", "init", "نظرة عامة على دورة trade_cycle (ورقية)")
        print("[DEBUG] new_run_id:", run_id, "type:", type(run_id))
    assert isinstance(run_id, int), f"run_id must be int, got {type(run_id)}"

    # 1) Research (Jim)
    _log("run", "1/5 البحث  [Jim]")
    research = None
    try:
        import agents.research as research_mod
        research = research_mod.run()
        research_mod.persist(research["rows"], run_id)
        _log("run", f"الخيارات: {len(research['rows'])}")
    except Exception as e:
        _log("run", f"البحث: {e}")

    # 2) Risk (Bob)
    _log("run", "2/5 المخاطر  [Bob]")
    decisions = []
    try:
        import agents.risk as risk_mod
        for row in research.get("rows", []):
            dec = risk_mod.evaluate(row)
            decision_id = risk_mod.persist(dec, run_id)
            decisions.append({"research": row, "decision": dec})
    except Exception as e:
        _log("run", f"المخاطر: {e}")

    # 3) Trading (Doug) — ورقي فقط (PAPER_ONLY)
    _log("run", "3/5 التداول  [Doug]")
    accepted = [d for d in decisions if d["decision"]["decision"] == "approve"]
    trades = []
    try:
        import agents.trading as trading_mod
        for d in accepted:
            tr = trading_mod.place(d["decision"], paper_only=PAPER_ONLY)
            trading_mod.persist(tr, run_id)
            trades.append(tr)
    except Exception as e:
        _log("run", f"التداول: {e}")

    # 4) Records (Jill)
    _log("run", "4/5 السجلات  [Jill]")
    try:
        import agents.records as records_mod
        total = records_mod.summarize_day(run_id)
        _log("run", f"الإجماليات: P&L={total.get('pnl', 0):.2f}")
    except Exception as e:
        _log("run", f"السجلات: {e}")

    # 5) CEO (Bill) يقرأ ويكتب القواعد
    _log("run", "5/5 المدير  [Bill]")
    try:
        import agents.ceo as ceo_mod
        ceo_mod.review(run_id)
    except Exception as e:
        _log("run", f"المدير: {e}")

    # 6) Feedback (Grok / OpenRouter إذا كان اليوم مقتُر)
    _log("run", "6/6 التغذية  [Grok]")
    try:
        import agents.feedback as feedback_mod
        feedback_mod.process(run_id)
    except Exception as e:
        _log("run", f"الغذاء: {e}")

    _mark_run(run_id, "done", "ok", "الدورة انتهت")
    _send_telegram(generate_summary(run_id))
    return run_id


def generate_summary(run_id: int) -> str:
    conn = get_conn()
    trade = conn.execute(
        "SELECT COUNT(*) AS n, SUM(pnl) AS p FROM trades WHERE status='closed' AND pnl IS NOT NULL",
        {"run_id": run_id},
    ).fetchone()
    conn.close()
    lines = [f"📊 تقرير دورة trade_cycle — {run_id}",
             f"✅ الصفقات المعتمدة: {trade['n'] or 0}",
             f"💰 صافي الأرباح: {trade['p'] or 0:.2f} (ورقي)"]
    return "\n".join(lines)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true", help="تشغيل دورة واحدة")
    p.add_argument("--daemon", action="store_true", help="تشغيل دوري")
    args = p.parse_args()
    if args.once:
        run_once()
    elif args.daemon:
        while True:
            run_once()
            time.sleep(3600)
