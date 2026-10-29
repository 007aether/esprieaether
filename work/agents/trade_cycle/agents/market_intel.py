#!/usr/bin/env python3
"""
MarketIntel Agent - استخراج البيانات من السوق والمنصات المالية
"""

import os, json, sqlite3, hashlib
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.parent
DB_PATH = BASE_DIR / "work" / "data" / "market_intel.db"

class MarketIntelAgent:
    def __init__(self):
        self.db_path = DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                source TEXT,
                price REAL,
                market_cap REAL,
                volume_24h REAL,
                change_24h REAL,
                timestamp TEXT,
                notes TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                threshold REAL,
                alert_type TEXT,
                triggered_at TEXT,
                status TEXT
            )
        """)
        conn.commit()
        conn.close()

    def fetch_markets(self, symbols=["BTC", "ETH", "SOL"]):
        results = []
        for symbol in symbols:
            result = {
                "symbol": symbol,
                "source": "local",
                "timestamp": datetime.now().isoformat(),
                "price": None,
                "market_cap": None,
                "volume_24h": None,
                "change_24h": None,
                "notes": "بيانات محلية - سيتم تحديثها عند ربط البيانات الحقيقية"
            }
            results.append(result)
        return results

    def check_alerts(self, symbols):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        alerts = []
        for symbol in symbols:
            cur.execute("SELECT * FROM alerts WHERE symbol=? AND status='active'", (symbol,))
            alert = cur.fetchone()
            if alert:
                alerts.append({
                    "id": alert[0],
                    "symbol": alert[1],
                    "threshold": alert[2],
                    "alert_type": alert[3],
                    "triggered_at": alert[4],
                    "status": alert[5]
                })
        conn.close()
        return alerts

    def save_market_data(self, data):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO market_data (symbol, source, price, market_cap, volume_24h, change_24h, timestamp, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (data.get("symbol"), data.get("source"), data.get("price"),
              data.get("market_cap"), data.get("volume_24h"),
              data.get("change_24h"), data.get("timestamp"), data.get("notes")))
        conn.commit()
        conn.close()

    def add_alert(self, symbol, threshold, alert_type):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO alerts (symbol, threshold, alert_type, triggered_at, status)
            VALUES (?, ?, ?, ?, ?)
        """, (symbol, threshold, alert_type, datetime.now().isoformat(), "active"))
        conn.commit()
        conn.close()

    def get_alerts(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM alerts WHERE status='active'")
        alerts = cur.fetchall()
        conn.close()
        return alerts

    def generate_report(self, symbols=None):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        if symbols:
            for symbol in symbols:
                cur.execute("SELECT * FROM market_data WHERE symbol=?", (symbol,))
                data = cur.fetchone()
                if data:
                    yield {
                        "id": data[0],
                        "symbol": data[1],
                        "source": data[2],
                        "price": data[3],
                        "market_cap": data[4],
                        "volume_24h": data[5],
                        "change_24h": data[6],
                        "timestamp": data[7],
                        "notes": data[8]
                    }
        else:
            cur.execute("SELECT * FROM market_data ORDER BY id DESC LIMIT 100")
            rows = cur.fetchall()
            for row in rows:
                yield {
                    "id": row[0],
                    "symbol": row[1],
                    "source": row[2],
                    "price": row[3],
                    "market_cap": row[4],
                    "volume_24h": row[5],
                    "change_24h": row[6],
                    "timestamp": row[7],
                    "notes": row[8]
                }
        conn.close()
