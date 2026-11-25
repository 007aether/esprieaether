"""CEO Agent — Bill

يقرأ تقرير الدورة، ويفحص قواعد المخاطر، ويوفر تعديلات قابلة للتنفيذ.
قرارات CEO مبنية على Python (قواعد معرفية)، لا تعتمد على نموذج ذكاء اصطناعي،
الهدف هو تبسيطها وتسميتها في config.py.

القواعد (يقرأ CEO منها) تُعدّل يدويًا في config.py أو بواسطة script upright governance.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # work (4 levels up)
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "logs" / "trade_cycle" / "ceo.log"
DB_PATH = DATA_DIR / "trade_cycle.db"


def _log(msg: str):
    print(f"[ceo] {msg}")


def _connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def review(run_id: int) -> dict:
    conn = _connect()
    trades = conn.execute(
        "SELECT symbol, side, size, pnl, status FROM trades WHERE run_id=?", (run_id,)
    ).fetchall()
    risk_rows = conn.execute(
        "SELECT symbol, decision, reason FROM risk_decisions WHERE run_id=?", (run_id,)
    ).fetchall()
    conn.close()

    summary = {
        "run_id": run_id,
        "trades": [dict(t) for t in trades],
        "risk_decisions": [dict(r) for r in risk_rows],
        "total_trades": len(trades),
        "approved": sum(1 for r in risk_rows if r["decision"] == "approve"),
        "rejected": sum(1 for r in risk_rows if r["decision"] == "reject"),
    }

    _log(f"✅ دورة trade_cycle {run_id}: trades={summary['total_trades']} "
         f"approved={summary['approved']} rejected={summary['rejected']}")

    # Example policy note: if any rejected trades, store a log
    for r in risk_rows:
        if r["decision"] == "reject":
            _log(f"⬅️ رفض trade {r['symbol']}: {r['reason']}")

    return summary


if __name__ == "__main__":
    _log("CEO Agent (Bill) — governance & rules review")
