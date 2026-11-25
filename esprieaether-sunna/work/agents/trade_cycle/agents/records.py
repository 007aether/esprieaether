"""Records Agent — Jill

تسجل كل صفقة وحالة في SQLite وتحسب P&L اليومي وملف العموم.
تستخدم نفس trade_cycle.db مع trade_cycle لتحديث معاً.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # work (4 levels up)
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "logs" / "trade_cycle" / "records.log"
DB_PATH = DATA_DIR / "trade_cycle.db"


def _log(msg: str):
    print(f"[records] {msg}")


def _connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def log_trade(trade: dict, run_id: int) -> int:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO ledger (run_id, symbol, side, size, entry_price, exit_price, pnl, fees, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (run_id, trade["symbol"], trade["side"], trade["size"],
         trade["entry_price"], trade.get("final_price"), trade.get("pl", 0.0),
         0.0, trade["status"], trade["created_at"]),
    )
    lid = cur.lastrowid
    conn.commit()
    conn.close()
    return lid


def summarize_day(run_id: int) -> dict:
    conn = _connect()
    row = conn.execute(
        """SELECT
              COUNT(*) AS trades,
              SUM(pnl) AS pnl,
              SUM(fees) AS fees,
              SUM(CASE WHEN status='closed' THEN 1 ELSE 0 END) AS closed
           FROM ledger WHERE run_id=?""",
        (run_id,),
    ).fetchone()
    conn.close()
    data = dict(row) if row else {}
    return {
        "run_id": run_id,
        "trades": data.get("trades") or 0,
        "pnl": data.get("pnl") or 0,
        "fees": data.get("fees") or 0,
        "closed": data.get("closed") or 0,
    }


if __name__ == "__main__":
    _log("Records Agent (Jill) — equities staging")
