"""Trade Cycle — orchestration (loop driver)

6 agents in sequence:
  1. research → 2. risk → 3. trading → 4. records → 5. ceo → 6. feedback

Shared SQLite: work/data/trade_cycle.db (see database.py)

Usage:
  python loop.py --once
  python loop.py --daemon          # every 3600s
  python loop.py --daemon --interval 1800
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

TC_DIR = Path(__file__).resolve().parent
# BASE_DIR = repo root (work/agents/trade_cycle → up 3)
BASE_DIR = TC_DIR.parent.parent.parent
sys.path.insert(0, str(TC_DIR))

from config import PAPER_ONLY  # noqa: E402
from database import get_conn, init_db  # noqa: E402

LOGS = BASE_DIR / "data" / "logs" / "trade_cycle"
LOGS.mkdir(parents=True, exist_ok=True)


def _log(step: str, msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {step.upper()} | {msg}")


def _new_run(phase: str, status: str, summary: str = "") -> int:
    """Always create a fresh cycle_runs row and return its id."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO cycle_runs (started_at, phase, status, summary) VALUES (?,?,?,?)",
        (datetime.now(timezone.utc).isoformat(), phase, status, summary),
    )
    rid = int(cur.lastrowid)
    conn.commit()
    conn.close()
    return rid


def _mark_run(rid: int, phase: str, status: str, summary: str = "") -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE cycle_runs SET phase=?, status=?, summary=? WHERE id=?",
        (phase, status, summary, rid),
    )
    conn.commit()
    conn.close()


def _send_telegram(text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat:
        _log("telegram", "skip (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set)")
        return
    try:
        import requests

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(
            url,
            json={"chat_id": chat, "text": text, "parse_mode": "Markdown"},
            timeout=15,
        )
        if r.status_code == 200:
            _log("telegram", "report sent")
        else:
            _log("telegram", f"send failed: {r.text[:80]}")
    except Exception as e:
        _log("telegram", f"error: {e}")


def generate_summary(run_id: int) -> str:
    conn = get_conn()
    try:
        trades = conn.execute(
            """
            SELECT COUNT(*) AS n,
                   COALESCE(SUM(CASE WHEN status='closed' THEN pnl ELSE 0 END), 0) AS p,
                   SUM(CASE WHEN status IN ('open','pending') THEN 1 ELSE 0 END) AS open_n
            FROM trades WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()
        research_n = conn.execute(
            "SELECT COUNT(*) AS n FROM research WHERE run_id = ?", (run_id,)
        ).fetchone()["n"]
        approved = conn.execute(
            "SELECT COUNT(*) AS n FROM risk_decisions WHERE run_id = ? AND decision = 'approve'",
            (run_id,),
        ).fetchone()["n"]
    finally:
        conn.close()

    mode = "PAPER" if PAPER_ONLY else "LIVE"
    lines = [
        f"📊 *Trade Cycle #{run_id}* ({mode})",
        f"🔍 Research rows: {research_n}",
        f"✅ Approved: {approved}",
        f"📈 Trades this run: {trades['n'] or 0} (open: {trades['open_n'] or 0})",
        f"💰 P&L (closed): {float(trades['p'] or 0):.2f}",
    ]
    return "\n".join(lines)


def run_once() -> int:
    """Run one full cycle. Returns run_id."""
    init_db()
    run_id = _new_run("start", "running", "trade_cycle paper cycle")
    _log("run", f"cycle #{run_id} started (PAPER_ONLY={PAPER_ONLY})")

    research = {"rows": []}
    decisions: list[dict] = []

    # 1) Research
    _log("run", "1/6 Research [Jim]")
    try:
        import agents.research as research_mod

        research = research_mod.run()
        research_mod.persist(research.get("rows", []), run_id)
        _log("run", f"opportunities: {len(research.get('rows', []))}")
    except Exception as e:
        _log("run", f"research error: {e}")
        _mark_run(run_id, "research", "error", str(e)[:200])

    # 2) Risk
    _log("run", "2/6 Risk [Bob]")
    try:
        import agents.risk as risk_mod

        for row in research.get("rows", []):
            dec = risk_mod.evaluate(row)
            risk_mod.persist(dec, run_id)
            decisions.append({"research": row, "decision": dec})
        approved_n = sum(1 for d in decisions if d["decision"].get("decision") == "approve")
        _log("run", f"approved: {approved_n}/{len(decisions)}")
    except Exception as e:
        _log("run", f"risk error: {e}")

    # 3) Trading
    _log("run", "3/6 Trading [Doug]")
    accepted = [d for d in decisions if d["decision"].get("decision") == "approve"]
    try:
        import agents.trading as trading_mod

        for d in accepted:
            tr = trading_mod.place(d["decision"], paper_only=PAPER_ONLY)
            trading_mod.persist(tr, run_id)
        _log("run", f"orders placed: {len(accepted)}")
    except Exception as e:
        _log("run", f"trading error: {e}")

    # 4) Records
    _log("run", "4/6 Records [Jill]")
    try:
        import agents.records as records_mod

        total = records_mod.summarize_day(run_id)
        _log("run", f"day P&L: {total.get('pnl', 0):.2f}")
    except Exception as e:
        _log("run", f"records error: {e}")

    # 5) CEO
    _log("run", "5/6 CEO [Bill]")
    try:
        import agents.ceo as ceo_mod

        ceo_mod.review(run_id)
    except Exception as e:
        _log("run", f"ceo error: {e}")

    # 6) Feedback
    _log("run", "6/6 Feedback")
    try:
        import agents.feedback as feedback_mod

        feedback_mod.process(run_id)
    except Exception as e:
        _log("run", f"feedback error: {e}")

    summary = generate_summary(run_id)
    _mark_run(run_id, "done", "ok", "cycle complete")
    _log("run", f"cycle #{run_id} done")
    print(summary)
    _send_telegram(summary)
    return run_id


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="EsprieAether Trade Cycle")
    p.add_argument("--once", action="store_true", help="Run a single cycle")
    p.add_argument("--daemon", action="store_true", help="Run continuously")
    p.add_argument("--interval", type=int, default=3600, help="Seconds between daemon cycles")
    args = p.parse_args()

    if args.once:
        run_once()
    elif args.daemon:
        _log("daemon", f"starting (interval={args.interval}s)")
        while True:
            try:
                run_once()
            except Exception as e:
                _log("daemon", f"cycle crashed: {e}")
            time.sleep(max(60, args.interval))
    else:
        p.print_help()
        print("\nExample: python loop.py --once")
