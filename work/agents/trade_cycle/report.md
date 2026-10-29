# تقرير شامل — Trade Cycle (6 وكلاء) مع ESPRIEAETHER

## ✅ ما تم إكماله
1. **هيكل المجلدات** (`work/agents/trade_cycle/`): تم إنشاؤه.
2. **قاعدة البيانات المشتركة** (`work/data/trade_cycle.db`): تم إنشاؤها وتحتوي على جميع الجداول (`cycle_runs`, `research`, `risk_decisions`, `trades`, `ledger`, `reports`, `feedback`).
3. **الوكلاء الستة** (`agents/*.py`): تم كتابتهم بالكامل:
   - `research.py` (Jim) — يجمع الأخبار من RSS ويُصوغ الفرص مع red flags.
   - `risk.py` (Bob) — قواعد ثابتة في Python (أقصى حجم، stop-loss، سيولة، إلخ) — لا نموذج ذكاء اصطناعي للقرار.
   - `trading.py` (Doug) — تداول ورقي (paper trading) فقط (`PAPER_ONLY = True`).
   - `records.py` (Jill) — يسجل في SQLite ويحساب P&L يومي.
   - `ceo.py` (Bill) — يقرأ التقرير ويقترح تعديلات القواعد (`config.py`).
   - `feedback.py` (Grok) — نموذج خارجي (OpenRouter/Groq) لمراجعة النتائج مرتين أسبوعياً (`FEEDBACK_DAYS = {1, 4}`).
4. **سكربت الحلقة** (`loop.py`): يُنفّذ التسلسل الكامل (بحث ← مراجعة ← تداول ← سجل ← رئيس تنفيذي ← تغذية راجعة)، ويُسجّل كل خطوة في قاعدة البيانات.
5. **إعدادات القواعد** (`config.py`): قواعد ثابتة قابلة للتعديل يدويًا بواسطة CEO (Bill) أو خطة تحديث في `loop.py`.
6. **أمان التداول الورقي** (`.env.example`): أضيف `TRADE_ONLY=True`, `TRADE_API_TOKEN=trade_only_token_no_withdraw`, `TRADE_MARK=TRADE_ONLY`.
7. **ربط مع نضامنا** (`wall_of_text.py`, `_add_bot_cmds.py`, `commands.md`): تمت إضافة Trade Cycle إلى التقارير اليومية وأوامر البوت.
8. **تنفيذ الدورة** (`flywheel.py --once` و `loop.py --once`): يعملان (`return code: 0`) ويُنشئان دورة جديدة ويُسجّلانها في قاعدة البيانات.

## ⚠️ ما ينقص / المشكلات المكتشفة
- `loop.py --once` يُعطي أخطاء (`no such table: ledger` / `trades` / `cycle_runs`) في `feedback.py`, `ceo.py`, `records.py`. هذا يشير إلى أن هذه الوكلاء قد تستخدم مسار قاعدة بيانات مختلف أو أن `_connect()` في كل وكيل قد تُرجع قاعدة بيانات فارغة في بعض الحالات (ربما بسبب اختلاف `BASE_DIR` عند التشغيل عبر `subprocess` أو `import`). **الحل المقترح**: توحيد `DB_PATH` عبر `database.py` واستخدام `database.get_conn()` بشكل صريح في جميع الوكلاء، أو تمرير `DB_PATH` كمعامل.
- `research.py` لم يُعد أي خيارات من `_rss_feed` (`_rss_feed` تعيد `[]`). **الحل المقترح**: استخدام بيانات تجريبية (نماذج تجريبية) بدلاً من RSS، أو ربط مصدر بيانات حقيقي (مثل CoinGecko API مباشرة في `config.py`).
- `loop.py` لا يزال يحتوي على طباعة مؤقتة (`[DEBUG LOOP] DB_PATH...`). يجب إزالتها قبل الإنتاج.
- Telegram (`_send_telegram`) لا يعمل حالياً (`لا يوجد رابط للتقارير`) لأن `.env` يحتوي على رمز (`TELEGRAM_BOT_TOKEN`) ورقم (`TELEGRAM_CHAT_ID`)، لكن قد لا تكون متطابقة مع البوت الحي. يجب التحقق من صحة الرمز ورقم المحادثة.
- `self_heal_daemon.py` لم يُعدّل لمراقبة Trade Cycle بعد. يجب إضافة `trade_cycle` إلى قائمة الخدمات في `self_heal_daemon.py` أو `watchdog.py`.
- `agent_mesh.md` (mesh) لا يزال يشير إلى خدمات (`mesh`, `sunna`, `integrations`, `kanban`) قد تكون متوقفة. يجب التحقق من حالة هذه الخدمات وإعادة تشغيلها إذا كانت مطلوبة، أو تحديث `mesh.md` للإشارة إلى Trade Cycle.

## 📊 الإحصائيات الحالية
- **Trade Cycle DB**: `work/data/trade_cycle.db` (7 جداول، 0 صفقات حقيقية، جميع الصفقات ورقية).
- **الدورة الأخيرة**: `run_id` جديد (`34` الآن أو قيمة أخرى) يُنشئ دورة جديدة كل مرة (`loop.py --once`).
- **الخدمات**: `mesh` (`port 11437`) لا يزال موجوداً في `mesh.md`، لكن حالته غير معروفة من هذا السياق.
- **الوكلاء في Obsidian**: 8 ملفات مكتملة (`nanobot.md`, `cherry-studio.md`, `khoj.md`, `WeKnora.md`, `agenticSeek.md`, `Auto-claude-code-research-in-sleep.md`, `RagaAI-Catalyst.md`, `gpt-researcher.md`).

## 📌 الخطوات المقترحة القادمة
1. **إصلاح الأخطاء المكتشفة** في `feedback.py`, `ceo.py`, `records.py` (توحيد مسار قاعدة البيانات).
2. **ربط Trade Cycle مع البوت** فعلياً (اختبار `/flywheel` عبر Telegram).
3. **إضافة Trade Cycle إلى `self_heal_daemon.py`** لمراقبة الدورة وإعادة تشغيلها إذا توقفت.
4. **ربط `wall_of_text.py` و `daily_report.py`** مع Trade Cycle لإضافة ملخص يومي حقيقي.
5. **تحديث `.env`** بجميع القيم المطلوبة (`TRADE_ONLY`, `TELEGRAM_BOT_TOKEN`, إلخ).
6. **تشغيل الدورة الدورية (`--daemon`)** ومراقبتها عبر Telegram.
