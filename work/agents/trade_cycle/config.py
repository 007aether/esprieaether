"""Trade Cycle — Configuration (قواعد الصفقة والسوق والمراقبة)

جميع القواعد هنا قابلة للتعديل يدويًا بواسطة CEO (Bill) أو خطة تحديث في
loop.py. صُنفت كثابت Python — لا تُقرّر هذا الجزء بالذكاء الاصطناعي.
"""

# ── خيارات التشغيل ───────────────────────────────────────────────
PAPER_ONLY = True          # الشحن الورقي فقط
MAX_CONTRACTS = 3          # أقصى عدد للعقود أو الصفقات المفتوحة دفعة واحدة.
RISK_PER_TRADE = 0.02      # مخاطرة لا تزيد عن 2% من رأس المال لكل صفقة.
STOP_LOSS_PCT = 0.04       # توقف تلقائي عند خسارة 4%.
TAKE_PROFIT_PCT = 0.08     # حجز ربح عند 8% (يقترح، لا يُجبر إلا إذا أخاف المخاطرة).
MIN_LIQUIDITY = 5_000_000  # الحد الأدنى للسيولة (تقريبي).
TRADING_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]  # دورة الأحد (لا عطلة يوم السبت).
FEEDBACK_DAYS = {1, 4}     # تذاكر Feedback: يكملان أو يمحوران في يومي الإثنين والخميس.
DAILY_REPORT_TO_TELEGRAM = True
TRADE_ONLY_MARK = "TRADE_REAL"   # العلم: trade_only مفعّل في .env

# ── البيانات المشتركة للوكلاء ────────────────────────────────────
# استُخدمها الوكلاء عند تفضيل واجهة أوصال خارجية أو محلية.
DEFAULT_MARKETS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
DEFAULT_FEED = {"cointelegraph": "rss", "theblock": "rss", "decrypt": "rss", "u.today": "rss"}

# ── أذونات trading الورقي (trade-only without withdraw) ───────────
import os

# استخدام المحلي Qwen3-Coder-30B بدلاً من API الخارجي
# Model: D:/AetherData/colibri-models/qwen3-coder-30b
# Router: http://127.0.0.1:8000/v1/chat/completions

# تفضيلات الذكاء الاصطناعي
DEFAULT_AI_MODEL = "qwen3-coder-30b"
AI_ROUTER_URL = "http://127.0.0.1:8000/v1/chat/completions"
AI_USE_LOCAL = True

# رأس المال الافتراضي للصفقات
DEFAULT_EQUITY = 1000.0

# أذونات trading الورقي (trade-only without withdraw)
TRADE_API_TOKEN = os.environ.get("TRADE_API_TOKEN", "")
TRADE_MARK = os.environ.get("TRADE_MARK", "TRADE_REAL")
