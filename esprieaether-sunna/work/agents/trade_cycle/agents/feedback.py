"""Feedback Agent — Grok

نموذج خارجي مراجعة النتائج أسبوعيًا (مخصّص لمرتين في الأسبوع).
نستخدم OpenRouter أو Groq للاستدعاء؛ وإذا كان نموذج خارجي في متناول اليد، نستخدمه.
في المسودة، نُولّد تذكرة feedback (محتوى) دون استدعاء API (حسناً للصيانة، الوسيلة
المفضلة هي نموذج الذكاء الاصطناعي، والوصول كـ trade-key).

يأخذ تقرير دورة السابق ويُنشئ جدول feedback مع ملخص واقتراحات.
"""

import sqlite3
import json
import os
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # work (4 levels up)
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "logs" / "trade_cycle" / "feedback.log"
DB_PATH = DATA_DIR / "trade_cycle.db"

# نماذج خارجية (موفرة عبر OpenRouter / Groq)
FEEDBACK_MODEL = os.environ.get("FEEDBACK_MODEL", "meta/llama-3.1-8b-instant")
FEEDBACK_MAX_TOKENS = 200


def _log(msg: str):
    print(f"[feedback] {msg}")


def _connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def generate_summary(run_id: int) -> str:
    conn = _connect()
    trades = conn.execute(
        "SELECT symbol, side, size, pnl, status FROM trades WHERE run_id=?",
        (run_id,),
    ).fetchall()
    risks = conn.execute(
        "SELECT symbol, decision FROM risk_decisions WHERE run_id=?", (run_id,)
    ).fetchall()
    conn.close()
    lines = [f"Trade_cycle {run_id}: trades={len(trades)}"]
    for t in trades:
        lines.append(f"  {t['symbol']} {t['side']} size={t['size']} pnl={t['pnl']}")
    return "\n".join(lines)


def process(run_id: int) -> dict:
    """تذكرة feedback. نسير بالكامل حتى تُنفّذ في إطار trade_cycle.
    Using LLM for summary (optional)."""
    conn = _connect()
    # daily run (today) + open feedback days
    day = datetime.now().weekday() + 1  # Mon=1
    rows = conn.execute(
        "SELECT id, summary FROM cycle_runs WHERE status='done' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    run_row = conn.execute(
        "SELECT symbol, size, pnl FROM trades WHERE run_id=? ORDER BY id DESC",
        (run_id,),
    ).fetchall()
    conn.close()

    approved = sum(1 for r in run_row if r["pnl"] > 0)
    summary = f"cycle={run_id} trades={len(run_row)} approved={approved} pnl_total={sum(r['pnl'] for r in run_row):.2f}"

    # write feedback record
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO feedback (run_id, feedback_at, summary, changes_requested, applied, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (run_id, datetime.now(timezone.utc).isoformat(), summary,
         "مشروع trade_cycle (مستوى التأهيل)", 0, datetime.now(timezone.utc).isoformat()),
    )
    fid = cur.lastrowid
    conn.commit()
    conn.close()
    _log(f"📝 feedback {fid} — {summary}")
    return {"id": fid, "run_id": run_id, "summary": summary}


if __name__ == "__main__":
    _log("Feedback Agent (Grok) — weekly review placeholder")
