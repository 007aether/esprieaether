# 🧪 الاختبار (Testing) — 1 اقتراح

## 1. Automated Test Suite
- **Tool:** `pytest` + `pytest-cov` (مثبت في `.venv`)
- **الهدف:** 200+ tests ذاتية لكل `src/*.py`
- **التشغيل:**
  ```bash
  cd /c/Users/ESPRIEAETHER/Desktop/esprieaether
  .venv/Scripts/python -m pytest src/ -v --cov=src --cov-report=term-missing
  ```
- **قاعدة البيانات:** `data/trade_cycle.db` (cycle_runs, trades, ledger, research, feedback)
- **الإضافة لجميع services:** `src/bot.py`, `src/web_interface.py`, `src/bot_heartbeat.py`, `src/watchdog.py`
