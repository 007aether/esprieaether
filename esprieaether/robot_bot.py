#!/usr/bin/env python3
"""
ESPRIEAETHER ROBOT BOT — بوت التحكم بالروبوتات
بوت تيليغرام مستقل خفيف كيتحكم ف محرك الروبوتات (robot_engine).
يخدم ف نفس الوقت مع bot.py الكبير (توكن مختلف).

الأوامر:
  /robots        — حالة الروبوتات
  /run           — تشغيل دورة كاملة
  /activate      — تفعيل نظام (ai/immune/...)
  /deactivate    — إيقاف نظام
  /stats         — إحصائيات المحرك
  /log           — آخر النتائج
  /ai <سؤال>     — سؤال AI (LLM7/Ollama)
"""

import os
import sys
import json
import logging
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "src"))

from dotenv import load_dotenv

# ─── env خاص (يسمح بتشغيل البوتات متعددة) ───
BOT_ENV = os.getenv("BOT_ENV", ".env.robots")
load_dotenv(BASE_DIR / BOT_ENV, override=True)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))

LOG_FILE = BASE_DIR / "robot_bot.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("robot-bot")

from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, ContextTypes, filters
)

# ─── المحرك ───
from robots.robot_engine import RobotEngine
eng = RobotEngine()

# ─── AI (LLM7 / Ollama) ───
try:
    from src.hermes_bridge import HermesBridge
    ai = HermesBridge()
except Exception:
    ai = None


def md_escape(text: str) -> str:
    if not text:
        return ""
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, "\\" + ch)
    return text


def authorized_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if CHAT_ID and update.effective_user.id != CHAT_ID:
            await update.message.reply_text(
                f"⛔ غير مصرح. ID: `{update.effective_user.id}`",
                parse_mode="Markdown"
            )
            return
        return await func(update, context)
    return wrapper


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 *ESPRIEAETHER ROBOT BOT*\n\n"
        "*الأوامر:*\n"
        "/robots — حالة الروبوتات\n"
        "/run — تشغيل دورة\n"
        "/activate <نظام> — تفعيل\n"
        "/deactivate <نظام> — إيقاف\n"
        "/stats — إحصائيات\n"
        "/log — آخر النتائج\n"
        "/ai <سؤال> — سؤال AI"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


@authorized_only
async def cmd_robots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    st = eng.get_stats()
    by_status = st.get("robots_by_status", {})
    results = st.get("results_by_status", {})
    text = (
        f"🤖 *محرك الروبوتات*\n\n"
        f"• الدورات: `{st.get('cycles', 0)}`\n"
        f"• نشطة: `{by_status.get('active', 0)}`\n"
        f"• idle: `{by_status.get('idle', 0)}`\n\n"
        f"✅ ناجحة: `{results.get('ok', 0)}`\n"
        f"❌ أخطاء: `{results.get('error', 0)}`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


@authorized_only
async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⚙️ جارٍ تشغيل الروبوتات...")
    system = context.args[0] if context.args else None
    r = eng.run_once(system=system)
    await msg.edit_text(
        f"✅ *دورة #{r['cycle']}*\n\n"
        f"• المجموع: `{r['total']}`\n"
        f"• ناجح: `{r['ok']}`\n"
        f"• خطأ: `{r['error']}`",
        parse_mode="Markdown"
    )


@authorized_only
async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("استخدم: /activate <نظام>\nمثال: /activate ai")
        return
    system = context.args[0]
    eng.activate(system=system)
    await update.message.reply_text(f"✅ تم تفعيل نظام: `{system}`", parse_mode="Markdown")


@authorized_only
async def cmd_deactivate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("استخدم: /deactivate <نظام>")
        return
    system = context.args[0]
    eng.deactivate(system=system)
    await update.message.reply_text(f"⏸️ تم إيقاف نظام: `{system}`", parse_mode="Markdown")


@authorized_only
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    st = eng.get_stats()
    recent = st.get("recent", [])
    text = "📊 *إحصائيات المحرك*\n\n"
    for r in recent[:8]:
        emoji = "✅" if r["status"] == "ok" else "❌"
        text += f"{emoji} `{r['robot_id']}` {r['role']}\n"
    await update.message.reply_text(text, parse_mode="Markdown")


@authorized_only
async def cmd_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    st = eng.get_stats()
    recent = st.get("recent", [])
    if not recent:
        await update.message.reply_text("📭 لا نتائج بعد")
        return
    text = "📋 *آخر النتائج*\n\n"
    for r in recent[:10]:
        emoji = "✅" if r["status"] == "ok" else "❌"
        text += f"{emoji} `{r['robot_id']}` — {md_escape(r['summary'][:40])}\n"
    await update.message.reply_text(text, parse_mode="Markdown")


@authorized_only
async def cmd_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ai:
        await update.message.reply_text("⚠️ المحرك غير متاح")
        return
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("استخدم: /ai <سؤال>")
        return
    msg = await update.message.reply_text("🧠 يفكر...")
    try:
        r = ai.ask(prompt)
        engine = ai.status().get("active_engine", "?")
        label = {"llm7": "☁️ LLM7", "ollama": "🖥️ محلي"}.get(engine, engine)
        await msg.edit_text(f"🧠 *{label}*:\n\n{md_escape(r)}", parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"⚠️ خطأ: {e}")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)


def main():
    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN غير موجود")
        sys.exit(1)

    print("═" * 60)
    print("🤖 ESPRIEAETHER ROBOT BOT")
    print(f"🔑 Token: {TOKEN[:20]}...")
    print(f"👤 Chat ID: {CHAT_ID or 'OPEN'}")
    print("═" * 60)

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("robots", cmd_robots))
    app.add_handler(CommandHandler("run", cmd_run))
    app.add_handler(CommandHandler("activate", cmd_activate))
    app.add_handler(CommandHandler("deactivate", cmd_deactivate))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("log", cmd_log))
    app.add_handler(CommandHandler("ai", cmd_ai))

    async def set_commands(app):
        await app.bot.set_my_commands([
            BotCommand("robots", "حالة الروبوتات"),
            BotCommand("run", "تشغيل دورة"),
            BotCommand("activate", "تفعيل نظام"),
            BotCommand("deactivate", "إيقاف نظام"),
            BotCommand("stats", "إحصائيات"),
            BotCommand("log", "آخر النتائج"),
            BotCommand("ai", "سؤال AI"),
        ])

    app.post_init = set_commands
    logger.info("robot bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
