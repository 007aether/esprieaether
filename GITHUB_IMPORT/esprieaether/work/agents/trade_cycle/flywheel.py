"""
Flywheel — trading cycle agents (paper trading only)
------------------------------------------
Usage:
    python -m flywheel  --once      (run one full cycle)
    python -m flywheel  --daemon    (run continuously)
    python -m flywheel  --summary   (show last cycle report)

This module connects to the ESPRIEAETHER system via the shared SQLite
trade_cycle.db and sends reports through Telegram when configured.
"""

import argparse
import json
import sqlite3
from pathlib import Path

from agents.research import run as run_research
from agents.risk import evaluate as run_risk, persist as persist_risk
from agents.trading import place as run_trading, persist as persist_trading
from agents.records import summarize_day
from agents.ceo import review as run_ceo
from agents.feedback import process as run_feedback
from database import init_db, DB_PATH, get_conn


def cycle_once() -> int:
    """تُنفّذ دورة واحدة كاملة من الوكلاء الستة (ورقي)."""
    init_db()
    conn = get_conn()
    # إنشاء دورة جديدة دائماً
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO cycle_runs (started_at, phase, status, summary) VALUES (?, ?, ?, ?)",
        ("2026-10-24 01:00:00", "start", "init", "دورة تجريبية جديدة"),
    )
    run_id = cur.lastrowid
    conn.commit()
    conn.close()

    # 1) بحث
    print("[Jim] البحث...")
    picks = run_research()
    # حفظ البيانات في البحث
    conn = get_conn()
    cur = conn.cursor()
    for p in picks.get("rows", []):
        cur.execute(
            "INSERT INTO research (run_id, symbol, source, title, url, market_cap, volume_24h, change_24h, red_flags, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, p.get("symbol"), p.get("source"), p.get("title"), p.get("url"),
             p.get("market_cap"), p.get("volume_24h"), p.get("change_24h"),
             p.get("red_flags"), p.get("notes"), p.get("created_at")),
        )
    conn.commit()
    conn.close()

    # 2) مخاطر
    print("[Bob] المخاطر...")
    decisions = []
    for p in picks.get("rows", []):
        dec = run_risk(p, {}, [])
        # حفظ القرار
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO risk_decisions (run_id, symbol, size, stop_loss, take_profit, reason, decision, reviewed_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, dec.get("symbol"), dec.get("size"), dec.get("stop_loss_pct"), dec.get("take_profit_pct"),
             "; ".join(dec.get("reasons", [])) or "موافقة", dec.get("decision"), "Bob", "2026-10-24 01:00:00"),
        )
        conn.commit()
        conn.close()
        decisions.append({"research": p, "decision": dec})

    # 3) تداول ورقي
    print("[Doug] التداول الورقي...")
    accepted = [d for d in decisions if d["decision"].get("decision") == "approve"]
    trades = []
    for d in accepted:
        tr = run_trading(d, paper_only=True)
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO trades (run_id, symbol, side, size, price, status, reason, created_at, closed_at, pnl) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, tr.get("symbol"), tr.get("side"), tr.get("size"), tr.get("entry_price"),
             tr.get("status"), tr.get("reason"), tr.get("created_at"), tr.get("closed_at"), tr.get("pl", 0.0)),
        )
        conn.commit()
        conn.close()
        trades.append(tr)

    # 4) سجلات
    print("[Jill] السجلات...")
    for tr in trades:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ledger (run_id, symbol, side, size, entry_price, exit_price, pnl, fees, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, tr.get("symbol"), tr.get("side"), tr.get("size"), tr.get("entry_price"),
             tr.get("final_price"), tr.get("pl", 0.0), 0.0, tr.get("status"), tr.get("created_at")),
        )
        conn.commit()
        conn.close()

    # 5) الرئيس التنفيذي
    print("[Bill] المدير...")
    # لا تعديل مباشر للقواعد هنا؛ يرجع إلى مراجعة القواعد يدويًا

    # 6) تغذية راجعة
    print("[Grok] التغذية...")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO feedback (run_id, feedback_at, summary, changes_requested, applied, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (run_id, "2026-10-24 01:00:00", f"دورة {run_id} مكتملة (ورقي)", "لا تغيير حالياً", 0, "2026-10-24 01:00:00"),
    )
    conn.commit()
    conn.close()

    print(f"✅ دورة trade_cycle {run_id} اكتملت (ورقي فقط، لا صفقات حقيقية)")
    return run_id


def show_summary(run_id: int) -> str:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM cycle_runs WHERE id=?", (run_id,)).fetchall()
    trades = conn.execute("SELECT symbol, side, size, pnl FROM trades WHERE run_id=?", (run_id,)).fetchall()
    ledgers = conn.execute("SELECT symbol, pnl FROM ledger WHERE run_id=?", (run_id,)).fetchall()
    conn.close()
    lines = [f"📊 ملخص دورة trade_cycle — {run_id}"]
    for r in rows:
        lines.append(f"  دورة: {r['phase']} / {r['status']} — {r['summary']}")
    lines.append(f"  الصفقات: {len(trades)}")
    for t in trades:
        lines.append(f"    {t['symbol']} {t['side']} size={t['size']} pnl={t['pnl']}")
    total_pnl = sum(l["pnl"] for l in ledgers)
    lines.append(f"  صافي الأرباح اليومي: {total_pnl:.2f} (ورقي)")
    return "\n".join(lines)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true", help="تشغيل دورة واحدة")
    p.add_argument("--daemon", action="store_true", help="تشغيل دوري")
    p.add_argument("--summary", action="store_true", help="عرض ملخص الدورة الأخيرة")
    args = p.parse_args()
    if args.summary:
        conn = sqlite3.connect(str(DB_PATH))
        row = conn.execute("SELECT MAX(id) FROM cycle_runs").fetchone()
        conn.close()
        latest = row[0] if row and row[0] else 0
        if latest > 0:
            print(show_summary(latest))
        else:
            print("لا توجد دورات بعد.")
    elif args.once:
        cycle_once()
    elif args.daemon:
        while True:
            cycle_once()
            time.sleep(3600)
    else:
        print("استخدم --once أو --daemon أو --summary")
