import sqlite3, requests, os, sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from wallet.manager import get_existing_wallet
from github_agent import get_github_status, auto_commit_and_push
from trading.trader import get_okx_market_data
from security_agent import activate_stealth_and_defense
from lab_generator import generate_custom_tool
from jarvis_bridge import query_open_jarvis, get_jarvis_status
from sys_agent import execute_shell_command

TELEGRAM_TOKEN = "8366524959:AAGvIB-bS-NQ2aQxXedSPYc-3UHKi1ziNXc"
ADMIN_CHAT_ID = None

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    global ADMIN_CHAT_ID
    ADMIN_CHAT_ID = u.effective_chat.id
    msg = (
        "⚡🤖 **ESPRIEAETHER - REAL CORE (NO MOCK)**\n\n"
        "النظام يعمل بالحقيقة المطلقة والصلاحيات الكاملة.\n\n"
        "/structure - حالة النظام الحقيقية 📊\n"
        "/okx - السعر الحقيقي لـ Bitcoin من OKX 📈\n"
        "/security - فحص الأمان الحقيقي للبيسي 🛡️\n"
        "/makelab [optimizer] - إنشاء أداة برمجية حقيقية 🛠️\n"
        "/cmd [أمر] - تنفيذ أوامر النظام مباشرة ⚡"
    )
    await u.message.reply_text(msg)

async def structure_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    w = get_existing_wallet()
    sec = activate_stealth_and_defense()
    await u.message.reply_text(
        f"📊 **[حالة النظام الحقيقية]**\n\n"
        f"📍 محفظة Aether: `{w['address']}`\n"
        f"👤 الهوية: `007aether@gmail.com`\n"
        f"{sec}"
    )

async def okx_trade_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    data = get_okx_market_data("BTC/USDT")
    if data["success"]:
        await u.message.reply_text(f"📊 **سعر Bitcoin الفعلي (OKX):** `${data['price']}` | التغير: `{data['change']}%`")
    else:
        await u.message.reply_text(f"❌ خطأ في الاتصال بمنصة OKX: {data['error']}")

async def security_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text(activate_stealth_and_defense())

async def makelab_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    args = c.args
    tool_type = args[0] if args else "optimizer"
    res = generate_custom_tool(tool_type)
    auto_commit_and_push(f"EsprieAether Real Sync: {tool_type}")
    await u.message.reply_text(f"{res}\n\n✅ تم الحفظ والرفع لـ GitHub بنجاح.")

async def cmd_execution(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cmd = " ".join(c.args)
    if not cmd:
        return await u.message.reply_text("⚠️ أكتب الأمر، مثال: `/cmd uptime`")
    await u.message.reply_text(execute_shell_command(cmd))

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    commands = [
        ("start", start), ("structure", structure_cmd), ("okx", okx_trade_cmd),
        ("security", security_cmd), ("makelab", makelab_cmd), ("cmd", cmd_execution)
    ]
    for cmd, func in commands:
        app.add_handler(CommandHandler(cmd, func))
        
    print("[+] EsprieAether Real Core is running...")
    app.run_polling()
