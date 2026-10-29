"""Risk Agent — Bob

قواعد معرفية ثابتة (Python) لقبول أو رفض الصفقة. لا يوجد نموذج ذكاء اصطناعي
للقرار. البيانات الوحيدة التي يدخل بها الملف هي من research + صفقتك.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # work (4 levels up)
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "logs" / "trade_cycle" / "risk.log"
DB_PATH = DATA_DIR / "trade_cycle.db"

# ── قواعد المخاطر (تاريخية وقابلة للتعديل بواسطة CEO) ─────────
RISK_RULES = {
    "max_contract_size_pct": 0.05,          # لا تزيد الصفقة عن 5% من رأس المال
    "max_open_trades": 3,                    # عدد مفتوح في نفس الوقت
    "stop_loss_pct": 0.04,                   # توقف تلقائي عند 4% خسارة
    "take_profit_pct": 0.08,                 # ربح 8% (يعمل فقط في الحالات الورقية)
    "min_market_cap_usd": 100_000_000,       # لا تداول العملات الرقمية ذات السوق الصغير
    "min_liquidity_usd": 5_000_000,          # سيولة الحد الأدنى
    "forbidden_terms": ["hack", "bypass", "scam", "rug pull"],
    "allowed_symbols": ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE"],
}


def _log(msg: str) -> None:
    print(f"[risk] {msg}")


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _current_equity() -> float:
    """عند بدء الفحص، الورقة الافتراضية 10000, تم احتساب P&L في ledger."""
    conn = _connect()
    total = conn.execute("SELECT COALESCE(SUM(pnl), 0) AS s FROM ledger").fetchone()["s"]
    conn.close()
    return 10000.0 + total


def evaluate(research_row: dict[str, Any]) -> dict[str, Any]:
    symbol = research_row.get("symbol", "").upper()
    flags = research_row.get("red_flags", "").lower()
    price = research_row.get("price", 0.0)
    market_cap = research_row.get("market_cap") or 0.0
    volume_24h = research_row.get("volume_24h") or 0.0

    reasons = []
    approved = True

    if symbol not in RISK_RULES["allowed_symbols"]:
        approved = False
        reasons.append(f"رمز غير مسموح: {symbol}")

    if market_cap < RISK_RULES["min_market_cap_usd"]:
        approved = False
        reasons.append(f"السوق الصغير: {market_cap:,.0f}")

    if volume_24h < RISK_RULES["min_liquidity_usd"]:
        approved = False
        reasons.append(f"سيولة منخفضة: {volume_24h:,.0f}")

    bad = [t for t in RISK_RULES["forbidden_terms"] if t in flags]
    if bad:
        approved = False
        reasons.append("فعل سلبي: " + ", ".join(bad))

    # محايدة: حجم الحساب مناسب (ورقي 10000 وقيمة 10,200)
    equity = _current_equity()
    max_size = equity * RISK_RULES["max_contract_size_pct"]

    decision = "approve" if approved else "reject"
    return {
        "decision": decision,
        "symbol": symbol,
        "size": max_size,
        "price": 0.0,  # قيمة سوقية (بحاجة للإدخال)
        "stop_loss_pct": RISK_RULES["stop_loss_pct"],
        "take_profit_pct": RISK_RULES["take_profit_pct"],
        "market_cap": market_cap,
        "volume_24h": volume_24h,
        "reasons": reasons,
        "rule_set": RISK_RULES,
    }


def persist(decision: dict[str, Any], run_id: int) -> int:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO risk_decisions
           (run_id, symbol, size, stop_loss, take_profit, reason, decision, reviewed_by, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (run_id, decision["symbol"], decision["size"], decision["stop_loss_pct"],
         decision["take_profit_pct"], "; ".join(decision["reasons"]) or "موافقة",
         decision["decision"], "Bob", datetime.now(timezone.utc).isoformat()),
    )
    rid = cur.lastrowid
    conn.commit()
    conn.close()
    return rid


if __name__ == "__main__":
    _log(f"Risk rules: {RISK_RULES}")
