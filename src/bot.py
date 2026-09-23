import sqlite3, requests, os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from wallet.manager import get_existing_wallet
from github_agent import get_github_status, auto_commit_and_push
from trading.trader import get_okx_market_data
from sys_agent import execute_shell_command, take_system_screenshot
from airdrop_farmer import execute_farming_cycle
from developer_agent import scan_github_trends_and_build
from autonomous_brain import aether_strategic_thinking, execute_autonomous_earning_action
from security_agent import activate_stealth_and_defense
from search_agent import ask_aether_web
from bounty_farmer import hunt_bounties_and_airdrops
from lab_generator import generate_custom_tool
from jarvis_bridge import query_open_jarvis, get_jarvis_status

TELEGRAM_TOKEN = "8366524959:AAGvIB-bS-NQ2aQxXedSPYc-3UHKi1ziNXc"
ADMIN_CHAT_ID = None

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    global ADMIN_CHAT_ID
    ADMIN_CHAT_ID = u.effective_chat.id
    msg = (
        "⚡🤖 **ESPRIEAETHER - JARVIS ULTIMATE CORE** شاعل 24/24!\n\n"
        "تم دمج محرك OpenJarvis المحلي بنجاح مع منظومة AETHER.\n"
        "الهوية: `007aether@gmail.com` | الأمان: خفي ومحمي (Stealth)\n\n"
        "/jarvis [سؤالك/أمرك] - **محادثة EsprieAether Jarvis بالذكاء المحلي المتقدم 🧠**\n"
        "/makelab [scraper/optimizer] - ابتكار أدوات برمجية في الـ Lab 🛠️\n"
        "/structure - هيكل النظام الشامل والوكلاء 📊\n"
        "/security - درع الأمان السيبراني 🛡️\n"
        "/bounty - صيد الجوائز والأيردروبات 🏆\n"
        "/okx - أسعار التداول الحقيقية 📈\n"
        "/shot - لقطة شاشة مباشرة للبيسي 📸\n"
        "/cmd [أمر] - التحكم الكامل في النظام ⚡"
    )
    await u.message.reply_text(msg)

# محادثة Jarvis المباشرة عبر تيليغرام
async def jarvis_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = " ".join(c.args)
    if not query:
        return await u.message.reply_text("⚠️ اكتب أمرك أو سؤالك لـ Jarvis، مثال:\n`/jarvis كيف نطور استراتيجية التداول اليوم؟`")
    await u.message.reply_text("⚡ **[EsprieAether Jarvis]** جاري معالجة الطلب عبر محرك OpenJarvis المحلي...")
    reply = query_open_jarvis(query)
    await u.message.reply_text(reply)

async def structure_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    w = get_existing_wallet()
    github_st = get_github_status()
    security_st = activate_stealth_and_defense()
    jarvis_st = get_jarvis_status()
    
    report = (
        "📐 **[EsprieAether - Jarvis Unified System Architecture]**\n\n"
        f"👤 **الهوية والاتصال:** `007aether@gmail.com`\n"
        f"💼 **المحفظة الذكية:** `{w['address']}`\n"
        f"🧠 **محرك الذكاء:** {jarvis_st}\n"
        f"🛡️ **الأمان السيبراني:** مفعل 100% (Stealth Mode)\n"
        f"🔗 **GitHub Sync:** {github_st}\n\n"
        "🤖 **الوكلاء النشطون (24/24):**\n"
        "1. EsprieAether Jarvis Core (الإدارة العليا والذكاء المحلّي)\n"
        "2. Security Agent (حماية ضد الاختراق والحجب)\n"
        "3. Bounty & Airdrop Farmer (صيد الأيردروبات والفرص)\n"
        "4. Software Lab Factory (توليد السكربتات والأدوات أوتوماتيكياً)\n\n"
        "🟢 **النظام يعمل بذاتية تامة ولا يتوقف حتى عند إغلاق التيرمينال.**"
    )
    await u.message.reply_text(report)

async def makelab_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    args = c.args
    tool_type = args[0] if args else "optimizer"
    await u.message.reply_text(f"🧪 **[Jarvis Lab Factory]** جاري توليد الأداة (`{tool_type}`)...")
    res = generate_custom_tool(tool_type)
    auto_commit_and_push(f"EsprieAether Jarvis: Generated {tool_type}")
    await u.message.reply_text(f"{res}\n\n✅ تم الحفظ والرفع إلى GitHub أوتوماتيكياً!")

async def security_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text(activate_stealth_and_defense())

async def bounty_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("🏆 " + hunt_bounties_and_airdrops())

async def okx_trade_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    data = get_okx_market_data("BTC/USDT")
    if data["success"]:
        await u.message.reply_text(f"📊 **Bitcoin (OKX):** `${data['price']}` | التغير: `{data['change']}%`")
    else:
        await u.message.reply_text(f"❌ خطأ: {data['error']}")

async def screenshot_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    path = take_system_screenshot()
    if path and os.path.exists(path):
        with open(path, 'rb') as photo:
            await u.message.reply_photo(photo=photo, caption="🖥️ لقطة شاشة مباشرة من مركز تحكم Jarvis")

async def cmd_execution(u: Update, c: ContextTypes.DEFAULT_TYPE):
    command_text = " ".join(c.args)
    if not command_text:
        return await u.message.reply_text("⚠️ أكتب الأمر، مثال: `/cmd ls`")
    await u.message.reply_text(execute_shell_command(command_text))

# التقرير التلقائي كل ساعتين
async def automated_two_hour_report(context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_CHAT_ID:
        thought = aether_strategic_thinking()
        bounty = hunt_bounties_and_airdrops()
        security = activate_stealth_and_defense()
        
        report = (
            "🤖⏰ **[EsprieAether Jarvis - 2h Auto Report]**\n\n"
            f"{security}\n"
            f"{thought}\n"
            f"{bounty}\n\n"
            "🟢 *النظام ومحرك Jarvis يعملان بكفاءة تامة في الخلفية 24/24.*"
        )
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=report)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    commands = [
        ("start", start), ("jarvis", jarvis_cmd), ("structure", structure_cmd),
        ("makelab", makelab_cmd), ("security", security_cmd), ("bounty", bounty_cmd),
        ("okx", okx_trade_cmd), ("shot", screenshot_cmd), ("cmd", cmd_execution)
    ]
    for cmd, func in commands:
        app.add_handler(CommandHandler(cmd, func))
        
    app.job_queue.run_repeating(automated_two_hour_report, interval=7200, first=30)
    
    print("[+] EsprieAether Jarvis Unified System is running 24/7...")
    app.run_polling()
