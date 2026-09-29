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

from vpn_agent import VPNAgent
from airdrop_agent import AirdropAgent

# ─── الإعدادات ───
load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
AETHER_ID = os.getenv("AETHER_ID", "007aether")

# ─── Logger ───
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("aether-bot")

# ─── JARVIS ───
jarvis = JarvisBridge()

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
    """عرض أحدث الإيردروبات"""
    text = airdrop_agent.format_telegram(limit=5)
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
async def cmd_pharos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حالة Pharos"""
    await update.message.reply_text(
        "🚧 *Pharos قيد التطوير*\n\n"
        "_سيتم إضافته في التحديث القادم._",
        parse_mode="Markdown"
    )
@authorized_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة الترحيب"""
    text = f"""
⚡ *ESPRIEAETHER COMMAND CENTER* ⚡

مرحباً بك في نظامك السيبراني المحلي.
الهوية: `{AETHER_ID}`
التاريخ: `{datetime.now().strftime('%Y-%m-%d %H:%M')}`

*الأوامر المتاحة:*

🤖 *JARVIS*
• `/jarvis <سؤال>` — اسأل الذكاء المحلي
• `/clear` — مسح سجل المحادثة

📊 *النظام*
• `/status` — حالة النظام الكاملة
• `/metrics` — CPU/RAM/Disk
• `/web` — رابط لوحة التحكم

🛠️ *الأدوات*
• `/cmd <أمر>` — تنفيذ أمر shell
• `/ping` — اختبار سريع

💰 *البلوكشين*
• `/wallet` — معلومات المحفظة
• `/airdrop` — حالة الأيردروب
• `/ollama` — حالة Ollama

_اكتب /help لعرض هذه القائمة_
"""
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
        response = f"🤖 *JARVIS:*\n\n{answer}"
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

        ollama_status = jarvis.ping()
        ollama_text = "🟢 متصل" if ollama_status["status"] == "online" else "🔴 غير متصل"

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

*JARVIS*
• Ollama: {ollama_text}
• النموذج: `{ollama_status.get('current_model', '—')}`

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
    """حالة Ollama"""
    status = jarvis.ping()
    if status["status"] == "online":
        text = f"""
🤖 *Ollama*

• الحالة: 🟢 متصل
• المضيف: `{status['host']}`
• النموذج الحالي: `{status['current_model']}`
• النماذج المتاحة: `{', '.join(status['models'])}`
"""
    else:
        text = f"🔴 *Ollama غير متصل*\n\n`{status.get('error', 'خطأ غير معروف')}`"
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
    await update.message.reply_text(
        "📡 *حالة الأيردروب*\n\n"
        "_سيتم تفعيل هذه الميزة قريباً مع وكلاء Somnia._",
        parse_mode="Markdown"
    )

@authorized_only
async def cmd_sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مزامنة GitHub فورية"""
    msg = await update.message.reply_text("🔄 جارٍ المزامنة مع GitHub...")
    try:
        from github_agent import GitHubAgent
        agent = GitHubAgent()
        if not agent.gh:
            await msg.edit_text("⚠️ GitHub غير متصل")
            return

        files = [
            BASE_DIR / "src" / "jarvis_bridge.py",
            BASE_DIR / "src" / "web_interface.py",
            BASE_DIR / "src" / "bot.py",
            BASE_DIR / "src" / "github_agent.py",
            BASE_DIR / "src" / "autonomous_loop.py",
            BASE_DIR / "STATUS.md",
        ]
        existing = [f for f in files if f.exists()]
        result = agent.push_files(existing, "⚡ Manual sync from Telegram")

        if result.get("status") == "ok":
            await msg.edit_text(
                f"✅ *تمت المزامنة*\n\n"
                f"📦 الملفات: `{result.get('files_count')}`\n"
                f"🔗 [عرض الـ Commit]({result.get('url')})",
                parse_mode="Markdown"
            )
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
        await update.message.reply_text("⚠️ `/approve <id>`", parse_mode="Markdown")
        return

    sid = context.args[0]
    msg = await update.message.reply_text(f"⚙️ جارٍ التنفيذ...")
    try:
        result = evolve.approve(sid)
        if result["status"] == "ok":
            await msg.edit_text(f"✅ *تم*\n\n{result['message']}", parse_mode="Markdown")
        else:
            await msg.edit_text(f"❌ {result['message']}")
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {e}")


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
async def cmd_cloud(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة Cloud Fallback"""
    import asyncio

    args = context.args or []
    action = args[0].lower() if args else "status"

    if action == "test":
        await update.message.reply_text(
            "☁️ جارٍ اختبار Cloud... سيصلك الرد قريباً"
        )
        result = await asyncio.to_thread(cloud.ask, "قل فقط: مرحبا", None, "cloud")
        if result["status"] == "ok":
            await update.message.reply_text(
                "✅ Cloud يعمل" + chr(10) + chr(10) +
                "📡 المصدر: " + result["source"] + chr(10) +
                "💬 الرد: " + result["answer"][:150]
            )
        else:
            await update.message.reply_text(
                "❌ فشل Cloud" + chr(10) + chr(10) +
                "السبب: " + result.get("message", "unknown")[:200]
            )

    elif action == "local":
        await update.message.reply_text(
            "🏠 جارٍ اختبار Local..."
        )
        result = await asyncio.to_thread(cloud.ask, "قل فقط: مرحبا", None, "local")
        if result["status"] == "ok":
            await update.message.reply_text(
                "✅ Local يعمل" + chr(10) + chr(10) +
                "📡 المصدر: " + result["source"] + chr(10) +
                "💬 الرد: " + result["answer"][:150]
            )
        else:
            await update.message.reply_text(
                "❌ فشل Local" + chr(10) + chr(10) +
                "السبب: " + result.get("message", "unknown")[:200]
            )

    else:  # status
        text = cloud.format_telegram()
        await update.message.reply_text(text)

@authorized_only
async def cmd_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حالة الخدمات"""
    import subprocess
    text = "⚙️ *حالة الخدمات*\n\n"
    for svc in ["aether-web", "aether-bot", "aether-core", "ollama"]:
        try:
            r = subprocess.run(
                ["systemctl", "is-active", svc],
                capture_output=True, text=True, timeout=5
            )
            status = r.stdout.strip()
            emoji = "🟢" if status == "active" else "🔴"
            text += f"{emoji} `{svc}`: {status}\n"
        except Exception:
            text += f"⚠️ `{svc}`: unknown\n"
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
        response = f"🤖 *JARVIS:*\n\n{answer}"
        if len(response) > 4000:
            response = response[:4000] + "\n\n... (تم قص الباقي)"
        await msg.edit_text(response, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"⚠️ خطأ: {e}")


# ═══════════════════════════════════════
#  Main
# ═══════════════════════════════════════

async def set_commands(app: Application):
    """ضبط قائمة الأوامر في Telegram"""
    commands = [
        BotCommand("start", "بدء البوت"),
        BotCommand("help", "المساعدة"),
        BotCommand("jarvis", "محادثة مع الذكاء المحلي"),
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
        BotCommand("airdrop_sync", "جلب الإيردروبات فوراً"),
        BotCommand("pharos", "حالة Pharos"),
        BotCommand("cmd", "تنفيذ أمر shell"),
        BotCommand("run", "تنفيذ أمر ذكي"),
        BotCommand("evolve", "اقتراحات التطوير"),
        BotCommand("cloud", "حالة Cloud"),
        BotCommand("approve", "الموافقة على اقتراح"),
        BotCommand("reject", "رفض اقتراح"),
        BotCommand("clear", "مسح سجل JARVIS"),
        BotCommand("ping", "اختبار سريع"),
    ]
    await app.bot.set_my_commands(commands)


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
    print(f"🤖 Bot: @Esprieaether_bot")
    print(f"👤 Authorized Chat ID: {CHAT_ID}")
    print(f"🧠 JARVIS: {os.getenv('OLLAMA_MODEL')}")
    print("═" * 60)

    app = Application.builder().token(TOKEN).build()

    # تسجيل الأوامر
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("jarvis", cmd_jarvis))
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
    app.add_handler(CommandHandler("approve", cmd_approve))
    app.add_handler(CommandHandler("reject", cmd_reject))
    app.add_handler(CommandHandler("vpn", cmd_vpn))
    app.add_handler(CommandHandler("airdrops", cmd_airdrops))
    app.add_handler(CommandHandler("airdrop_sync", cmd_airdrop_sync))
    app.add_handler(CommandHandler("pharos", cmd_pharos))
    # أي رسالة عادية → JARVIS
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # ضبط قائمة الأوامر عند البدء
    app.post_init = set_commands

    logger.info("🚀 بدء تشغيل البوت...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
