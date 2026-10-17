"""
⚡ EsprieAether - Telegram Bot Controller
بوت تيليغرام للتحكم الكامل في النظام
"""
import os
import sys
import json
import subprocess
import logging
from datetime import datetime
from cloud_fallback import CloudFallback
from ask_agent import AskAgent
from smart_alerts import SmartAlerts
from log_analyzer import LogAnalyzer
from auto_apply import AutoApply
from market_watcher import MarketWatcher
from daily_digest import DailyDigest
from bandwidth_agent import BandwidthAgent
from pharos_agent import PharosAgent
from self_evolve import SelfEvolve
from pathlib import Path

# مسار المشروع
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from dotenv import load_dotenv

from jarvis_bridge import JarvisBridge

# محرك Hermes (اختياري — يُحمّل عند الطلب)
try:
    from src.hermes_bridge import HermesBridge
except ImportError:
    HermesBridge = None

from vpn_agent import VPNAgent
from airdrop_agent import AirdropAgent

# ─── الإعدادات ───
# BOT_ENV: يسمح بتشغيل بوتات متعددة ف نفس الوقت (كل واحد env خاص)
# مثال: BOT_ENV=.env.bot1 uv run python src/bot.py
# override=True: .env.botX يفوق .env الأساسي (uv run كيقرا .env تلقائياً)
BOT_ENV = os.getenv("BOT_ENV", ".env")
load_dotenv(BASE_DIR / BOT_ENV, override=True)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
AETHER_ID = os.getenv("AETHER_ID", "007aether")
# اسم البوت ف الـ log (باش نفرّق بين البوتات)
BOT_NAME = os.getenv("BOT_NAME", "aether")

# ─── Logger (log خاص بكل بوت) ───
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / f"bot_{BOT_NAME}.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(f"aether-bot-{BOT_NAME}")


def md_escape(text: str) -> str:
    """يهرّب رموز Markdown ف المحتوى الديناميكي (ردود AI، أسعار...)
    باش Telegram ما يرفضش الرسالة بـ 'Can't parse entities'."""
    if not text:
        return ""
    # رموز Markdown classic: _ * ` [
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, "\\" + ch)
    return text


def md_safe(text: str, parse_mode: str = "Markdown") -> tuple:
    """يرجع (text, parse_mode) — إذا فشل الـ escape، يرجع بلا parse_mode
    حتى ما يطيحش الـ handler الكل."""
    return md_escape(text), parse_mode


# ─── JARVIS (المحرك الموحّد: LLM7 مجاني → Ollama محلي) ───
# HermesBridge = fallback chain (LLM7 free cloud → Ollama local)
# JarvisBridge = Ollama فقط (fallback)
try:
    from src.hermes_bridge import HermesBridge
    jarvis = HermesBridge()
except Exception:
    from jarvis_bridge import JarvisBridge
    jarvis = JarvisBridge()
cloud = CloudFallback()
ask_agent = AskAgent()
alerts = SmartAlerts()
analyzer = LogAnalyzer()
auto_apply = AutoApply()
market = MarketWatcher()
digest = DailyDigest()
bandwidth = BandwidthAgent()
pharos = PharosAgent()
evolve = SelfEvolve()

vpn = VPNAgent()
airdrop_agent = AirdropAgent()
# ═══════════════════════════════════════
#  حماية: فقط CHAT_ID المسموح
# ═══════════════════════════════════════
def authorized_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if CHAT_ID and user_id != CHAT_ID:
            await update.message.reply_text(
                f"⛔ غير مصرح لك بالوصول.\nID الخاص بك: `{user_id}`",
                parse_mode="Markdown"
            )
            logger.warning(f"محاولة وصول غير مصرح: {user_id}")
            return
        return await func(update, context)
    return wrapper


# ═══════════════════════════════════════
#  الأوامر
# ═══════════════════════════════════════

@authorized_only
async def cmd_airdrops(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أفضل فرص Airdrop (scored)"""
    from airdrop_scorer import format_telegram, top_candidates
    text = format_telegram(limit=5)
    cands = top_candidates(limit=5, min_grade="B")
    if cands:
        a = sum(1 for c in cands if c["grade"] == "A")
        b = sum(1 for c in cands if c["grade"] == "B")
        text += f"\n\n📊 المؤهلة: 🟢 A=`{a}` · 🔵 B=`{b}`"
    await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)


@authorized_only
async def cmd_airdrop_sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """جلب الإيردروبات فوراً"""
    msg = await update.message.reply_text("📡 جارٍ جلب الإيردروبات...")
    try:
        items = airdrop_agent.fetch_all()
        new = airdrop_agent.save_airdrops(items)
        total = airdrop_agent.count()
        await msg.edit_text(
            f"✅ *تم التحديث*\n\n"
            f"📥 جُلب: `{len(items)}`\n"
            f"🆕 جديد: `{new}`\n"
            f"📊 الإجمالي: `{total}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Voice — /voice say <text> or /voice status"""
    import asyncio
    from voice_agent import speak_telegram, format_telegram
    args = context.args or []
    action = args[0].lower() if args else "status"

    if action == "status" or not args:
        await update.message.reply_text(format_telegram(), parse_mode="Markdown")
        return

    if action == "say":
        text = " ".join(args[1:])
        if not text:
            await update.message.reply_text("مثال: /voice say السلام عليكم")
            return
        msg = await update.message.reply_text("🎙️ جارٍ التحويل إلى صوت...")
        try:
            voice = "ar-EG-SalmaNeural" if any("\u0600" <= c <= "\u06FF" for c in text) else "en-US-JennyNeural"
            path = await asyncio.to_thread(speak_telegram, text, voice)
            if path:
                with open(path, "rb") as audio:
                    await msg.edit_text("🎙️")
                    await update.message.reply_voice(audio)
                os.unlink(path)
            else:
                await msg.edit_text("❌ TTS مش متاح — pip install edge-tts")
        except Exception as e:
            await msg.edit_text(f"❌ خطأ: {e}")
        return

    await update.message.reply_text("الأوامر: /voice say <text> · /voice status")


@authorized_only
async def cmd_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vector memory — ذاكرة دلالية"""
    from pathlib import Path
    args = context.args or []
    action = args[0].lower() if args else "recent"
    BASE = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(BASE / "src"))

    try:
        from vector_memory_agent import VectorMemory
        vm = VectorMemory()

        if action == "stats":
            st = vm.stats()
            by_kind = st.get("by_kind", {})
            kinds = " · ".join(f"{k}={v}" for k, v in by_kind.items()) or "—"
            await update.message.reply_text(
                f"🧠 *الذاكرة الدلالية*\n\n"
                f"إجمالي: `{st['total']}` ذكرى\n"
                f"الحجم: `{st['db_size_kb']}` KB\n"
                f"الأنواع: {kinds}",
                parse_mode="Markdown"
            )
        else:
            query = " ".join(args) if args and action not in ("recent", "stats") else None
            if query:
                text = vm.format_telegram(query=query, limit=5)
            else:
                text = vm.format_telegram(limit=8)
            await update.message.reply_text(text, parse_mode="Markdown")
        vm.close()
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_veille(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Veille 24/7 — GitHub harvest (25 categories)"""
    from pathlib import Path
    from veille_agent import format_telegram
    args = context.args or []
    action = args[0].lower() if args else "top"

    BASE = Path(__file__).resolve().parent.parent

    if action == "run":
        msg = await update.message.reply_text("📡 جارٍ الحصاد (قد يأخذ دقائق)...")
        try:
            sys.path.insert(0, str(BASE / "src"))
            import veille_agent
            index = veille_agent.harvest(per_query=20, target="esprieaether")
            total = sum(len(v) for v in index.values())
            payload = veille_agent.save_index(index)
            await msg.edit_text(
                f"✅ *حصاد كامل*\n\n"
                f"📡 حُصد: `{total}` repo\n"
                f"📚 الفهرس: `{payload['total']}` repo\n"
                f"🗂️ الفئات: `{len(payload['categories'])}`",
                parse_mode="Markdown"
            )
        except Exception as e:
            await msg.edit_text(f"❌ خطأ: {e}")

    else:  # top
        text = format_telegram(top=8)
        await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)


@authorized_only
async def cmd_cloudnode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """GitHub Cloud Node — التحكم من التيليفون عبر Issues"""
    import urllib.request
    import json as _json
    from pathlib import Path
    args = context.args or []
    action = args[0].lower() if args else "status"

    BASE = Path(__file__).resolve().parent.parent

    if action == "poll":
        msg = await update.message.reply_text("☁️ جارٍ سحب أوامر السحابة...")
        try:
            sys.path.insert(0, str(BASE))
            import cloud_poller
            rep = cloud_poller.poll_once()
            n = len(rep.get("executed", []))
            lines = [
                "☁️ *جسر السحابة*\n",
                f"📥 سحب: {'✅' if rep.get('pull') else '❌'}",
                f"⚡ أوامر منفذة: `{n}`",
                f"📤 رفع: {'✅' if rep.get('pushed') else '❌'}",
            ]
            for e in rep.get("executed", []):
                lines.append(f"\n`{e['command']}`: {e['status']}")
            await msg.edit_text("\n".join(lines), parse_mode="Markdown")
        except Exception as e:
            await msg.edit_text(f"❌ خطأ: {e}")

    elif action == "url":
        await update.message.reply_text(
            "📱 *التحكم من التيليفون*\n\n"
            "صوّب issue جديدة هنا:\n"
            "https://github.com/007aether/esprieaether/issues/new\n\n"
            "الأوامر: `mesh cycle` · `scan` · `status` · `board`",
            parse_mode="Markdown", disable_web_page_preview=True
        )

    else:  # status
        try:
            status_file = BASE / "data" / "cloud_status.json"
            if status_file.exists():
                st = _json.loads(status_file.read_text(encoding="utf-8"))
                pc_seen = st.get("pc_last_seen", "?")[:19]
                cloud_seen = st.get("cloud_last_run", "?")[:19]
                scan_n = st.get("last_scan_count", 0)
                await update.message.reply_text(
                    f"☁️ *GitHub Cloud Node*\n\n"
                    f"🖥️ آخر ظهور للـ PC: `{pc_seen}`\n"
                    f"☁️ آخر دورة سحابية: `{cloud_seen}`\n"
                    f"📡 آخر فحص: `{scan_n}` عنصر\n\n"
                    f"/cloud poll — سحب الأوامر الآن\n"
                    f"/cloud url — رابط التحكم من التيليفون",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    "☁️ ما كاين حتى cloud status بعد.\n"
                    "صوّب issue فـ GitHub باش تبدأ الدورة السحابية."
                )
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_mesh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Agent Mesh — وكيل الوكلاء كيتواصلو مع بعض"""
    import urllib.request
    import json as _json
    args = context.args or []
    action = args[0].lower() if args else "board"

    if action == "cycle":
        msg = await update.message.reply_text("🕸️ جارٍ تشغيل دورة الوكلاء...")
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:11437/cycle",
                data=_json.dumps({"rounds": 1}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=200) as r:
                mesh = _json.loads(r.read())
            lines = [f"✅ *دورة كاملة* — {mesh.get('agents_thought', 0)} وكيل خدّمو\n"]
            for res in mesh.get("results", []):
                icon = "✅" if res["ok"] else "❌"
                lines.append(f"{icon} `{res['agent']}` — {res['text'][:70]}")
            lines.append(f"\n📋 الرسائل: {mesh.get('board_total', 0)}")
            await msg.edit_text("\n".join(lines), parse_mode="Markdown")
        except Exception as e:
            await msg.edit_text(f"❌ خطأ: {e}")

    elif action == "tasks":
        try:
            with urllib.request.urlopen("http://127.0.0.1:11437/tasks", timeout=10) as r:
                tasks = _json.loads(r.read()).get("tasks", [])
            if not tasks:
                await update.message.reply_text("📭 ما كاين حتى مهمة مقترحة")
                return
            lines = ["📋 *مهام مقترحة من الوكلاء:*\n"]
            for t in tasks[-10:]:
                lines.append(f"• `{t['agent']}`: {t['title'][:70]}")
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")

    else:  # board (default)
        try:
            with urllib.request.urlopen("http://127.0.0.1:11437/board?limit=8", timeout=10) as r:
                board = _json.loads(r.read())
            msgs = board.get("messages", [])
            if not msgs:
                await update.message.reply_text("📭 اللوحة فارغة. صيف `/mesh cycle` باش يبداو الوكلاء")
                return
            lines = ["🕸️ *لوحة الوكلاء* (آخر الرسائل):\n"]
            for m in msgs[-8:]:
                lines.append(f"`{m['agent']}`: {m['text'][:90]}")
            lines.append(f"\n📊 الإجمالي: {board.get('total', 0)} رسالة")
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_pharos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حالة Pharos Testnet"""
    args = context.args or []
    action = args[0].lower() if args else "status"

    if action == "claim":
        msg = await update.message.reply_text("🔷 جارٍ ادعاء Faucet...")
        result = pharos.claim_faucet()
        if result["status"] == "ok":
            await msg.edit_text("✅ تم ادعاء 0.01 PHRS!")
        elif result["status"] == "cooldown":
            await msg.edit_text("⏳ " + result["message"])
        else:
            await msg.edit_text(
                "⚠️ يحتاج المتصفح" + chr(10) + chr(10) +
                "افتح: https://testnet.pharosnetwork.xyz",
                disable_web_page_preview=True
            )
        return

    text = pharos.format_telegram()
    await update.message.reply_text(text, parse_mode="Markdown")



@authorized_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة الترحيب"""
    text = (
        "⚡ *ESPRIEAETHER COMMAND CENTER*" + chr(10) + chr(10) +
        "مرحباً! أنا JARVIS." + chr(10) + chr(10) +
        "*الأوامر:*" + chr(10) +
        "/ask — مساعد ذكي" + chr(10) +
        "/airdrop — الإيردروبات" + chr(10) +
        "/pharos — Pharos Testnet" + chr(10) +
        "/bandwidth — مشاركة الإنترنت" + chr(10) +
        "/market — أسعار السوق" + chr(10) +
        "/digest — التقرير اليومي" + chr(10) +
        "/services — حالة الخدمات" + chr(10) +
        "/vpn — حالة VPN" + chr(10) +
        "/report — تقرير" + chr(10) +
        "/status — حالة النظام" + chr(10) +
        "/jarvis — محادثة" + chr(10) +
        "/hermes — محرك Hermes (محلي/سحابي)" + chr(10) +
        "/help — مساعدة"
    )
    # اهرّب _ حتى ما يرفضش Telegram (مثل "الإيردروبات" فيها _)
    text = text.replace("_", "\\_")
    await update.message.reply_text(text, parse_mode="Markdown")

@authorized_only
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)


@authorized_only
async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong! النظام يعمل.")


@authorized_only
async def cmd_jarvis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """محادثة مع JARVIS"""
    prompt = " ".join(context.args) if context.args else ""

    if not prompt:
        await update.message.reply_text(
            "🤖 اكتب سؤالك بعد الأمر:\nمثال: `/jarvis ما هي أفضل طريقة لتأمين محفظة؟`",
            parse_mode="Markdown"
        )
        return

    msg = await update.message.reply_text("🤖 JARVIS يفكر...")

    try:
        answer = jarvis.ask(prompt)
        # تنسيق الرد
        response = f"🤖 *JARVIS:*\n\n{md_escape(answer)}"
        # إذا كان الرد طويلاً، قسّمه
        if len(response) > 4000:
            parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
            await msg.edit_text(parts[0])
            for part in parts[1:]:
                await update.message.reply_text(part)
        else:
            await msg.edit_text(response, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"⚠️ خطأ: {e}")


@authorized_only
async def cmd_hermes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """محادثة مع محرك Hermes (Ollama محلي، أو endpoint خارجي إن وُجد)"""
    prompt = " ".join(context.args) if context.args else ""

    if not prompt:
        await update.message.reply_text(
            "⚡ اكتب سؤالك بعد الأمر:\nمثال: `/hermes كيف أحسّن أمان السيرفر؟`",
            parse_mode="Markdown"
        )
        return

    msg = await update.message.reply_text("⚡ Hermes يفكر...")

    try:
        from src.hermes_bridge import HermesBridge
        bridge = HermesBridge()
        answer = bridge.ask(prompt)
        engine = bridge.status().get("active_engine", "?")
        engine_label = {"llm7": "☁️ LLM7 (مجاني)", "ollama": "🖥️ محلي", "hermes": "☁️ Hermes"}.get(engine, engine)
        response = f"⚡ *HERMES* ({engine_label}):\n\n{md_escape(answer)}"
        if len(response) > 4000:
            parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
            await msg.edit_text(parts[0])
            for part in parts[1:]:
                await update.message.reply_text(part)
        else:
            await msg.edit_text(response, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"⚠️ خطأ: {e}")


@authorized_only
async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مسح سجل JARVIS"""
    jarvis.clear_history()
    await update.message.reply_text("✅ تم مسح سجل المحادثة.")


@authorized_only
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حالة النظام الكاملة"""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # حالة المحرك (universal: HermesBridge أو JarvisBridge)
        try:
            st = jarvis.status()
            engine = st.get("active_engine", "?")
            engine_label = {"llm7": "☁️ LLM7 (مجاني)", "ollama": "🖥️ محلي", "hermes": "☁️ Hermes"}.get(engine, engine)
            model = st.get("model", "—")
        except Exception:
            engine_label = "🖥️ Ollama"
            model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

        text = f"""
📊 *حالة ESPRIEAETHER*

*المعالج*
• الاستخدام: `{cpu}%`
• الأنوية: `{psutil.cpu_count()}`

*الذاكرة*
• الاستخدام: `{mem.percent}%`
• متاح: `{round(mem.available/(1024**3), 2)} GB` / `{round(mem.total/(1024**3), 2)} GB`

*القرص*
• الاستخدام: `{disk.percent}%`
• متاح: `{round(disk.free/(1024**3), 2)} GB`

*المحرك*
• النشط: {engine_label}
• الموديل: `{model}`

*الهوية*: `{AETHER_ID}`
*الوقت*: `{datetime.now().strftime('%H:%M:%S')}`
"""
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ خطأ: {e}")


@authorized_only
async def cmd_metrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_status(update, context)


@authorized_only
async def cmd_web(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رابط لوحة التحكم"""
    host = os.getenv("WEB_HOST", "127.0.0.1")
    port = os.getenv("WEB_PORT", "5000")
    text = f"""
🌐 *JARVIS Command Center*

• محلي: `http://{host}:{port}`
• من الشبكة: `http://192.168.1.15:{port}`

_افتح الرابط في متصفح الحاسوب_
"""
    await update.message.reply_text(text, parse_mode="Markdown")


@authorized_only
async def cmd_ollama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حالة المحرك (LLM7 / Ollama)"""
    st = jarvis.status()
    engine = st.get("active_engine", "?")
    engine_label = {"llm7": "☁️ LLM7 (مجاني)", "ollama": "🖥️ محلي", "hermes": "☁️ Hermes"}.get(engine, engine)
    text = (
        f"🤖 *حالة المحرك*\n\n"
        f"• المحرك النشط: {engine_label}\n"
        f"• الموديل: `{st.get('model', '—')}`\n"
        f"• Ollama محلي: {'🟢' if st.get('ollama_available') else '🔴'}\n"
        f"• LLM7 سحابي: {'🟢' if st.get('remote', {}).get('status') == 'online' else '🔴'}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


@authorized_only
async def cmd_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معلومات المحفظة"""
    try:
        wallet_file = BASE_DIR / "test_wallets.json"
        if not wallet_file.exists():
            await update.message.reply_text("⚠️ لا توجد محفظة مسجلة.")
            return

        with open(wallet_file) as f:
            wallets = json.load(f)

        text = "💰 *المحافظ*\n\n"
        for i, w in enumerate(wallets, 1):
            text += f"*{i}.* `{w['address']}`\n"

        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ خطأ: {e}")


@authorized_only
async def cmd_vpn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التحكم بـ VPN"""
    # Windows: wireguard/sudo ماشي متوفر — رسالة واضحة
    if os.name == "nt":
        await update.message.reply_text(
            "⚠️ *VPN غير مدعوم على Windows*\n\n"
            "التحكم بـ VPN (wireguard + sudo) متوفر على Linux فقط.\n"
            "على Windows، استخدم تطبيق WireGuard مباشرة.",
            parse_mode="Markdown"
        )
        return

    args = context.args or []
    action = args[0].lower() if args else "status"

    if action == "on":
        msg = await update.message.reply_text("🔌 جارٍ تشغيل VPN...")
        result = vpn.connect()
        if result["status"] in ("connected", "already_active"):
            text = vpn.format_telegram()
            await msg.edit_text(f"✅ *تم التشغيل*\n\n{text}", parse_mode="Markdown")
        else:
            await msg.edit_text(f"❌ فشل: {result.get('message', 'خطأ')}")

    elif action == "off":
        msg = await update.message.reply_text("🔌 جارٍ إيقاف VPN...")
        result = vpn.disconnect()
        if result["status"] in ("disconnected", "already_down"):
            await msg.edit_text("✅ *تم إيقاف VPN*", parse_mode="Markdown")
        else:
            await msg.edit_text(f"❌ فشل: {result.get('message', 'خطأ')}")

    elif action == "restart":
        msg = await update.message.reply_text("🔄 جارٍ إعادة التشغيل...")
        result = vpn.restart()
        if result["status"] == "connected":
            text = vpn.format_telegram()
            await msg.edit_text(f"✅ *تم إعادة التشغيل*\n\n{text}", parse_mode="Markdown")
        else:
            await msg.edit_text(f"❌ فشل: {result.get('message', 'خطأ')}")

    elif action == "ip":
        ip4 = vpn.get_ip(ipv4=True)
        ip6 = vpn.get_ip(ipv4=False)
        await update.message.reply_text(
            f"🌍 *IP الحالي*\n\n"
            f"IPv4: `{ip4}`\n"
            f"IPv6: `{ip6}`",
            parse_mode="Markdown"
        )

    else:  # status
        text = vpn.format_telegram()
        await update.message.reply_text(text, parse_mode="Markdown")


@authorized_only
async def cmd_vpn_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مساعد VPN"""
    text = """
🔐 *أوامر VPN*

• `/vpn` — عرض الحالة
• `/vpn status` — الحالة الكاملة
• `/vpn on` — تشغيل VPN
• `/vpn off` — إيقاف VPN
• `/vpn restart` — إعادة تشغيل
• `/vpn ip` — عرض IP الحالي
"""
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_airdrop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حالة الأيردروب"""
    try:
        from airdrop_agent import AirdropAgent
        agent = AirdropAgent()
        total = agent.count()
        recent = agent.get_recent(5)

        text = "📡 *حالة الأيردروب*" + chr(10) + chr(10)
        text += f"📊 الإجمالي: `{total}`" + chr(10) + chr(10)
        text += "*أحدث 5:*" + chr(10)

        for i, item in enumerate(recent, 1):
            title = item["title"][:60]
            text += f"{i}. {title}" + chr(10)
            text += f"   [رابط]({item['link']})" + chr(10)

        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")



@authorized_only
async def cmd_robots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إحصائيات الروبوتات (محرك حقيقي)"""
    msg = await update.message.reply_text("🤖 جارٍ الفحص...")
    try:
        from robots.robot_engine import RobotEngine
        eng = RobotEngine()
        st = eng.get_stats()
        by_status = st.get("robots_by_status", {})
        results = st.get("results_by_status", {})
        text = (
            "🤖 *محرك الروبوتات*\n\n"
            f"• الدورات: `{st.get('cycles', 0)}`\n"
            f"• Robots نشطة: `{by_status.get('active', 0)}`\n"
            f"• Robots idle: `{by_status.get('idle', 0)}`\n\n"
            f"✅ نتائج ناجحة: `{results.get('ok', 0)}`\n"
            f"❌ أخطاء: `{results.get('error', 0)}`\n"
        )
        await msg.edit_text(text, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_robots_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تشغيل دورة روبوتات فوراً"""
    msg = await update.message.reply_text("⚙️ جارٍ تشغيل الروبوتات...")
    try:
        from robots.robot_engine import RobotEngine
        eng = RobotEngine()
        system = context.args[0] if context.args else None
        r = eng.run_once(system=system)
        text = (
            f"✅ *دورة #{r['cycle']}* تمّت\n\n"
            f"• المجموع: `{r['total']}`\n"
            f"• ناجح: `{r['ok']}`\n"
            f"• خطأ: `{r['error']}`"
        )
        await msg.edit_text(text, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مزامنة GitHub فورية (git CLI)"""
    msg = await update.message.reply_text("🔄 جارٍ المزامنة مع GitHub...")
    try:
        from github_agent import GitHubAgent
        agent = GitHubAgent()

        # تحقق أن git CLI شغال (remote موجود)
        if not agent.git_status().get("remote"):
            await msg.edit_text("⚠️ GitHub غير متصل (git remote ناقص)")
            return

        # git CLI كيدير add -A (المشروع كامل) — أحسن من لستة ملفات
        result = agent.push_files(message="⚡ Manual sync from Telegram")

        if result.get("status") == "ok":
            if result.get("sha"):
                await msg.edit_text(
                    f"✅ *تمت المزامنة*\n\n"
                    f"📦 Commit: `{result.get('sha')}`\n"
                    f"🔗 [عرض الـ Commit]({result.get('url')})",
                    parse_mode="Markdown"
                )
            else:
                await msg.edit_text("✅ " + result.get("message", "تمت"))
        else:
            await msg.edit_text(f"⚠️ فشل: {result.get('message')}")
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إحصائيات شاملة"""
    msg = await update.message.reply_text("📊 جارٍ الفحص...")
    try:
        import requests
        r = requests.get("http://127.0.0.1:5000/api/stats/full", timeout=10)
        d = r.json()

        if d.get("status") != "ok":
            await msg.edit_text("❌ فشل")
            return

        s = d.get("system", {})
        a = d.get("airdrops", {})
        g = d.get("github", {})
        v = d.get("vpn", {})
        ag = d.get("agents", {})

        text = f"""
📊 *ESPRIEAETHER — إحصائيات*

💻 *النظام*
• CPU: `{s.get('cpu', '—')}%`
• RAM: `{s.get('ram', '—')}%`
• Disk: `{s.get('disk', '—')}%`

📡 *الإيردروبات*: `{a.get('total', 0)}`

🔄 *GitHub*: `{g.get('status', '—')}`
🔐 *VPN*: `{'🟢' if v.get('active') else '🔴'} {v.get('ip', '—')}`

🤖 *Autonomous*
• الدورات: `{ag.get('cycles', 0)}`
• المهام: `{ag.get('tasks_count', 0)}`
"""
        await msg.edit_text(text, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_somnia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حالة Somnia"""
    msg = await update.message.reply_text("🔍 جارٍ فحص Somnia...")
    try:
        import json
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider("https://dream-rpc.somnia.network"))
        wallet_file = BASE_DIR / "test_wallets.json"

        if not wallet_file.exists():
            await msg.edit_text("⚠️ لا توجد محفظة")
            return

        wallet = json.loads(wallet_file.read_text())[0]
        address = wallet["address"]
        balance = w3.from_wei(w3.eth.get_balance(address), "ether")

        text = f"""
💰 *محفظة Somnia Shannon*

📍 العنوان:
`{address}`

💵 الرصيد: `{balance} STT`
🔗 متصل: `{w3.is_connected()}`
📦 آخر بلوك: `{w3.eth.block_number}`

🔍 [عرض في المستكشف](https://shannon-explorer.somnia.network/address/{address})
"""
        await msg.edit_text(text, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_evolve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اقتراحات التطوير الذاتي"""
    msg = await update.message.reply_text("🧠 جارٍ التحليل...")
    try:
        suggestions = evolve.suggest_improvements()
        if not suggestions:
            await msg.edit_text("📭 لا توجد اقتراحات")
            return

        text = evolve.format_suggestions(limit=3)
        await msg.edit_text(text, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الموافقة على اقتراح"""
    if not context.args:
        await update.message.reply_text("استخدم: /approve <id>")
        return

    sid = context.args[0].strip()

    # ابحث عن تطابقات
    matches = [s for s in evolve.suggestions if s["id"].endswith(sid)]

    if not matches:
        await update.message.reply_text("لم أجد اقتراحاً بـ " + sid)
        return

    if len(matches) > 1:
        text = str(len(matches)) + " اقتراحات متطابقة:" + chr(10) + chr(10)
        for m in matches[:5]:
            text += "- " + m["id"] + chr(10)
        text += chr(10) + "استخدم ID أطول"
        await update.message.reply_text(text)
        return

    msg = await update.message.reply_text("جارٍ التنفيذ...")
    try:
        result = evolve.approve(sid)
        if result["status"] == "ok":
            await msg.edit_text("تم" + chr(10) + chr(10) + result["message"])
        else:
            await msg.edit_text("فشل: " + result["message"])
    except Exception as e:
        await msg.edit_text("خطأ: " + str(e))



@authorized_only
async def cmd_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رفض اقتراح"""
    if not context.args:
        await update.message.reply_text("⚠️ `/reject <id>`", parse_mode="Markdown")
        return

    result = evolve.reject(context.args[0])
    await update.message.reply_text(f"✅ {result['message']}")


@authorized_only
async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنفيذ أمر ذكي بالعربية"""
    if not context.args:
        await update.message.reply_text(
            "⚡ *الأوامر المدعومة:*\n\n"
            "• `/run أرسل التقرير`\n"
            "• `/run افحص المنافذ`\n"
            "• `/run حالة VPN`\n"
            "• `/run زامن GitHub`\n"
            "• `/run اعرض الإيردروبات`\n"
            "• `/run حالة الخدمات`\n"
            "• `/run إحصائيات النظام`\n"
            "• `/run أعد تشغيل core`\n"
            "• `/run اعرض السجلات`\n"
            "• `/run اعرض المهام`\n"
            "• `/run اعرض الـ IP`\n"
            "• `/run فحص الحرارة`\n"
            "• `/run خذ نسخة احتياطية`\n"
            "• `/run اعرض المساحة`\n"
            "• `/run نظف السجلات`\n"
            "• `/run أعد تشغيل البوت`\n"
            "• `/run أوقف VPN`\n",
            parse_mode="Markdown"
        )
        return

    text = " ".join(context.args)
    msg = await update.message.reply_text(f"⚙️ *جارٍ التنفيذ:*\n`{text}`", parse_mode="Markdown")

    # توجيه الأمر
    route = router.route(text)

    if route["status"] != "ok":
        await msg.edit_text(
            f"❌ لم أفهم الأمر: `{text}`\n\n"
            f"_استخدم `/run` لعرض الأوامر المدعومة_",
            parse_mode="Markdown"
        )
        return

    action = route["action"]
    source = route["source"]

    # تنفيذ
    result = executor.execute(action)

    # تنسيق النتيجة
    if result.get("status") == "ok":
        output = format_run_result(action, result)
        await msg.edit_text(
            f"✅ *تم التنفيذ* ({source})\n\n{output}",
            parse_mode="Markdown"
        )
    else:
        await msg.edit_text(
            f"⚠️ *فشل التنفيذ*\n\n"
            f"الأمر: `{action}`\n"
            f"الخطأ: `{result.get('message', 'غير معروف')}`",
            parse_mode="Markdown"
        )


def format_run_result(action: str, result: dict) -> str:
    """تنسيق نتيجة التنفيذ"""
    if action == "send_report":
        return f"📧 {result.get('message', 'تم')}"

    if action == "scan_ports":
        ports = result.get("ports", [])[:5]
        return f"🔍 *المنافذ* ({result.get('count', 0)})\n" + "\n".join(f"• `{p}`" for p in ports)

    if action == "get_vpn_status":
        emoji = "🟢" if result.get("active") else "🔴"
        return f"{emoji} *VPN*: `{result.get('ip', '—')}`"

    if action == "sync_github":
        return f"🔄 GitHub: `{result.get('sha', '—')}`"

    if action == "get_airdrops":
        recent = result.get("recent", [])[:3]
        text = f"📡 *الإيردروبات* ({result.get('total', 0)})\n"
        for item in recent:
            text += f"• {item['title'][:50]}\n"
        return text

    if action == "get_services":
        svcs = result.get("services", {})
        text = "⚙️ *الخدمات*\n"
        for name, status in svcs.items():
            emoji = "🟢" if status == "active" else "🔴"
            text += f"{emoji} `{name}`\n"
        return text

    if action == "get_stats":
        return (
            f"📊 *الإحصائيات*\n"
            f"• CPU: `{result.get('cpu', '—')}%`\n"
            f"• RAM: `{result.get('ram', '—')}%`\n"
            f"• Disk: `{result.get('disk', '—')}%`"
        )

    if action == "count_airdrops":
        return f"📡 *العدد*: `{result.get('count', 0)}` إيردروب"

    if action == "get_jarvis_status":
        emoji = "🟢" if result.get("jarvis") == "online" else "🔴"
        return f"{emoji} *JARVIS*: `{result.get('jarvis', '—')}`"

    if action == "restart_core":
        return "♻️ *تم إعادة التشغيل*"

    return f"✅ {result}"


@authorized_only
async def cmd_bandwidth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حالة مشاركة الإنترنت"""
    try:
        text = bandwidth.format_telegram()
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("❌ خطأ: " + str(e))

@authorized_only
async def cmd_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أسعار السوق"""
    msg = await update.message.reply_text("📊 جارٍ جلب الأسعار...")

    try:
        market.fetch_prices()
        text = market.format_telegram()
        await msg.edit_text(text, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text("❌ خطأ: " + str(e))

@authorized_only
async def cmd_auto_apply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تطبيق اقتراح تلقائياً"""
    if not context.args:
        text = auto_apply.format_telegram()
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    sid = context.args[0].strip()
    msg = await update.message.reply_text("🤖 جارٍ التطبيق...")

    try:
        result = auto_apply.apply(sid)

        if result["status"] == "ok":
            await msg.edit_text(
                "✅ *تم التطبيق بنجاح*" + chr(10) + chr(10) +
                "📁 `" + result["file"] + "`" + chr(10) +
                "📊 " + str(result["old_size"]) + " → " + str(result["new_size"]) + " حرف",
                parse_mode="Markdown"
            )
        else:
            await msg.edit_text(
                "❌ " + result.get("message", result["status"]),
                parse_mode="Markdown"
            )
    except Exception as e:
        await msg.edit_text("❌ خطأ: " + str(e))

@authorized_only
async def cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تحليل السجلات عبر Cloud"""
    msg = await update.message.reply_text("📊 جارٍ التحليل...")

    try:
        result = analyzer.analyze()

        if result["status"] == "ok":
            text = analyzer.format_telegram()
            await msg.edit_text(text, parse_mode="Markdown")
        elif result["status"] == "local_only":
            s = result["stats"]
            text = "📊 *تحليل محلي*" + chr(10) + chr(10)
            text += f"• إجمالي: `{s['total']}`" + chr(10)
            text += f"• أخطاء: `{s['errors']}`" + chr(10) + chr(10)
            text += "_Cloud فشل — استخدم /cloud test_"
            await msg.edit_text(text, parse_mode="Markdown")
        else:
            await msg.edit_text("📭 لا توجد سجلات للتحليل")
    except Exception as e:
        await msg.edit_text("❌ خطأ: " + str(e))

@authorized_only
async def cmd_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنبيهات ذكية"""
    try:
        text = alerts.format_telegram()
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("❌ خطأ: " + str(e))

@authorized_only
async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مساعد ذكي شامل"""
    if not context.args:
        await update.message.reply_text(
            "🤖 *Ask Agent*" + chr(10) + chr(10) +
            "*أمثلة:*" + chr(10) +
            "• `/ask كم إيردروب؟`" + chr(10) +
            "• `/ask حالة VPN`" + chr(10) +
            "• `/ask إحصائيات النظام`" + chr(10) +
            "• `/ask حالة الخدمات`" + chr(10) +
            "• `/ask رصيد Somnia`" + chr(10) +
            "• `/ask اقتراحات التطوير`" + chr(10) +
            "• `/ask خذ نسخة احتياطية`",
            parse_mode="Markdown"
        )
        return

    question = " ".join(context.args)
    msg = await update.message.reply_text("🤔 جارٍ التحليل...")

    try:
        result = ask_agent.ask(question)
        await msg.edit_text(md_escape(result["answer"]), parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        await msg.edit_text("❌ خطأ: " + str(e))

@authorized_only
async def cmd_cloud(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة Cloud Fallback"""
    import concurrent.futures

    args = context.args or []
    action = args[0].lower() if args else "status"

    if action == "test":
        await update.message.reply_text(
            "☁️ جارٍ اختبار Cloud..."
        )
        try:
            loop = __import__('asyncio').get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = await loop.run_in_executor(pool, lambda: cloud.ask("قل: مرحبا", None, "cloud"))
            if result["status"] == "ok":
                await update.message.reply_text(
                    "✅ Cloud يعمل" + chr(10) + "📡 المصدر: " + result["source"] + chr(10) + "💬 الرد: " + result["answer"][:150]
                )
            else:
                await update.message.reply_text(
                    "❌ فشل Cloud: " + result.get("message", "unknown")[:200]
                )
        except Exception as e:
            await update.message.reply_text("❌ خطأ: " + str(e)[:200])

    elif action == "local":
        await update.message.reply_text(
            "🏠 جارٍ اختبار Local..."
        )
        try:
            loop = __import__('asyncio').get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = await loop.run_in_executor(pool, lambda: cloud.ask("قل: مرحبا", None, "local"))
            if result["status"] == "ok":
                await update.message.reply_text(
                    "✅ Local يعمل" + chr(10) + "📡 المصدر: " + result["source"] + chr(10) + "💬 الرد: " + result["answer"][:150]
                )
            else:
                await update.message.reply_text(
                    "❌ فشل Local: " + result.get("message", "unknown")[:200]
                )
        except Exception as e:
            await update.message.reply_text("❌ خطأ: " + str(e)[:200])

    else:  # status
        text = cloud.format_telegram()
        await update.message.reply_text(text)



@authorized_only
async def cmd_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حالة الخدمات (Windows + Linux)"""
    text = "⚙️ *حالة الخدمات*\n\n"
    # Windows: services via tasklist / sc query
    # Linux: systemctl is-active
    is_windows = os.name == "nt"

    services = ["aether-web", "aether-bot", "aether-core", "ollama"]
    for svc in services:
        try:
            if is_windows:
                # Windows: sc query
                r = subprocess.run(
                    ["sc", "query", svc],
                    capture_output=True, text=True, timeout=5
                )
                out = (r.stdout or "").lower()
                if "running" in out:
                    status = "active"
                elif "failed" in out or "does not exist" in out:
                    status = "not found"
                else:
                    status = "stopped"
            else:
                r = subprocess.run(
                    ["systemctl", "is-active", svc],
                    capture_output=True, text=True, timeout=5
                )
                status = r.stdout.strip() or "unknown"

            emoji = "🟢" if status == "active" else "🔴"
            text += f"{emoji} `{svc}`: {status}\n"
        except Exception:
            text += f"⚠️ `{svc}`: unknown\n"

    # Ollama دايماً: ping مباشر (كيدوز على systemctl)
    try:
        import requests
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
        if r.status_code == 200:
            models = r.json().get("models", [])
            text += f"🟢 `ollama` (ping): {len(models)} models\n"
        else:
            text += "🔴 `ollama` (ping): error\n"
    except Exception:
        text += "🔴 `ollama` (ping): offline\n"

    await update.message.reply_text(text, parse_mode="Markdown")


@authorized_only
async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تقرير فوري"""
    msg = await update.message.reply_text("📊 جارٍ إنشاء التقرير...")
    try:
        import json
        from datetime import datetime

        state_file = BASE_DIR / "autonomous_state.json"
        state = json.loads(state_file.read_text()) if state_file.exists() else {}

        last_runs = state.get("last_run", {})
        text = f"""
📊 *تقرير EsprieAether*

🔄 الدورات: `{state.get('cycles', 0)}`
⏰ البداية: `{state.get('started_at', '—')[:19]}`

*آخر فحوصات:*
• Health: `{last_runs.get('health_check', '—')[:19]}`
• Security: `{last_runs.get('security_scan', '—')[:19]}`
• GitHub: `{last_runs.get('github_sync', '—')[:19]}`
• Somnia: `{last_runs.get('somnia_check', '—')[:19]}`
"""
        await msg.edit_text(text, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {e}")

@authorized_only
async def cmd_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنفيذ أمر shell — بحذر"""
    # حماية: بلا CHAT_ID مضبوط، ما نسمحوش بـ /cmd (أي واحد يقدر يتحكم)
    if not CHAT_ID:
        await update.message.reply_text(
            "⛔ /cmd معطّل: ضيّق TELEGRAM_CHAT_ID ف .env أولاً (أمان)."
        )
        logger.warning("cmd blocked: CHAT_ID not set")
        return
    if not context.args:
        await update.message.reply_text("⚠️ اكتب الأمر:\n`/cmd ls -la`", parse_mode="Markdown")
        return

    cmd = " ".join(context.args)

    # قائمة أوامر محظورة
    forbidden = ["rm -rf /", "mkfs", "dd if=", ":(){:|:&};:", "> /dev/sda"]
    if any(f in cmd for f in forbidden):
        await update.message.reply_text("⛔ أمر محظور لأسباب أمنية.")
        return

    await update.message.reply_text(f"⚙️ تنفيذ:\n`{cmd}`", parse_mode="Markdown")

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30,
            cwd=str(BASE_DIR)
        )
        output = result.stdout + result.stderr
        if not output.strip():
            output = "(لا يوجد مخرجات)"

        if len(output) > 3500:
            output = output[:3500] + "\n\n... (تم قص الباقي)"

        await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")
    except subprocess.TimeoutExpired:
        await update.message.reply_text("⏱️ انتهت المهلة (30 ثانية).")
    except Exception as e:
        await update.message.reply_text(f"⚠️ خطأ: {e}")


@authorized_only
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أي رسالة عادية → تُرسل لـ JARVIS"""
    text = update.message.text
    if not text:
        return

    msg = await update.message.reply_text("🤖 JARVIS يفكر...")
    try:
        answer = jarvis.ask(text)
        response = f"🤖 *JARVIS:*\n\n{md_escape(answer)}"
        if len(response) > 4000:
            response = response[:4000] + "\n\n... (تم قص الباقي)"
        await msg.edit_text(response, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"⚠️ خطأ: {e}")


@authorized_only
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Voice note → STT → JARVIS answer"""
    import asyncio
    import tempfile
    from pathlib import Path
    from voice_agent import transcribe

    msg = await update.message.reply_text("🎙️ جارٍ الاستماع...")
    try:
        voice = update.message.voice or update.message.audio
        if not voice:
            await msg.edit_text("❌ ما كاين حتى صوت")
            return

        tg_file = await context.bot.get_file(voice.file_id)
        suffix = ".ogg" if update.message.voice else ".mp3"
        tmp = Path(tempfile.gettempdir()) / f"aether_in_{voice.file_unique_id}{suffix}"
        await tg_file.download_to_drive(str(tmp))

        text, engine = await asyncio.to_thread(transcribe, str(tmp))
        tmp.unlink(missing_ok=True)

        if not text:
            await msg.edit_text("❌ ما فهمتش — (STT محتاج مفتاح Groq أو LLM7)")
            return

        await msg.edit_text(f"🗣️ سمعت: {text}\n\n🤖 جارٍ الرد...")
        answer = jarvis.ask(text)
        response = f"🗣️ *سمعت:* {md_escape(text)}\n\n🤖 *JARVIS:*\n\n{md_escape(answer)}"
        if len(response) > 4000:
            response = response[:4000] + "..."
        await msg.edit_text(response, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"⚠️ خطأ: {e}")


@authorized_only
async def cmd_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📁 file manager — /files [path]"""
    try:
        from src.file_manager import list_dir, read_file, delete_file, write_file
        if not context.args:
            r = list_dir(".")
            items = r.get("items", [])[:20]
            text = "📁 *Files* (root)\n\n"
            for it in items:
                icon = "📁" if it["type"] == "dir" else "📄"
                text += f"{icon} `{it['name']}`\n"
            await update.message.reply_text(text, parse_mode="Markdown")
            return
        sub = context.args[0]
        if sub == "read" and len(context.args) > 1:
            r = read_file(context.args[1])
            text = f"📄 `{context.args[1]}` ({r.get('size',0)}B)\n\n{r.get('content','')}"
        elif sub == "delete" and len(context.args) > 1:
            r = delete_file(context.args[1])
            text = f"🗑️ deleted: `{context.args[1]}`" if r.get("ok") else f"❌ {r.get('error')}"
        else:
            r = list_dir(sub)
            items = r.get("items", [])
            text = f"📁 `{sub}`\n\n"
            for it in items[:30]:
                icon = "📁" if it["type"] == "dir" else "📄"
                text += f"{icon} `{it['name']}`\n"
        await update.message.reply_text(text[:4000], parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📅 calendar/tasks — /task [add|list|done]"""
    try:
        from src.calendar_agent import add_task, list_tasks, complete_task
        if not context.args:
            r = list_tasks()
            tasks = r.get("tasks", [])
            if not tasks:
                await update.message.reply_text("📅 ما كاينش tasks.")
                return
            text = "📅 *Tasks*\n\n"
            for t in tasks[:20]:
                due = f" ⏰{t['due']}" if t.get("due") else ""
                text += f"`{t['id']}` {t['title']}{due}\n"
            await update.message.reply_text(text, parse_mode="Markdown")
            return
        sub = context.args[0]
        if sub == "add" and len(context.args) > 1:
            due = context.args[2] if len(context.args) > 2 else None
            r = add_task(" ".join(context.args[1:2]), due)
            await update.message.reply_text(f"✅ task #{r.get('id')}: {context.args[1]}")
        elif sub == "done" and len(context.args) > 1:
            r = complete_task(int(context.args[1]))
            await update.message.reply_text(f"✅ done: #{context.args[1]}")
        else:
            await update.message.reply_text("⚠️ /task [add|done|list]")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_vault(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔐 password vault — /vault [get|store|list]"""
    try:
        from src.vault_agent import store, retrieve, list_secrets, delete_secret
        if not context.args:
            r = list_secrets()
            names = r.get("names", [])
            text = "🔐 *Vault*\n\n" + ("\n".join(f"• `{n}`" for n in names) if names else "فارغ")
            await update.message.reply_text(text, parse_mode="Markdown")
            return
        sub = context.args[0]
        if sub == "store" and len(context.args) > 2:
            r = store(context.args[1], context.args[2])
            await update.message.reply_text(f"✅ stored: `{context.args[1]}`")
        elif sub == "get" and len(context.args) > 1:
            r = retrieve(context.args[1])
            if r.get("ok"):
                await update.message.reply_text(f"🔐 `{r['name']}`:\n`{r['value']}`", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"❌ {r.get('error')}")
        elif sub == "delete" and len(context.args) > 1:
            r = delete_secret(context.args[1])
            await update.message.reply_text(f"🗑️ deleted: `{context.args[1]}`")
        else:
            await update.message.reply_text("⚠️ /vault [store|get|delete|list]")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_browse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🌐 browser — /browse <url>"""
    if not context.args:
        await update.message.reply_text("⚠️ /browse <url>")
        return
    url = context.args[0]
    msg = await update.message.reply_text(f"🌐 جارٍ فتح {url}...")
    try:
        from src.browser_agent import extract, screenshot
        r = extract(url)
        if r.get("ok"):
            text = f"🌐 *{r.get('title', url)}*\n\n{r.get('text', '')[:2500]}"
            await msg.edit_text(text, parse_mode="Markdown")
        else:
            await msg.edit_text(f"❌ {r.get('error')}")
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_sysinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """💻 system info — /sysinfo"""
    import platform, shutil
    text = "💻 *System Info*\n\n"
    text += f"• OS: `{platform.system()} {platform.release()}`\n"
    text += f"• Machine: `{platform.machine()}`\n"
    text += f"• Processor: `{platform.processor()[:40]}`\n"
    disk = shutil.disk_usage("/")
    text += f"• Disk: `{disk.used // (2**30)}/{disk.total // (2**30)} GB`\n"
    try:
        import psutil
        text += f"• CPU: `{psutil.cpu_percent(interval=1)}%`\n"
        text += f"• RAM: `{psutil.virtual_memory().percent}%`\n"
    except Exception:
        pass
    await update.message.reply_text(text, parse_mode="Markdown")


@authorized_only
async def cmd_integrations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔌 integrations — status of 11 GitHub integrations"""
    msg = await update.message.reply_text("🔌 جارٍ الفحص...")
    try:
        from integrations import scan_integrations
        report = scan_integrations()
        text = "🔌 *Integrations*\n\n"
        for name, info in report.items():
            status = info.get("status", "?")
            if status == "ready":
                text += f"✅ `{name}` — {info.get('files',0)} files\n"
            else:
                text += f"⚠️ `{name}` — {status}\n"
        # brain stats
        text += "\n🧠 *AI Brains:*\n"
        try:
            import urllib.request, json as _json
            with urllib.request.urlopen("http://127.0.0.1:11435/stats", timeout=5) as r:
                stats = _json.loads(r.read())
            for brain, st in stats.get("brains", {}).items():
                ok = st.get("ok", 0)
                fail = st.get("fail", 0)
                healthy = "🟢" if st.get("healthy") else "🔴"
                text += f"{healthy} `{brain}` — ok:{ok} fail:{fail}\n"
        except Exception:
            text += "⚠️ router offline\n"
        await msg.edit_text(text, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {e}")


async def cmd_obsidian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🧠 obsidian — build/refresh the knowledge-graph vault + stats"""
    msg = await update.message.reply_text("🧠 بناء الـ vault...")
    try:
        from obsidian_vault_builder import main as build_vault
        build_vault()
        vault = Path.home() / "ObsidianVault" / "EsprieAether"
        n_notes = len(list(vault.rglob("*.md")))
        n_services = len(list((vault / "Services").glob("*.md"))) if (vault / "Services").exists() else 0
        n_bots = len(list((vault / "Bots").glob("*.md"))) if (vault / "Bots").exists() else 0
        n_integ = len(list((vault / "Integrations").glob("*.md"))) if (vault / "Integrations").exists() else 0
        text = (
            "🧠 *Obsidian Vault* ✅\n\n"
            f"📝 {n_notes} notes\n"
            f"  ⚙️ {n_services} services · 🤖 {n_bots} bots · 🔌 {n_integ} integrations\n\n"
            "📂 `~/ObsidianVault/EsprieAether`\n"
            "افتح فالـ Obsidian → Graph View تشوف الخريطة كاملة.\n"
            "graph.html: `python integrations/obsidian-graphify`"
        )
        await msg.edit_text(text, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_clouddesktop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """☁️ /clouddesktop — cloud desktop agent info"""
    try:
        import urllib.request, json as _json
        with urllib.request.urlopen("http://127.0.0.1:5001/health", timeout=5) as r:
            _json.loads(r.read())
        text = (
            "☁️ *Cloud Desktop Agent*\n\n"
            "✅ Online — port 5001\n\n"
            "📋 *الأوامر:*\n"
            "/cloudstatus — حالة كاملة\n"
            "/tunnel — نفق SSH\n"
            "/group — أعضاء المجموعة\n"
            "/cloudexec — تنفيذ أمر\n\n"
            "🔗 *Endpoints:*\n"
            "`/status` · `/exec` · `/group`\n"
            "`/tunnel/start` · `/tunnel/stop`"
        )
    except Exception:
        text = "❌ Cloud Desktop offline\n\nشغّلو: `uv run python src/cloud_desktop_agent.py`"
    await update.message.reply_text(text, parse_mode="Markdown")


@authorized_only
async def cmd_cloudstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📊 /cloudstatus — full cloud desktop status"""
    msg = await update.message.reply_text("☁️ جارٍ الفحص...")
    try:
        import urllib.request, json as _json
        with urllib.request.urlopen("http://127.0.0.1:5001/status", timeout=10) as r:
            st = _json.loads(r.read())
        svc = st.get("services", {})
        procs = st.get("processes", {})
        text = "📊 *Cloud Desktop Status*\n\n🖥️ *Services:*\n"
        for name, code in svc.items():
            text += f"{'✅' if code == 200 else '🔴'} `{name}`\n"
        text += "\n⚙️ *Processes:*\n"
        for name, count in procs.items():
            text += f"• `{name}`: {count}\n"
        t = st.get("tunnel", {})
        if t.get("pid"):
            text += f"\n🔗 *Tunnel:* active → {t.get('remote_host')}\n"
        else:
            text += "\n🔗 *Tunnel:* inactive\n"
        await msg.edit_text(text, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_tunnel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔗 /tunnel — SSH reverse tunnel control"""
    args = context.args
    if not args:
        await update.message.reply_text(
            "🔗 *SSH Tunnel*\n\n"
            "`/tunnel status` — الحالة\n"
            "`/tunnel start` — تشغيل\n"
            "`/tunnel stop` — إيقاف\n\n"
            "⚙️ *Config* (في .env):\n"
            "`TUNNEL_HOST` · `TUNNEL_USER`\n"
            "`TUNNEL_KEY` · `TUNNEL_PORT`",
            parse_mode="Markdown",
        )
        return
    action = args[0].lower()
    import subprocess as _sp
    py = sys.executable
    try:
        if action == "status":
            out = _sp.run([py, "src/setup_tunnel.py", "status"],
                          capture_output=True, text=True, timeout=15, cwd=str(BASE_DIR))
            await update.message.reply_text(f"```\n{out.stdout or out.stderr}\n```", parse_mode="Markdown")
        elif action == "start":
            await update.message.reply_text("🔗 تشغيل النفق...")
            out = _sp.run([py, "src/setup_tunnel.py", "start"],
                          capture_output=True, text=True, timeout=30, cwd=str(BASE_DIR))
            await update.message.reply_text(f"```\n{out.stdout or out.stderr}\n```", parse_mode="Markdown")
        elif action == "stop":
            out = _sp.run([py, "src/setup_tunnel.py", "stop"],
                          capture_output=True, text=True, timeout=15, cwd=str(BASE_DIR))
            await update.message.reply_text(f"```\n{out.stdout or out.stderr}\n```", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ استعمل: status | start | stop")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """👥 /group — cloud desktop group members"""
    try:
        import urllib.request, json as _json
        with urllib.request.urlopen("http://127.0.0.1:5001/group", timeout=5) as r:
            g = _json.loads(r.read())
        members = g.get("members", [])
        text = f"👥 *Group* ({len(members)} members)\n\n"
        for m in members:
            text += f"• *{m.get('name')}* — {m.get('role')}\n"
        text += "\n➕ `/group add <name> [role]`"
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_cloudexec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """⚡ /cloudexec — run a shell command via cloud desktop (token required)"""
    args = context.args
    if not args:
        await update.message.reply_text(
            "⚡ *Cloud Exec*\n\n`/cloudexec <command>`\n\n⚠️ يشفّر عبر token"
        )
        return
    cmd = " ".join(args)
    msg = await update.message.reply_text(f"⚡ `{cmd}`")
    try:
        import urllib.request, json as _json, os
        token = os.getenv("CLOUD_DESKTOP_TOKEN", "")
        payload = _json.dumps({"cmd": cmd, "timeout": 60}).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:5001/exec", data=payload,
            headers={"Content-Type": "application/json", "X-Token": token},
        )
        with urllib.request.urlopen(req, timeout=90) as r:
            res = _json.loads(r.read())
        if "error" in res:
            await msg.edit_text(f"❌ {res['error']}")
            return
        text = f"```\n{res.get('stdout','') or res.get('stderr','')}\n```\nexit: {res.get('exit_code')}"
        await msg.edit_text(text[:4000], parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_tm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """💰 /tm — TraffMonetizer status"""
    try:
        import json as _json
        sfile = Path(os.environ["APPDATA"]) / "Traffmonetizer" / "settings.json"
        dfile = Path(os.environ["APPDATA"]) / "Traffmonetizer" / "storage.json"
        s = _json.loads(sfile.read_text()) if sfile.exists() else {}
        d = _json.loads(dfile.read_text()) if dfile.exists() else {}
        tok = s.get("Token", "")
        tok_short = f"{tok[:8]}...{tok[-4:]}" if tok else "(none)"
        text = (
            "💰 *TraffMonetizer*\n\n"
            f"🔑 Token: `{tok_short}`\n"
            f"✅ Accepting: {s.get('Accepting', '?')}\n"
            f"🚀 StartWithWindows: {s.get('StartWithWindows', '?')}\n"
            f"🆔 Device ID: `{d.get('id', '?')}`\n\n"
            "📊 Dashboard: https://app.traffmonetizer.com/dashboard\n"
            "🔄 `/tmrestart` — إعادة التشغيل\n"
            "🐕 watchdog: auto-restart 24/7"
        )
    except Exception as e:
        text = f"❌ خطأ: {e}"
    await update.message.reply_text(text, parse_mode="Markdown")


@authorized_only
async def cmd_tmrestart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔄 /tmrestart — restart TraffMonetizer"""
    msg = await update.message.reply_text("🔄 إعادة تشغيل TraffMonetizer...")
    try:
        import subprocess as _sp
        import time as _time
        _sp.run(["taskkill", "/F", "/IM", "Traffmonetizer.exe"],
                capture_output=True, timeout=10)
        _time.sleep(2)
        _sp.Popen([str(Path(os.environ["APPDATA"]) / "Traffmonetizer" / "app" / "Traffmonetizer.exe")])
        await msg.edit_text("✅ TraffMonetizer restarted")
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {e}")


SUNNA_DIR = Path.home() / "Desktop" / "Sunna-Equipe-Industrial"
SUNNA_API = "http://127.0.0.1:5100"


def _sunna_api(path: str) -> dict:
    import urllib.request
    import json as _json
    try:
        with urllib.request.urlopen(SUNNA_API + path, timeout=8) as r:
            return _json.loads(r.read().decode("utf-8"))
    except Exception:
        return {}


@authorized_only
async def cmd_sunna(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🏭 /sunna — Sunna company status (bots + agents + counts)"""
    st = _sunna_api("/status")
    bots = _sunna_api("/bots")
    lines = ["🏭 *SUNNA ÉQUIPE INDUSTRIAL*", ""]
    if not st:
        lines.append("⚠️ bridge offline — `sunna_api.py` ماشي شغال")
    else:
        c = st.get("company", {})
        t = st.get("team", {})
        cnt = st.get("counts", {})
        lines += [
            f"🏢 {c.get('name', 'SUNNA')} — {c.get('type', '')}",
            f"🆔 ICE: `{c.get('ice', '')}`",
            f"🏗️ {c.get('workshop', '')}",
            "",
            f"📂 بحث: {cnt.get('research_files', '?')} · وثائق: {cnt.get('docs', '?')} · كتالوج: {cnt.get('catalogue', '?')}",
            f"🤖 بوتات: {len(bots.get('bots', [])) if bots else '?'} · وكلاء: {len(t.get('agents', []))}",
            "",
            "📋 `/sunnabilan` — التقرير اليومي",
            "🧾 `/sunnadevis <client> <produit> <qty>` — devis جديد",
        ]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@authorized_only
async def cmd_sunnabilan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📋 /sunnabilan — latest Sunna bilan report"""
    candidates = sorted(SUNNA_DIR.glob("Bilan_Journee_*.md"), reverse=True)
    if not candidates:
        candidates = sorted(SUNNA_DIR.glob("Etat_du_Projet*.md"), reverse=True)
    if not candidates:
        await update.message.reply_text("📭 ما كاين حتى bilan — شغّل `Al_Afdal` أولاً")
        return
    txt = candidates[0].read_text(encoding="utf-8", errors="replace")
    head = txt[:1800]
    msg = await update.message.reply_text("📋 ...")
    try:
        await msg.edit_text(f"📋 *{candidates[0].name}*\n\n{md_escape(head)}", parse_mode="Markdown")
    except Exception:
        await msg.edit_text(f"📋 {candidates[0].name}\n\n{head}")


@authorized_only
async def cmd_sunnadevis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🧾 /sunnadevis <client> <produit> <qty> — build a devis via Sunna bot"""
    args = context.args or []
    if len(args) < 3:
        await update.message.reply_text(
            "🧾 الاستعمال: `/sunnadevis \"Nom Client\" \"Produit\" 5`\n"
            "مثال: `/sunnadevis \"Amine\" \"Abreuvoir 200L\" 5`\n\n"
            "المنتجات المعروفة: `/sunnadevis list`",
            parse_mode="Markdown")
        return
    if args[0].lower() == "list":
        import subprocess as _sp
        r = _sp.run([sys.executable, str(SUNNA_DIR / "bots" / "devis_builder.py"), "--list"],
                    capture_output=True, text=True, timeout=30)
        out = r.stdout[:1500] or r.stderr[:500]
        await update.message.reply_text(f"📦 *Produits:*\n\n{md_escape(out)}", parse_mode="Markdown")
        return
    client, produit, qty = args[0], " ".join(args[1:-1]), args[-1]
    msg = await update.message.reply_text("🧾 كنعمّر الـ devis...")
    try:
        import subprocess as _sp
        r = _sp.run([sys.executable, str(SUNNA_DIR / "bots" / "devis_builder.py"),
                     "--client", client, "--product", produit, "--qty", qty],
                    capture_output=True, text=True, timeout=60)
        out = (r.stdout or r.stderr)[:1200]
        await msg.edit_text(f"🧾 *Devis*\n\n{md_escape(out)}", parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {md_escape(str(e))}")


@authorized_only
async def cmd_sunnanetlify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🌐 /sunnanetlify — live site URL + claim status"""
    nf = _sunna_api("/netlify")
    if not nf or not nf.get("deployed"):
        await update.message.reply_text("🌐 الموقع مازال ماشي منشور — شغّل `netlify_deploy_bot.py`")
        return
    claimed = "✅ دائم" if nf.get("claimed") else "⏰ مؤقت (خاص claim)"
    lines = [
        "🌐 *Sunna — الموقع*",
        "",
        f"🔗 {nf.get('url')}",
        f"🔑 password: `{nf.get('password', '—')}`",
        f"📌 {claimed}",
        "",
        "باش يولي دائم: app.netlify.com → sign up (sunnaequipeindustrial@gmail.com) → Claim",
    ]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@authorized_only
async def cmd_sunnaprix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📈 /sunnaprix — live material prices (steel/galva/zinc)"""
    pj = SUNNA_DIR / "Recherche" / "live_prices.json"
    if not pj.exists():
        await update.message.reply_text("📈 ما كاين حتى بيانات — شغّل `sunna_price_tracker.py`")
        return
    try:
        d = json.loads(pj.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    lines = ["📈 *أثمنة المواد (live)*", ""]
    for k, v in d.items():
        p = v.get("price")
        unit = v.get("unit", "")
        ch = v.get("change_pct")
        if p is None:
            lines.append(f"• {k}: —")
        else:
            arrow = f" ({ch:+.1f}%)" if isinstance(ch, (int, float)) else ""
            lines.append(f"• {k}: *{p}* {unit}{arrow}")
    lines += ["", "🔄 tracker كايحدّث كل 6 ساعات", "🧾 `/sunnadevis` كايستعمل هاد الأثمنة"]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@authorized_only
async def cmd_sunnacout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🧮 /sunnacout [product] [qty] — cost estimate against live prices"""
    args = context.args or []
    try:
        sys.path.insert(0, str(SUNNA_DIR / "bots"))
        import importlib
        ce = importlib.import_module("cost_estimator_agent")
        if not args:
            # estimate-all summary
            results = ce.estimate_all()
            lines = [f"🧮 *تقدير الكلفة* — {len(results)} produit\n"]
            for r in results[:10]:
                lines.append(f"• {r['product'][:32]}: `{r['price_ttc']:,.0f}` DH TTC")
            lines += ["", f"الأسعار: حديد `{results[0]['prices_used']['steel_dh_kg']}` DH/kg · جلفنة `{results[0]['prices_used']['galva_dh_kg']}` DH/kg"]
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
            return
        qty = 1
        product_name = " ".join(args)
        if args[-1].isdigit():
            qty = int(args[-1])
            product_name = " ".join(args[:-1])
        p = ce.find_product(product_name)
        if not p:
            await update.message.reply_text(f"❌ produit introuvable: {product_name}")
            return
        est = ce.estimate_product(p, qty)
        await update.message.reply_text(ce.format_telegram(est), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_digest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📊 /digest — observability digest (services + board + cloud + memory)"""
    from pathlib import Path
    BASE = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(BASE / "src"))
    try:
        from digest_agent import format_telegram
        text = format_telegram()
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_harvest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🎯 /harvest — skill candidates from the veille index"""
    from pathlib import Path
    BASE = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(BASE / "src"))
    try:
        from skill_harvester import format_telegram
        text = format_telegram(top=8)
        await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_jarvis_intel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🧠 /jarvisintel — JARVIS intel bridge status | /jarvisintel <name> — research"""
    from pathlib import Path
    BASE = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(BASE / "src"))
    try:
        import jarvis_intel_bridge as jib
        args = context.args
        if args:
            name = " ".join(args)
            await update.message.reply_text(f"🧠 JARVIS: كنجيب على `{name}`...", parse_mode="Markdown")
            result = jib.research(name)
            if result.get("status") == "complete":
                dossier = json.dumps(result.get("dossier", {}), ensure_ascii=False)[:800]
                text = f"🧠 *JARVIS — {name}*\n\n`{dossier}`"
                await update.message.reply_text(text, parse_mode="Markdown")
            else:
                await update.message.reply_text(
                    f"🧠 JARVIS `{name}`: {result.get('status')}\n`{json.dumps(result, ensure_ascii=False)[:400]}`",
                    parse_mode="Markdown")
        else:
            text = jib.status_report()
            await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_selfimprove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🧪 /selfimprove — self-improvement status | /selfimprove run — learn from errors now"""
    from pathlib import Path
    BASE = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(BASE / "bots"))
    try:
        import self_improve as si
        args = context.args
        if args and args[0] == "run":
            await update.message.reply_text("🧪 كنشخّص الأخطاء...", parse_mode="Markdown")
            r = si.improve_once()
            await update.message.reply_text(
                f"🧪 *Self-Improve*\nفحص: `{r.get('scanned',0)}` · جديد: `{r.get('new',0)}` · شخّص: `{r.get('diagnosed',0)}`",
                parse_mode="Markdown")
        else:
            await update.message.reply_text(si.status(), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_cherry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🍒 /cherry — Cherry Studio bridge status | /cherry mirror — push board to web UI"""
    from pathlib import Path
    BASE = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(BASE / "bots"))
    try:
        import cherry_bridge as cb
        args = context.args
        if args and args[0] == "mirror":
            r = cb.mirror_board()
            if r.get("ok"):
                await update.message.reply_text(
                    f"🍒 تم إرسال `{r.get('mirrored',0)}` رسالة للوحة Cherry", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"❌ {r.get('error','cherry not reachable')}")
        else:
            await update.message.reply_text(cb.status(), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_apps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🏭 /apps — app factory status | /apps build <slug> — MVP+code | /apps ideate — regen"""
    from pathlib import Path
    BASE = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(BASE / "bots"))
    try:
        import app_factory as af
        args = context.args or []
        if not args:
            await update.message.reply_text(af.status(), parse_mode="Markdown")
            return
        sub = args[0]
        if sub == "ideate":
            await update.message.reply_text("🏭 كنولّدو 60 فكرة... (يقدر ياخد 2-3 دقايق)", parse_mode="Markdown")
            r = af.run_ideate()
            if r.get("ok"):
                await update.message.reply_text(
                    f"🏭 *App Factory*\nولّد: `{r.get('generated',0)}` فكرة\nأحسن: `{r.get('top',0)}`\nالأول: `{r.get('best','')}`",
                    parse_mode="Markdown")
            else:
                await update.message.reply_text(f"❌ {r.get('error','فشل')}")
        elif sub == "build" and len(args) >= 2:
            slug = args[1]
            await update.message.reply_text(f"🏗️ كنبني `{slug}` (MVP + كود)...", parse_mode="Markdown")
            from app_mvp import run_mvp, run_code
            r1 = run_mvp(slug)
            r2 = run_code(slug)
            if r2.get("ok"):
                await update.message.reply_text(
                    f"✅ *{slug}* جاهز\n📁 `AppFactory/apps/{slug}/`\n\n"
                    f"الملفات:\n" + "\n".join(f"• `{f}`" for f in r2.get("files", [])),
                    parse_mode="Markdown")
            else:
                await update.message.reply_text(f"❌ {r2.get('error', r1.get('error','فشل'))}")
        elif sub == "top":
            top = af.load_top()
            if not top:
                await update.message.reply_text("ما كاينش أفكار — دير `/apps ideate`")
                return
            lines = ["🏆 *أحسن 20 تطبيق*", ""]
            for a in top[:10]:
                lines.append(f"• `{a['score']}` [{a.get('category','?')}] *{a['name']}*\n  _{a.get('pitch','')[:70]}_")
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown", disable_web_page_preview=True)
        else:
            await update.message.reply_text(
                "استعمل:\n`/apps` — الحالة\n`/apps ideate` — ولّد 60 فكرة\n`/apps top` — أحسن 20\n`/apps build <slug>` — MVP + كود",
                parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🕸️ /graph — vault graph health | /graph fix — link orphans now"""
    from pathlib import Path
    BASE = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(BASE / "bots"))
    try:
        import graph_fixer as gf
        args = context.args
        if args and args[0] == "fix":
            await update.message.reply_text("🕸️ كنربط الملاحظات المقطوعة...", parse_mode="Markdown")
            r = gf.fix()
            await update.message.reply_text(
                f"🕸️ *Graph Fixer*\nربط: `{r.get('fixed',0)}` · orphans: `{r.get('orphans_found',0)}` · graph: `{'✅' if r.get('graph_rebuilt') else '❌'}`",
                parse_mode="Markdown")
        else:
            await update.message.reply_text(gf.status(), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_jarvisdev(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🧠 /jarvisdev — JARVIS agent-developer status | /jarvisdev write — write a new agent"""
    from pathlib import Path
    BASE = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(BASE / "bots"))
    try:
        import jarvis_dev as jd
        args = context.args
        if args and args[0] == "write":
            await update.message.reply_text("🧠 JARVIS كيكتب agent جديد... (يقدر ياخد شوية وقت)", parse_mode="Markdown")
            idea = " ".join(args[1:]) if len(args) > 1 else None
            r = jd.develop_once(idea_text=idea)
            if r.get("written"):
                await update.message.reply_text(
                    f"🧠 *كتب agent جديد*\n`{r.get('module')}`\nالفكرة: `{r.get('idea')}`\nstaged: `src/_staged/`",
                    parse_mode="Markdown")
            else:
                await update.message.reply_text(f"❌ {r.get('error','فشل')}")
        else:
            await update.message.reply_text(jd.status(), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_jarvisdsh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🤖 /jarvisdsh — JARVIS⇄DSH relay status | /jarvisdsh task <url> — run a web task"""
    import urllib.request, json as _json
    args = context.args
    if args and args[0] == "task" and len(args) > 1:
        url = args[1]
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:5105/task",
                data=_json.dumps({"url": url, "actions": []}).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as r:
                d = _json.loads(r.read().decode())
            eng = d.get("engine", "?")
            note = d.get("note", "")
            await update.message.reply_text(
                f"🤖 *JARVIS⇄DSH*\nengine: `{eng}`\nurl: `{url}`\n{note}",
                parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")
        return
    # status
    try:
        with urllib.request.urlopen("http://127.0.0.1:5105/health", timeout=5) as r:
            h = _json.loads(r.read().decode())
        dsh = "🟢 running" if h.get("dsh_running") else "🟡 local-fallback"
        await update.message.reply_text(
            f"🤖 *JARVIS⇄DSH relay*\nrelay: `{h.get('status')}`\nDSH: {dsh}\nfallback: `{h.get('fallback')}`\ntargets: `{h.get('targets')}`\n\n`/jarvisdsh task <url>` — run a web task",
            parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ relay ما خدامش: {e}")


@authorized_only
async def cmd_executor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """⚙️ /executor — task executor status | /executor run — execute now"""
    from pathlib import Path
    BASE = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(BASE / "bots"))
    try:
        import task_executor as te
        args = context.args
        if args and args[0] == "run":
            await update.message.reply_text("⚙️ كننفّذ المهام المقترحة...", parse_mode="Markdown")
            r = te.execute_once()
            await update.message.reply_text(
                f"⚙️ *Executor*\nنفّذ: `{r.get('executed',0)}` · باقي: `{r.get('pending',0)}`",
                parse_mode="Markdown")
        else:
            text = te.status()
            await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_colibri(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🧠 /colibri — colibri serve status | /colibri start — start 30B API"""
    from pathlib import Path
    BASE = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(BASE / "bots"))
    try:
        import colibri_launcher as cl
        args = context.args
        if args and args[0] == "start":
            await update.message.reply_text("🧠 colibri: كنشغّل serve...", parse_mode="Markdown")
            ok = cl.start_serve(detached=True)
            if ok:
                await update.message.reply_text(
                    f"✅ *colibri serve شغّال*\\n`{cl.SERVE_URL}/v1`", parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ serve ما تشغّلش — التحميل مازال ناقص", parse_mode="Markdown")
        else:
            text = cl.status()
            await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_work(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📋 /work — الحالة العامة للمهام والتكاملات"""
    from pathlib import Path
    BASE = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(BASE / "bots"))
    try:
        import work_organizer as wo
        text = wo.render_status(wo.build_status(wo.organize(wo.sort_items(wo.load_roadmap()))))
        await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_selfheal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """❤️ /heal — حالة الإصلاح والتشغيل الذاتي"""
    from pathlib import Path
    BASE = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(BASE / "bots"))
    try:
        import self_heal as sh
        args = context.args
        if args and args[0] == "run":
            await update.message.reply_text("❤️ إجراء فحص الإصلاح...")
            r = sh.heal()
            up = sum(1 for v in r.get("services", {}).values() if v == "up")
            total = len(r.get("services", {}))
            m = "❤️ *تقرير الإصلاح*" + NL + NL + "⏰ " + str(r.get("checked_at")) + NL + "✅ " + str(up) + "/" + str(total)
            await update.message.reply_text(m, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            try:
                r = json.loads(sh.REPORT_FILE.read_text())
                up = sum(1 for v in r.get("services", {}).values() if v == "up")
                total = len(r.get("services", {}))
                lines = ["❤️ *تقرير الإصلاح*", "⏰ " + str(r.get("checked_at")), "✅ " + str(up) + "/" + str(total)]
                if r.get("changed"):
                    lines.append("🔧 إعادة تشغيل: " + ", ".join(r["restarts"]))
                await update.message.reply_text(NL.join(lines), parse_mode="Markdown", disable_web_page_preview=True)
            except Exception:
                await update.message.reply_text("❤️ لا يوجد تقرير بعد. /heal run")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

async def cmd_rea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔬 /rea — REA reverse-engineering bridge | /rea <path> — analyze a target"""
    from pathlib import Path
    BASE = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(BASE / "src"))
    try:
        import rea_agent
        args = context.args
        if args:
            target = " ".join(args)
            await update.message.reply_text(f"🔬 REA: كنحلّل `{target}`...", parse_mode="Markdown")
            result = rea_agent.investigate(target)
            if result.get("ok"):
                await update.message.reply_text(
                    f"🔬 *REA — تم التحليل*\n`{target}`\n\n"
                    f"النتائج محفوظة فالذاكرة + معلنة فالـ mesh ✅",
                    parse_mode="Markdown")
            else:
                await update.message.reply_text(
                    f"❌ REA: {result.get('error', '?')[:200]}", parse_mode="Markdown")
        else:
            text = rea_agent.status_report()
            await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """💾 /backup — encrypted backup of both workspaces"""
    import subprocess
    args = context.args or []
    action = args[0].lower() if args else "run"
    BASE = Path(__file__).resolve().parent.parent

    try:
        if action == "dry":
            r = subprocess.run(
                [sys.executable, str(BASE / "src" / "backup_agent.py"), "--dry-run"],
                capture_output=True, text=True, timeout=60,
            )
            await update.message.reply_text(f"📦 *معاينة*\n```\n{r.stdout[:1500]}\n```", parse_mode="Markdown")
            return

        msg = await update.message.reply_text("💾 جارٍ النسخ الاحتياطي...")
        r = subprocess.run(
            [sys.executable, str(BASE / "src" / "backup_agent.py"), "--json"],
            capture_output=True, text=True, timeout=300,
        )
        if r.returncode == 0 and r.stdout.strip():
            data = json.loads(r.stdout.strip().splitlines()[-1])
            await msg.edit_text(
                f"✅ *نسخة احتياطية*\n\n"
                f"📦 ملفات: `{data.get('files')}`\n"
                f"💽 الحجم: `{data.get('archive_mb')}` MB → `{data.get('encrypted_mb')}` MB مشفّر\n"
                f"🔐 التشفير: `{data.get('engine')}`\n"
                f"📅 `{data.get('stamp')}`",
                parse_mode="Markdown"
            )
        else:
            await msg.edit_text(f"❌ خطأ: {(r.stderr or r.stdout or '')[:300]}")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


@authorized_only
async def cmd_sunnakanban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📋 /sunnakanban — Sunna kanban board (todo/doing/done)"""
    kb = _sunna_api("/kanban") if False else None  # kanban is on 5103, not 5100
    import urllib.request as _u
    try:
        with _u.urlopen("http://127.0.0.1:5103/board", timeout=8) as r:
            import json as _j
            kb = _j.loads(r.read().decode())
    except Exception:
        kb = None
    if not kb:
        await update.message.reply_text("📋 kanban ماشي شغال — شغّل `veritas_kanban.py`")
        return
    lines = ["📋 *Sunna Kanban*", ""]
    for col, emoji in [("todo", "🔴"), ("doing", "🟡"), ("done", "🟢")]:
        items = kb.get(col, [])
        lines.append(f"{emoji} *{col}* ({len(items)})")
        for it in items[:6]:
            t = it["title"][:45]
            lines.append(f"  • {t}")
        lines.append("")
    lines.append("🔗 http://localhost:5103/board")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ═══════════════════════════════════
#  Main
# ═══════════════════════════════════

async def set_commands(app: Application):
    """ضبط قائمة الأوامر في Telegram"""
    commands = [
        BotCommand("start", "بدء البوت"),
        BotCommand("help", "المساعدة"),
        BotCommand("jarvis", "محادثة مع الذكاء المحلي"),
        BotCommand("jarvisintel", "جسر JARVIS Intel — حالة + بحث"),
        BotCommand("rea", "REA — الهندسة العكسية (تحليل binaries/apps)"),
        BotCommand("colibri", "colibri serve — حالة 30B API المحلي"),
        BotCommand("executor", "منفّذ المهام — ينفّذ ما يقترحه الوكلاء"),
        BotCommand("selfimprove", "التعلّم الذاتي — يشخّص الأخطاء ويقترح إصلاحات"),
        BotCommand("cherry", "جسر Cherry Studio — لوحة الويب + موديلات إضافية"),
        BotCommand("jarvisdev", "JARVIS المطوّر — يكتب agents جدد للمنظومة"),
        BotCommand("jarvisdsh", "JARVIS⇄DSH relay — تشغيل مهام الويب عبر DSH"),
        BotCommand("graph", "شبكة المعرفة — صحة الـ vault | /graph fix يربط الملاحظات"),
        BotCommand("apps", "مصنع التطبيقات — 60 فكرة→20→MVP→كود+RevenueCat"),
        BotCommand("hermes", "محرك Hermes (محلي/سحابي)"),
        BotCommand("status", "حالة النظام"),
        BotCommand("web", "رابط لوحة التحكم"),
        BotCommand("ollama", "حالة Ollama"),
        BotCommand("wallet", "المحافظ"),
        BotCommand("airdrop", "حالة الأيردروب"),
        BotCommand("sync", "مزامنة GitHub"),
        BotCommand("somnia", "حالة Somnia"),
        BotCommand("stats", "الإحصائيات"),
        BotCommand("services", "حالة الخدمات"),
        BotCommand("report", "تقرير فوري"),
        BotCommand("vpn", "التحكم بـ VPN"),
        BotCommand("airdrops", "أحدث الإيردروبات"),
        BotCommand("mesh", "شبكة الوكلاء — تواصل وتطوير"),
        BotCommand("cloudnode", "GitHub Cloud Node — تحكم من التيليفون"),
        BotCommand("veille", "رصد GitHub — أفضل المستودعات"),
        BotCommand("memory", "الذاكرة الدلالية — تذكّر وابحث"),
        BotCommand("voice", "الصوت — /voice say <text>"),
        BotCommand("airdrop_sync", "جلب الإيردروبات فوراً"),
        BotCommand("pharos", "حالة Pharos"),
        BotCommand("robots", "محرك الروبوتات"),
        BotCommand("robots_run", "تشغيل دورة روبوتات"),
        BotCommand("cmd", "تنفيذ أمر shell"),
        BotCommand("run", "تنفيذ أمر ذكي"),
        BotCommand("evolve", "اقتراحات التطوير"),
        BotCommand("cloud", "حالة Cloud"),
        BotCommand("ask", "مساعد ذكي شامل"),
        BotCommand("alerts", "تنبيهات ذكية"),
        BotCommand("analyze", "تحليل السجلات"),
        BotCommand("auto_apply", "تطبيق تلقائي"),
        BotCommand("market", "أسعار السوق"),
        BotCommand("digest", "التقرير اليومي"),
        BotCommand("bandwidth", "مشاركة الإنترنت"),
        BotCommand("approve", "الموافقة على اقتراح"),
        BotCommand("reject", "رفض اقتراح"),
        BotCommand("robots", "حالة الروبوتات"),
        BotCommand("robots_run", "تشغيل دورة روبوتات"),
        BotCommand("files", "مدير الملفات"),
        BotCommand("task", "المهام والتذكيرات"),
        BotCommand("vault", "خزنة كلمات السر"),
        BotCommand("browse", "فتح صفحة ويب"),
        BotCommand("sysinfo", "معلومات النظام"),
        BotCommand("integrations", "حالة 11 تكامل + أدمغة AI"),
        BotCommand("sunna", "حالة شركة Sunna"),
        BotCommand("sunnabilan", "تقرير Sunna اليومي"),
        BotCommand("sunnadevis", "إنشاء devis (عرض ثمن)"),
        BotCommand("sunnanetlify", "رابط موقع Sunna المباشر"),
        BotCommand("sunnaprix", "أثمنة المواد الحية (حديد/غلفنة)"),
        BotCommand("sunnacout", "تقدير كلفة منتج (حديد+غلفنة+يد عاملة)"),
        BotCommand("backup", "نسخة احتياطية مشفرة"),
        BotCommand("digest", "ملخص النظام — خدمات + وكلاء + ذاكرة"),
        BotCommand("harvest", "مرشحون من veille — أفكار للتبني"),
        BotCommand("sunnakanban", "لوحة Sunna kanban"),
        BotCommand("obsidian", "خريطة المعرفة Obsidian"),
        BotCommand("clear", "مسح سجل JARVIS"),
        BotCommand("ping", "اختبار سريع"),
    ]
    await app.bot.set_my_commands(commands)


# ═══════════════════════════════════════════════════════════
# NEW: Arabic explanation command
# ═══════════════════════════════════════════════════════════
async def cmd_explain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شرح الموضوع باللغة العربية — /explain <موضوع>"""
    args = context.args or []
    topic = " ".join(args) if args else "نظام EsprieAether"

    if not args:
        help_text = (
            "📖 *شرح النظام*\n\n"
            "أرسل /explain <موضوع> عوضك تشتغل على:\n"
            "• /explain بوت — عن بوت تيليغرام\n"
            "• /explain وكلاء — عن شبكة الوكلاء\n"
            "• /explain كولابري — عن الخدمة القائمة\n"
            "• /explain أخبار — عن رصد الأخبار\n"
            "• /explain ذاكرة — عن المتعشية الموضوعية\n"
            "• /explain صحة — عن حالة الخدمات\n"
            "• /explain أي موضوع تاني وعايز شرح تفصيلي"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")
        return

    topic_lower = topic.lower()

    if any(k in topic_lower for k in ("بوت", "telegram", "bot")):
        text = (
            "🤖 *شرح البوت*\n\n"
            "بوت تيليغرام @Esprieaether_bot هو نقطة الدخول الرئيسية للتحكم بكل نظام EsprieAether.\n\n"
            "📋 *الأدوار:* \n"
            "1. الرد على الأوامر (start, help, status, ...)\n"
            "2. توجيه النصوص العامة لكل الوكيل/الأجهزة\n"
            "3. إدارة الصوت والتذكيرات والملفات\n"
            "4. جلب البيانات من الخدمات المختلفة\n\n"
            "🔑 *مصادقة:* البوت محدد بالـ CHAT_ID في .env\n"
            "🧠 *المحرك:* LLM7 مجاني (cloud) + Ollama (local)"
        )
    elif any(k in topic_lower for k in ("وكلاء", "agent", "mesh", "وكيل", "شبكة")):
        text = (
            "🤝 *شرح الوكلاء*\n\n"
            "شبكة الوكلاء (Agent Mesh) هي نظام متعدد الوكلاء اللي بيتحدث بعض شوية من خلال ملف مشترك.\n\n"
            "📊 *كيف يعمل:* \n"
            "• كل وكيل يشتغل في مسار مستقل\n"
            "• الوكيلات تتبادل المعلومات عبر board مشترك\n"
            "• there's a watchdog لمراقبة الحالة\n"
            "• ملف board: data/agent_board.json\n\n"
            "👥 *الوكيلات الرئيسية: *\n"
            "• self_evolve — التعلم والتطوير الذاتي\n"
            "• pharos_agent — الرصد والمراقبة\n"
            "• agent_mesh — الاتصال بين الوكيلات\n"
            "• orchestrator — تنسيق المهام\n"
            "• watchdog — الحماية والاستعادة"
        )
    elif any(k in topic_lower for k in ("كولابري", "collab", "cloud", "سحابي", "clouddesk", "cloud_desktop")):
        text = (
            "☁️ *شرح الخدمة السحابية*\n\n"
            "الخدمة السحابية (Cloud Desktop) هي واجهة بعيدة للتحكم في النظام من أي مكان.\n\n"
            "🔌 *الاتصال:* \n"
            "• HOST: 0.0.0.0:5001\n"
            "• Cloud Desktop Token: في .env (CLOUD_DESKTOP_TOKEN)\n"
            "• ملف log: data/logs/cloud_desktop.log\n\n"
            "⚠️ *ملاحظة:* الخدمة تحتاج التأكد من البورت والتوكن الصحيحين."
        )
    elif any(k in topic_lower for k in ("أخبار", "veille", "رصد", "news", "مستودعات")):
        text = (
            "📰 *شرح رصد الأخبار (Veille)*\n\n"
            "Veille = نظام رصد لمستودعات GitHub ومشاريع الذكاء الاصطناعي.\n\n"
            "🎯 *الوظائف:* \n"
            "• التسوق المنتظم للمستودعات المهمة\n"
            "• تصنيف المشاريع بدرجات (A، B، C)\n"
            "• إشعارات عن التحديثات الجديدة\n"
            "• تقديم اقتراحات للمشاريع المؤهلة\n\n"
            "📁 *ملفات:* data/veille.json, src/veille_agent.py"
        )
    elif any(k in topic_lower for k in ("ذاكرة", "memory", "متعشية", "ذكاء", "embeddings", "vector")):
        text = (
            "🧠 *شرح المتعشية الموضوعية (Vector Memory)*\n\n"
            "ذاكرة دلالية تعمل على حفظ وبحث المعرفة باستخدام التمثيلات الدلالية (embeddings).\n\n"
            "📝 *كيف تتصرف:* \n"
            "• تخزين النصوص مع فضلات دلالية\n"
            "• البحث عن مقالات مشابهة\n"
            "• الربط بين المفاهيم المتشابهة\n"
            "• استخدام by the LLM للسياق الإضافي\n\n"
            "📁 *ملفات:* src/memory_layer.py, data/memory/"
        )
    elif any(k in topic_lower for k in ("صحة", "health", "خدمات", "service", "حالة", "core")):
        text = (
            "🏥 *شرح حالة الخدمات (Health)*\n\n"
            "الخدمة الصحية تعرض حالة كل مكون من مكونات النظام.\n\n"
            "📋 *الخدمات التالية:* \n"
            "• web_interface (5000)\n"
            "• agent_mesh (11437)\n"
            "• ai_router (11435)\n"
            "• cloud_desktop (5001)\n"
            "• sunna_api (5100)\n"
            "• integrations (5102)\n"
            "• kanban (5103)\n"
            "• homedock (5104)\n\n"
            "✅ *نبئ:* كل خدمة جمهال حالتها الصحية ف الـ /bothealth"
        )
    elif any(k in topic_lower for k in ("أخطاء", "bug", "خطأ", "fix", "مشكلة", "أمن", "security")):
        text = (
            "🔧 *شرح حل الأخطاء*\n\n"
            "كيف تتعامل مع الأخطاء في النظام:\n\n"
            "1. راجع سجل البوت: cat data/logs/bot_aether.log\n"
            "2. شغل /bothealth عشان تعرف أي خدمة متأثرة\n"
            "3. شغل /botlog لتراجع الأخطاء الأخيرة\n"
            "4. أعد تشغيل البوت: /botrestart\n"
            "5. لو مش حل وهأمر: /selfimprove عشان أقترح إصلاحات\n\n"
            "📁 *ملفات السجل:* data/logs/*.log"
        )
    else:
        text = (
            "📝 *شرح الموضوع: " + topic + "*\n\n"
            "سأرسل لك شرحاً تفصيلياً عن هذا الموضوع...\n\n"
            "👉 يمكنك أيضاً كتابة: /explain <موضوع> عشان تحصل على شرح بالتفصيل."
        )

    await update.message.reply_text(text, parse_mode="Markdown")



def main():
    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN غير موجود في .env")
        sys.exit(1)
    if not CHAT_ID:
        print("⚠️ TELEGRAM_CHAT_ID غير موجود — البوت سيرد على أي شخص!")
        print("   أضفه في .env للأمان.")

    print("═" * 60)
    print("⚡ ESPRIEAETHER TELEGRAM BOT")
    print("═" * 60)
    bot_username = os.getenv("BOT_USERNAME", "ESPRIEXAETHER_bot")
    print(f"🤖 Bot: @{bot_username}")
    print(f"📋 Instance: {BOT_NAME} (env: {BOT_ENV})")
    print(f"👤 Authorized Chat ID: {CHAT_ID}")
    # المحرك النشط
    try:
        st = jarvis.status()
        engine_label = {"llm7": "☁️ LLM7 (مجاني)", "ollama": "🖥️ Ollama محلي", "hermes": "☁️ Hermes"}.get(
            st.get("active_engine"), st.get("active_engine", "?")
        )
        print(f"🧠 Engine: {engine_label} ({st.get('model')})")
    except Exception:
        print(f"🧠 Engine: 🖥️ Ollama ({os.getenv('OLLAMA_MODEL')})")
    print("═" * 60)

    app = Application.builder().token(TOKEN).build()

    # تسجيل الأوامر
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("jarvisintel", cmd_jarvis_intel))
    app.add_handler(CommandHandler("rea", cmd_rea))
    app.add_handler(CommandHandler("colibri", cmd_colibri))
    app.add_handler(CommandHandler("executor", cmd_executor))
    app.add_handler(CommandHandler("work", cmd_work))
    app.add_handler(CommandHandler("heal", cmd_selfheal))
    app.add_handler(CommandHandler("selfimprove", cmd_selfimprove))
    app.add_handler(CommandHandler("cherry", cmd_cherry))
    app.add_handler(CommandHandler("jarvisdev", cmd_jarvisdev))
    app.add_handler(CommandHandler("jarvisdsh", cmd_jarvisdsh))
    app.add_handler(CommandHandler("graph", cmd_graph))
    app.add_handler(CommandHandler("apps", cmd_apps))
    app.add_handler(CommandHandler("hermes", cmd_hermes))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("metrics", cmd_metrics))
    app.add_handler(CommandHandler("web", cmd_web))
    app.add_handler(CommandHandler("ollama", cmd_ollama))
    app.add_handler(CommandHandler("wallet", cmd_wallet))
    app.add_handler(CommandHandler("airdrop", cmd_airdrop))
    app.add_handler(CommandHandler("sync", cmd_sync))
    app.add_handler(CommandHandler("somnia", cmd_somnia))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("services", cmd_services))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("cmd", cmd_cmd))
    app.add_handler(CommandHandler("run", cmd_run))
    app.add_handler(CommandHandler("evolve", cmd_evolve))
    app.add_handler(CommandHandler("cloud", cmd_cloud))
    app.add_handler(CommandHandler("ask", cmd_ask))
    app.add_handler(CommandHandler("alerts", cmd_alerts))
    app.add_handler(CommandHandler("analyze", cmd_analyze))
    app.add_handler(CommandHandler("auto_apply", cmd_auto_apply))
    app.add_handler(CommandHandler("market", cmd_market))
    app.add_handler(CommandHandler("digest", cmd_digest))
    app.add_handler(CommandHandler("bandwidth", cmd_bandwidth))
    app.add_handler(CommandHandler("approve", cmd_approve))
    app.add_handler(CommandHandler("reject", cmd_reject))
    app.add_handler(CommandHandler("vpn", cmd_vpn))
    app.add_handler(CommandHandler("airdrops", cmd_airdrops))
    app.add_handler(CommandHandler("mesh", cmd_mesh))
    app.add_handler(CommandHandler("cloudnode", cmd_cloudnode))
    app.add_handler(CommandHandler("veille", cmd_veille))
    app.add_handler(CommandHandler("memory", cmd_memory))
    app.add_handler(CommandHandler("voice", cmd_voice))
    app.add_handler(CommandHandler("airdrop_sync", cmd_airdrop_sync))
    app.add_handler(CommandHandler("pharos", cmd_pharos))
    app.add_handler(CommandHandler("robots", cmd_robots))
    app.add_handler(CommandHandler("robots_run", cmd_robots_run))
    app.add_handler(CommandHandler("files", cmd_files))
    app.add_handler(CommandHandler("task", cmd_tasks))
    app.add_handler(CommandHandler("vault", cmd_vault))
    app.add_handler(CommandHandler("browse", cmd_browse))
    app.add_handler(CommandHandler("sysinfo", cmd_sysinfo))
    app.add_handler(CommandHandler("integrations", cmd_integrations))

    # cloud desktop commands
    app.add_handler(CommandHandler("clouddesktop", cmd_clouddesktop))
    app.add_handler(CommandHandler("tunnel", cmd_tunnel))
    app.add_handler(CommandHandler("group", cmd_group))
    app.add_handler(CommandHandler("cloudexec", cmd_cloudexec))
    app.add_handler(CommandHandler("cloudstatus", cmd_cloudstatus))

    # TraffMonetizer commands
    app.add_handler(CommandHandler("tm", cmd_tm))
    app.add_handler(CommandHandler("tmrestart", cmd_tmrestart))

    # Sunna company commands
    app.add_handler(CommandHandler("sunna", cmd_sunna))
    app.add_handler(CommandHandler("sunnabilan", cmd_sunnabilan))
    app.add_handler(CommandHandler("sunnadevis", cmd_sunnadevis))
    app.add_handler(CommandHandler("sunnanetlify", cmd_sunnanetlify))
    app.add_handler(CommandHandler("sunnaprix", cmd_sunnaprix))
    app.add_handler(CommandHandler("sunnacout", cmd_sunnacout))
    app.add_handler(CommandHandler("backup", cmd_backup))
    app.add_handler(CommandHandler("harvest", cmd_harvest))

    # ─── NEW: Arabic explanation command (user requested) ───
    app.add_handler(CommandHandler("explain", cmd_explain))
    app.add_handler(CommandHandler("شرح", cmd_explain))  # Arabic alias

    # ─── NEW: Bot self-maintenance commands (3) ───
    app.add_handler(CommandHandler("bothealth", cmd_bot_health))
    app.add_handler(CommandHandler("botlog", cmd_bot_log))
    app.add_handler(CommandHandler("botrestart", cmd_bot_restart))

    # register /sunna* in the Telegram command menu
    try:
        app.post_init = set_commands
    except Exception:
        pass


    # ─── Anything-but-commands: universal router (the user talks to the bot freely) ───
    # Routes any non-command text to the right agent/tool, or to the LLM brain
    # (Hermes free cloud / Ollama local) when it is a generic request.
    async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (update.message.text or "").strip()
        if not text:
            return
        user_id = update.effective_user.id
        if CHAT_ID and user_id != CHAT_ID:
            await update.message.reply_text("⛔ غير مصرح لك.")
            return
        low = text.lower()

        # ── keyword routing ──
        if any(k in low for k in ("airdrop", "إيردروب", "bsc", "telegram airdrop", "farm")):
            from airdrop_scorer import format_telegram
            msg = format_telegram(8)
            await update.message.reply_text(msg or "📭 لا توجد فرص مؤهلة حالياً.", parse_mode="Markdown")
            return
        if any(k in low for k in ("executor", "شغّل", "work", "run a", "استغل", "نفّذ")):
            from executor_agent import ExecutorAgent
            ex = ExecutorAgent()
            out = await ex.run(text)
            await update.message.reply_text(md_escape(str(out))[:4000] or "✅ تم التنفيذ بنجاح.", parse_mode="Markdown")
            return
        if any(k in low for k in ("mesh", "agent", "agent_mesh", "عام", "شبكة الوكيل")):
            from src.ask_agent import AskAgent
            a = AskAgent()
            resp = await a.ask(text, system="أجب كل ما أسألك كومة وكيل. اعرض اسم الخدمة أو النتيجة فقط.")
            await update.message.reply_text(md_escape(resp)[:4000] or "✅ تم الاستماع.", parse_mode="Markdown")
            return
        if any(k in low for k in ("selfimprove", "heal", "شفي", "تطوري", "تعلم")):
            from self_evolve import SelfEvolve
            s = SelfEvolve()
            r = await s.run(text)
            await update.message.reply_text(md_escape(str(r))[:4000], parse_mode="Markdown")
            return
        if "cloud" in low or "cloud node" in low:
            from cloud_fallback import CloudFallback
            c = CloudFallback()
            out = await c.pull_or_push(text)
            await update.message.reply_text(md_escape(str(out))[:4000], parse_mode="Markdown")
            return

        # ── anything else → LLM brain (Hermes free cloud, fallback Ollama) ──
        from src.hermes_bridge import HermesBridge
        try:
            brain = HermesBridge()
            reply = await brain.ask(text, system="أنت EsprieAether — ذكاء النظام الموحّد. خذ من المخزون (π، مذكرات، أهداف، مشاكل، أدوات قيد التشغيل) وأجب باداء المهمة المطلوبة في أقصر وقت. إذا طُلب تشغيل أمر، نفذه وrclّر. اجب بعمليات عن ذكر تقصد.")
            await update.message.reply_text(md_escape(str(reply))[:4000] or "✅ Ορασε.", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}", parse_mode="Markdown")

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    # ضبط قائمة الأوامر عند البدء
    app.post_init = set_commands

    logger.info("🚀 بدء تشغيل البوت...")

# ═══════════════════════════════════════════════════════════
# NEW: Bot self-maintenance commands (3)
# ═══════════════════════════════════════════════════════════

async def cmd_bot_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot health — shows system status & service endpoints (0.0.0.0)."""
    lines = []
    lines.append("┌" + "─" * 46 + "┬" + "─" * 30 + "┬" + "─" * 10 + "┬" * 10)
    lines.append("│ *Service*".ljust(46) + "│ *Port*".rjust(30) + "│ *State*".rjust(10) + "│ *URL*".rjust(10) + "│")
    lines.append("├" + "─" * 46 + "┼" + "─" * 30 + "┼" + "─" * 10 + "┼" * 10 + "┤")
    services = [
        ("web_interface", "5000", "http://127.0.0.1:5000/"),
        ("jarvis-api", "8000", "http://127.0.0.1:8000/api/health"),
        ("agent_mesh", "11437", "http://127.0.0.1:11437/"),
        ("ai_router", "11435", "http://127.0.0.1:11435/"),
        ("cloud_desktop", "5001", "http://127.0.0.1:5001/"),
        ("sunna_api", "5100", "http://127.0.0.1:5100/"),
        ("integrations", "5102", "http://127.0.0.1:5102/"),
        ("kanban", "5103", "http://127.0.0.1:5103/"),
        ("homedock", "5104", "http://127.0.0.1:5104/"),
    ]
    ok = 0
    for name, port, url in services:
        import urllib.request
        try:
            urllib.request.urlopen(url, timeout=4)
            st = "✅"
            ok += 1
        except Exception:
            st = "❌"
        lines.append(f"│ {name}".ljust(46) + f"│ {port}".rjust(30) + f"│ {st}".rjust(10) + f"│ {url}".rjust(10) + "│")
    lines.append("├" + "─" * 46 + "┴" + "─" * 30 + "┴" + "─" * 10 + "┴" * 10 + "┤")
    lines.append(f"│ *Total*: {ok}/9 ✅".ljust(46) + "│".rjust(30) + "│".rjust(10) + "│".rjust(10) + "│")
    lines.append("└" + "─" * 46 + "┴" + "─" * 30 + "┴" + "─" * 10 + "┴" * 10 + "┘")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_bot_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot log — shows last N lines of bot logs."""
    n = 20
    if context.args and context.args[0].isdigit():
        n = min(int(context.args[0]), 200)
    log_file = Path(__file__).parent.parent / "data" / "logs" / "bot.log"
    try:
        if not log_file.exists():
            raise FileNotFoundError
        text = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        last = text[-n:]
        if not last:
            await update.message.reply_text("📭 لا توجد سجلات (log empty).")
            return
        out = "\n".join(f"{i+1:>4} | {l}" for i, l in enumerate(reversed(last)))
        await update.message.reply_text(f"📋 *Last {n} lines of bot.log*\n" + out, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ لا يمكن قراءة السجل: {e}")

async def cmd_bot_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot restart — restarts the bot daemon (supervisor keeps it alive)."""
    user = update.effective_user.username or "user"
    await update.message.reply_text(f"🔄 *Bot restart* — إعادة تشغيل البوت (يتم من قبل supervisor)...\n", parse_mode="Markdown")
    from pathlib import Path
    log = Path(__file__).parent.parent / "data" / "logs" / "bot-restart.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(f"[{datetime.now().isoformat()}] restart requested by @{user}\n", encoding="utf-8")
    await update.message.reply_text("✅ *Bot restart requested* — البوت سيعود تلقائياً مع supervisor.")



app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

