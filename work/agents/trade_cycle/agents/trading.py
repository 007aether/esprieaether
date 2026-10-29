"""Trading Agent — Doug

ينفذ الصفقات المعتمَدة فقط، عبر واجهة البورصة (Trade API).
في هذه المسودة, trading مفعّل كـ paper trading (ورقي) ووهمي حتى لا توجد مخاطر
مالية. القاعدة الورقية: MAX_CONTRACT_SIZE = 2% من الرأس المال.
"""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # work (4 levels up)
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "logs" / "trade_cycle" / "trading.log"
DB_PATH = DATA_DIR / "trade_cycle.db"

# trade-only (trade without withdraw) - key never for withdraw
# TRADE_MARK decides real vs paper trading: TRADE_REAL => OKX real orders, TRADE_ONLY => paper simulation
import os
TRADE_MARK = os.environ.get("TRADE_MARK", "TRADE_ONLY")
real_trade = TRADE_MARK != "TRADE_ONLY"

def _log(msg: str):
    print(f"[trading] {msg}")

def _connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _simulate_final_price(side: str, entry: float, size: float, risk_pct: float, open_trades: int) -> float:
    """تجربة بسيطة (مُحاكاة): لا تعتمد على أي صورة، لا تقييم للخسارة.
    تُستخدم للمحاكاة وورقة القيد; يجب استبدالها عند ربط البورصة الحقيقية (trade-only without withdraw)."""
    import random
    random.seed(hash(side + str(entry)) & 0xFFFFFFFF)
    # price wanders ±0.6% around entry
    drift = 0.0
    if open_trades >= 3:
        drift = 0.0002
    return round(entry * (1 + drift + random.uniform(-0.006, 0.006)), 6)


def place(decision: dict, paper_only: bool = True) -> dict:
    symbol = decision["symbol"]
    size = decision["size"]
    side = "buy"  # جديد trade

    # trade API keys (trade-only without withdraw) -> read from env
    mark = decision.get("mark", TRADE_MARK)
    if mark and "TRADE_ONLY" in mark.upper():
        real_trade = False
    else:
        real_trade = TRADE_MARK == "TRADE_REAL"

    # final price simulation
    equity = 10000.0  # trade portfolio start
    # care ledger
    open_trades = _open_count()
    final_price = _simulate_final_price(side, decision["price"] or 42000.0, size, decision["stop_loss_pct"], open_trades)

    trade = {
        "symbol": symbol,
        "side": side,
        "size": size,
        "entry_price": round(decision["price"] or 42000.0, 2),
        "final_price": final_price,
        "pl": round((final_price - decision["price"]) * size, 2),
        "status": "open" if paper_only else "real_filled",
        "trade_mark": TRADE_MARK if real_trade else "paper",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _log(f"صفقة trade: symbol={symbol} side={side} size={size:.4f} entry={trade['entry_price']}")
    return trade


def _open_count() -> int:
    conn = _connect()
    n = conn.execute("SELECT COUNT(*) AS c FROM trades WHERE status='open'").fetchone()["c"]
    conn.close()
    return n


def persist(trade: dict, run_id: int) -> int:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO trades (run_id, symbol, side, size, price, status, reason, created_at, closed_at, pnl)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (run_id, trade["symbol"], trade["side"], trade["size"],
         trade["entry_price"], trade["status"], trade.get("reason", ""),
         trade["created_at"], trade.get("closed_at", ""), trade.get("pl", 0.0)),
    )
    tid = cur.lastrowid
    conn.commit()
    conn.close()
    return tid


if __name__ == "__main__":
    _log("Trading Agent (Doug) — trade only")
