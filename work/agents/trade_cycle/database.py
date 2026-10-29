"""Trade Cycle — Database layer

يعمل sqlite3 محلي للاتصال وإنشاء الجداول الأولية. جميع الوكلاء (6) يقرأون
ويكتبون نفس قاعدة البيانات في كل دورة من دورات المسودة التجريبية (loop).
"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "trade_cycle.db"


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.executescript(
        """
        -- دورات выполнения (single source of truth for the loop)
        CREATE TABLE IF NOT EXISTS cycle_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            phase TEXT NOT NULL,
            status TEXT NOT NULL,
            summary TEXT DEFAULT '',
            error TEXT DEFAULT ''
        );

        -- مخرجات البحث (Jim): الفرص والملاحظات
        CREATE TABLE IF NOT EXISTS research (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            symbol TEXT,
            source TEXT,
            title TEXT,
            url TEXT,
            price REAL,
            market_cap REAL,
            volume_24h REAL,
            change_24h REAL,
            red_flags TEXT,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY (run_id) REFERENCES cycle_runs(id)
        );

        -- قرارات المخاطر (Bob): موافقة/رفض، والسبب
        CREATE TABLE IF NOT EXISTS risk_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            contract_id INTEGER,
            symbol TEXT,
            size REAL,
            stop_loss REAL,
            take_profit REAL,
            reason TEXT,
            decision TEXT NOT NULL,   -- approve / reject
            reviewed_by TEXT DEFAULT '',
            created_at TEXT,
            FOREIGN KEY (run_id) REFERENCES cycle_runs(id)
        );

        -- صفقات (Doug): المتفقات والمنفذة
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            symbol TEXT,
            side TEXT,            -- buy / sell
            size REAL,
            price REAL,
            status TEXT NOT NULL, -- pending / open / closed / rejected
            reason TEXT DEFAULT '',
            created_at TEXT,
            closed_at TEXT DEFAULT '',
            pnl REAL DEFAULT 0,
            FOREIGN KEY (run_id) REFERENCES cycle_runs(id)
        );

        -- سجل Rewards والتداول اليومي (Jill)
        CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            symbol TEXT,
            side TEXT,
            size REAL,
            entry_price REAL,
            exit_price REAL,
            pnl REAL,
            fees REAL DEFAULT 0,
            status TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (run_id) REFERENCES cycle_runs(id)
        );

        -- تقرير اليوم (Bill) + ملاحظات القواعد
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            total_trades INTEGER DEFAULT 0,
            total_pnl REAL DEFAULT 0,
            equity REAL DEFAULT 0,
            rules_overview TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            generated_at TEXT
        );

        -- مراجعة Feedback (Grok / OpenRouter) للمعلومات الأسبوعية
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            feedback_at TEXT NOT NULL,
            summary TEXT,
            changes_requested TEXT,
            applied INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY (run_id) REFERENCES cycle_runs(id)
        );

        CREATE INDEX IF NOT EXISTS idx_research_run ON research(run_id);
        CREATE INDEX IF NOT EXISTS idx_risk_run ON risk_decisions(run_id);
        CREATE INDEX IF NOT EXISTS idx_trade_run ON trades(run_id);
        CREATE INDEX IF NOT EXISTS idx_ledger_run ON ledger(run_id);
        CREATE INDEX IF NOT EXISTS idx_feedback_run ON feedback(run_id);
        """
    )

    # شروط أولية للمحفظة المستخدمة (ورقي)
    cur.execute(
        "INSERT OR IGNORE INTO cycle_runs (started_at, phase, status) VALUES (?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), "init", "ok"),
    )
    conn.commit()
    conn.close()
    print(f"[DB] Initialized trade_cycle.db at {DB_PATH}")
