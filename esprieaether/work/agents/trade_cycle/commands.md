# Trade Cycle Commands

## Overview
Trade Cycle is a 6-agent autonomous loop (Research → Risk → Trading → Records → CEO → Feedback) operating in PAPER ONLY mode (no real funds at risk). It reads and writes to `work/data/trade_cycle.db`.

## Usage (CLI / Loop)
```bash
python work/agents/trade_cycle/loop.py --once
python work/agents/trade_cycle/flywheel.py --once
python work/agents/trade_cycle/flywheel.py --summary
```

## Integration Points
- **Database**: `work/data/trade_cycle.db` (SQLite)
- **Agent files**: `work/agents/trade_cycle/agents/*.py`
- **Config**: `work/agents/trade_cycle/config.py`
- **Orchestrator**: `work/agents/trade_cycle/loop.py`
- **Telegram**: Reports sent when `.env` has `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`

## Safety Rules (Hard-Coded in Python — Not LLM Decisions)
- `PAPER_ONLY = True` (no real orders unless `.env` sets `TRADE_ONLY = False`)
- `MAX_CONTRACTS = 3`
- `RISK_PER_TRADE = 0.02` (2% of portfolio per trade)
- `STOP_LOSS_PCT = 0.04` (4% automatic stop-loss)
- `TAKE_PROFIT_PCT = 0.08` (8% target)
- Trade-only keys (no withdraw permission) must be set in `.env`

## What is Completed
- [x] `agents/research.py` (Jim)
- [x] `agents/risk.py` (Bob)
- [x] `agents/trading.py` (Doug)
- [x] `agents/records.py` (Jill)
- [x] `agents/ceo.py` (Bill)
- [x] `agents/feedback.py` (Grok)
- [x] `loop.py` (orchestrator)
- [x] `flywheel.py` (entry point + CLI)
- [x] `database.py` (shared SQLite layer)
- [x] `config.py` (rules)

## What Remains / Gaps
- `loop.py` occasionally reports `no such table: ledger` / `trades` / `cycle_runs` inside `feedback.py`, `ceo.py`, and `records.py` even though the tables exist in the DB. This suggests the `sqlite3.connect(DB_PATH)` in those agent files may be resolving to a different DB instance (possibly due to relative path differences when run via subprocess vs import). **Fix needed**: standardize `DB_PATH` resolution (e.g., resolve absolute path at import time) or pass the DB handle explicitly.
- `research` agent currently returns 0 results from RSS feeds (`_rss_feed` returns `[]`). **Fix**: either use a mock data fallback (simulated market data) or integrate a reliable feed endpoint.
- Telegram reporting (`_send_telegram`) requires `.env` tokens; currently skipped because `.env` has tokens but maybe `TELEGRAM_CHAT_ID` is set but `TELEGRAM_BOT_TOKEN` may not match live bot authorization.
- `feedback.py` uses `FEEDBACK_MODEL` from `.env`; no external LLM call is made (placeholder only).
- Integration with `esprieaether.py` (main router) is not yet wired: `work/agents/trade_cycle/` is standalone; it should be callable as `from work.agents.trade_cycle.flywheel import cycle_once` or integrated into the orchestrator (`src/agents/` or `src/autonome_evolve.py`).
- `AGENTS.md`, `STATUS.md`, and `development_plan.md` should be updated with Trade Cycle references.
- The `self_heal_daemon.py` should be updated to monitor and restart `trade_cycle` services if they stop.
- No `systemd` timer is configured yet; a Windows-compatible cron/job (e.g., Python `schedule` or `apscheduler`) needs to be added for continuous loop operation (`--daemon`).
