# Trade Cycle — إطار العمل (Cycle Framework)

يُنفّذ هذا الإطار دورة سوقية من 6 وكلاء متعاونين، كل واحد بدوره واضح، ويتشارك في قاعدة بيانات SQLite واحدة:

1. **Research (Jim)** — يجمع الأخبار ومصادر crypto، ويصدر فرصاً مع مؤشرات `red flags`.
2. **Risk (Bob)** — يوافق أو يرفض بالكاملة، **دون** نموذج ذكاء اصطناعي، عن طريق قواعد Python ثابتة (أقصى حجم، stop-loss، سيولة، إلخ).
3. **Trading (Doug)** — ينفذ الصفقات المعتمَدة فقط، عبر API البورصة، بدائيًّا من trading ورقي.
4. **Records (Jill)** — يسجل كل صفقة وحالة في SQLite، ويحسب P&L اليومي.
5. **CEO (Bill)** — يقرأ التقرير ويراجع القواعد، ويعدّلها (متاحة كمتغيرات Python في `config.py`).
6. **Feedback (Grok / OpenRouter)** — نموذج خارجي يراجع النتائج مرتين أسبوعياً (مُسماة `FEEDBACK_DAYS`).

## الملفات
```
work/agents/trade_cycle/
├── config.py          # القواعد الثابتة وخواص السوق والبيانات
├── database.py        # ربط قاعدة بيانات SQLite ونماذج الصدارات
├── agents/
│   ├── __init__.py
│   ├── research.py    # Jim
│   ├── risk.py        # Bob
│   ├── trading.py     # Doug
│   ├── records.py     # Jill
│   ├── ceo.py         # Bill
│   └── feedback.py    # Grok / OpenRouter
├── loop.py            # سكِب البدء (بحث ← مراجعة ← تداول ← سجل ← تقرير ← تغذية)
└── README.md          # وثائق الإطار
```

## المتطلبات المحلية
- `python >= 3.10`
- SQLite (مُضمّن في Python، بدون إضافات)
- `requests` (للاسترجاع الخارجي واكتشاف البيانات)
- نماذج LLM (Ollama محلي مُعتاد، أو OpenRouter/Groq). ملاحظة: النماذج المحلية على CPU قوية لبعض المهام، فنستخدم OpenRouter/Groq للبحث والقرارات، ونركز على النماذج المحلية للمهام الخفيفة.

> **أولوية قوية:** لا تُفتح أموال حقيقية أبداً. يبدأ الإطار بالتداول الورقي فقط (`PAPER_ONLY = True`). يمكن تعطيل ذلك فقط بمفتاح أحادي `REALTrade` في ملف `.env` (وفق مبدأ trade-only without withdraw).

## الإعداد السريع
1. `cp .env.example .env` واملأها (مفتاح trade-only، رمز البورصة، إلخ).
2. `python loop.py --once` للاختبار في دورة واحدة.
3. `python loop.py --daemon` لسير الدورة تلقائياً.
