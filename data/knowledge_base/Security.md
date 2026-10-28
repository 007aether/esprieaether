# 🔒 الأمن (Security) — 1 اقتراح

## 1. حماية الفورية (Immediate Security)
- **قاعدة البيانات (SQLite):** تعطيل `WAL` و `journal_mode` إن وُجد تسريب للبيانات عبر `data/trade_cycle.db` و `self_improve_state.json`.
- **الجدار الناري (UFW):** تفعيل بورتات شرطية فقط: `5000`, `5100`, `5105`, `8000`, `11434`. بقا كل البورتات تبقا مغلقة.
- **الرقم السري (Secret):** حفظ `.env` في كل `.gitignore`، وتقليل `TELEGRAM_BOT_TOKEN` للسياقات غير الدموية.
