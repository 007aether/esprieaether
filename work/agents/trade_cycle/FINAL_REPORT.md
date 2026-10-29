# trade_cycle — التقرير النهائي

## ✅ الحالة
Trade Cycle (6 وكلاء + حلقة + SQLite 8 جداول) مكتمل ويعمل:
`python work/agents/trade_cycle/loop.py --once` → `return code 0`، دورة جديدة تُسجّل في `cycle_runs`، لا توجد أخطاء.

## 🧱 البنية
```
work/agents/trade_cycle/
├── loop.py                  # orchestration (6 مراحل)
├── flywheel.py              # entry point CLI (--once/--daemon/--summary)
├── database.py              # SQLite layer مشترك (7 جداول + cycle_runs)
├── config.py                # قواعد الصفقة الثابتة
├── agents/
│   ├── research.py (Jim)   # بحث + red flags
│   ├── risk.py (Bob)       # قواعد ثابتة Python (لا LLM)
│   ├── trading.py (Doug)   # تداول ورقي PAPER_ONLY
│   ├── records.py (Jill)   # SQLite + P&L يومي
│   ├── ceo.py (Bill)       # مراجعة + اقتراح قواعد
│   └── feedback.py (Grok)  # مراجعة أسبوعية
├── data/
│   └── trade_cycle.db       # 7 جداول (cycle_runs, research, risk_decisions, trades, ledger, reports, feedback)
├── README.md, commands.md, report.md, completion_summary.md
```

## 📊 الإحصائيات الحالية
| `cycle_runs` | **51** (طبيعي/ok) |
| `research` (source=coingecko) | **70** خيارات حقيقية من CoinGecko |
| `risk_decisions` | **70** |
| `trades` | **0** (ورقي فقط — PAPER_ONLY) |
| `feedback` | **13** تُسجّل تلقائياً كل دورة |
| آخر دورة | trade_cycle 51 → 12:50:36 (return code 0) |

## 🔧 ما تغير / ما أُصلح
1. **DB_PATH وحدة** — كل `agents/*.py` أصبح `BASE_DIR` 4 مستويات (`work`), فأصبحت `DB_PATH = work/data/trade_cycle.db`، متطابقة مع `database.py`.
2. **loop.py** — أُصلح `try/except` المكسور في البحث (كان `import` خارج `try`), صُرّف `research.get("rows", [])` لمنع `None` (LSP: `get` on None), وأُصلحت `total.get('pnl', 0)`.
3. **records.py** — `summarize_day` يعود `{trades, pnl, fees, closed}` مع قيم صفرية عند `None` (أصلح `sqlite3.Row` attribute error).
4. **feedback.py** — إزالة `run_id` من `SELECT id, run_id, summary FROM cycle_runs`، لأن `cycle_runs` لا يحتويه (المرمز `id`).
5. **research.py** — `persist(rows, run_id)` يعتمد `run_id` (تم إصلاح الإرسال من `loop.py`).
6. **self_heal_daemon.py** — `is_running("loop.py --daemon")` (دقة) + supervisor loop (180s) يبدأ/يعيد تشغيل trade_cycle.
7. **التشغيل بدون مؤثر**: trade_cycle يعمل تلقائياً (DB 50→51 cycles، 13 feedback) داخل 45s.

## ⚙️ ربط self_heal_daemon بحلقة trade_cycle
`self_heal_daemon.py` (الملف `work/autonomous/self_heal_daemon.py`) يُنفذ:
```
start_evolve() → start_hermes() → start_services() →
if not is_running("loop.py --daemon"):
    Popen([python, work/agents/trade_cycle/loop.py, "--daemon"], ...)
self.monitor()   # كل 180s: يعيد بدء trade_cycle إذا توقف
```
السجل `data/autonomous_selfheal_daemon.log` يؤكد:
```
🚀 بدء Trade Cycle loop (.../loop.py --daemon)...
✅ Trade Cycle في العمل
```
وتم تشغيله في الخلفية مع `log` = `data/autonomous_selfheal_daemon.log`.

## 🎛️ التشغيل والدعم
- **دخول واحد**: `python work/autonomous/self_heal_daemon.py` (background، lint=log)
- **دورة دورية**: `loop.py --daemon` → cycle one + sleep 3600s (Supervised)
- **ورقي فقط**: كل الصفقات `PAPER_ONLY = True`، لا أوامر حقيقية.
- **Telestop**: `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` غير مُملوء في الساندبكس → التقارير تُطبع على `stdout` فقط (لا رابط تيليغرام).
- **ملفات جاهزة للتشغيل**: `commands.md`, `README.md`, `report.md`, `completion_summary.md`.

## ⚠️ ما ينقص (مهام قادمة — اختياري)
- `research` `price` يرجع NULL في هذا الساندبكس التجريبي (market_cap/volume/change 24h حقيقية).
- `.env` الفعلي (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `FEEDBACK_MODEL`) في خارج الدردشة (secret-bearer) → ربط التقارير التليجرامية يكون عند تزويدها.
- تفعيل دورة متوقفة (`loop.py --daemon` كل ساعة) يدوياً عند تثبيت `.env`.
