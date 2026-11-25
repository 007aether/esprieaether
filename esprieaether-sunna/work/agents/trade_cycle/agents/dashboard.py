#!/usr/bin/env python3
"""
Dashboard Agent - أدوات عرض البيانات الحية
يعرض بيانات النظام في الوقت الحقيقي
"""

import os, json, sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.parent
DB_PATH = BASE_DIR / "work" / "data" / "trade_cycle.db"

class DashboardAgent:
    def __init__(self):
        self.db_path = DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def get_cycle_status(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, status, phase, summary FROM cycle_runs ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        if row:
            return {
                "cycle_id": row[0],
                "status": row[1],
                "phase": row[2],
                "summary": row[3]
            }
        return None

    def get_trading_stats(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trades WHERE status='closed'")
        total_trades = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM trades WHERE status='open'")
        open_trades = cur.fetchone()[0]
        cur.execute("SELECT SUM(pnl) FROM trades WHERE status='closed'")
        total_pnl = cur.fetchone()[0] or 0
        cur.execute("SELECT AVG(pnl) FROM trades WHERE status='closed'")
        avg_pnl = cur.fetchone()[0] or 0
        conn.close()
        return {
            "total_trades": total_trades,
            "open_trades": open_trades,
            "total_pnl": total_pnl,
            "avg_pnl": avg_pnl
        }

    def get_recent_trades(self, limit=10):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT symbol, side, size, price, status, created_at FROM trades ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [{"symbol": r[0], "side": r[1], "size": r[2], "price": r[3],
                 "status": r[4], "created_at": r[5]} for r in rows]

    def get_recent_research(self, limit=20):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT symbol, source, price, change_24h, created_at FROM research ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [{"symbol": r[0], "source": r[1], "price": r[2], "change_24h": r[3], "created_at": r[4]} for r in rows]

    def get_recent_feedback(self, limit=10):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT summary, changes_requested, created_at FROM feedback ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [{"summary": r[0], "changes": r[1], "created_at": r[2]} for r in rows]

    def generate_dashboard_data(self):
        return {
            "cycle": self.get_cycle_status(),
            "trading": self.get_trading_stats(),
            "recent_trades": self.get_recent_trades(10),
            "recent_research": self.get_recent_research(20),
            "recent_feedback": self.get_recent_feedback(10)
        }
