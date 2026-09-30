"""
⚡ ESPRIE AETHER — Fast Bot v1.0
بوت Telegram خفيف، سريع، وأذكى
"""
import os
import sys
import time
import logging
import hashlib
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=str(Path.home() / "AETHER_V8" / ".env"), override=True)
sys.path.insert(0, str(Path(__file__).parent))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.constants import ParseMode, ChatAction

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("fast_bot")

# ═══════════════════════════════════════════════════════════
#  التوكن
# ═══════════════════════════════════════════════════════════
BOT_TOKEN = os.getenv("TELEGRAM_CLIENT_BOT_TOKEN", "") or os.getenv("TELEGRAM_BOT_TOKEN", "")

# ═══════════════════════════════════════════════════════════
#  Cache
# ═══════════════════════════════════════════════════════════
_cache = {}
_CACHE_TTL = 300

def cache_get(text):
    k = hashlib.md5(text.encode()).hexdigest()[:16]
    if k in _cache:
        result, ts = _cache[k]
        if time.time() - ts < _CACHE_TTL:
            return result
        del _cache[k]
    return None

def cache_set(text, result):
    if len(_cache) > 200:
        oldest = min(_cache.items(), key=lambda x: x[1][1])
        del _cache[oldest[0]]
    k = hashlib.md5(text.encode()).hexdigest()[:16]
    _cache[k] = (result, time.time())


# ═══════════════════════════════════════════════════════════
#  AI Core
# ═══════════════════════════════════════════════════════════
def ai_ask(prompt, max_tokens=500):
    # Cache
    cached = cache_get(prompt)
    if cached:
        logger.info("💾 cache hit")
        return cached
    
    # FreeLLM
    try:
        import requests
        key = os.getenv("FREELLM_KEY", "")
        r = requests.post(
            "http://localhost:3000/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "command-a-reasoning-08-2025",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
            },
            timeout=60,
        )
        if r.status_code == 200:
            result = r.json()["choices"][0]["message"]["content"]
            cache_set(prompt, result)
            return result
    except Exception as e:
        logger.warning(f"FreeLLM: {e}")
    
    # Fallback: Ollama
    try:
        import requests
        r = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "qwen2.5:3b", "prompt": prompt, "stream": False},
            timeout=60,
        )
        if r.status_code == 200:
            result = r.json().get("response", "")
            cache_set(prompt, result)
            return result
    except Exception as e:
        logger.warning(f"Ollama: {e}")
    
    return "⚠️ لا يمكن الوصول إلى النموذج"


# ═══════════════════════════════════════════════════════════
#  Commands
# ═══════════════════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """⚡ **AETHER AI** — بوت سريع وذكي

🤖 **الأوامر:**
`/talk <رسالة>` — محادثة حرة
`/task <مهمة>` — تنفيذ مهمة
`/code <وصف>` — توليد كود
`/article <موضوع>` — مقال
`/search <موضوع>` — بحث
`/airdrop` — الإيردروبات
`/status` — الحالة
`/help` — المساعدة

💡 جرب: `/talk مرحبا`"""
    
    keyboard = [[InlineKeyboardButton("📖 المساعدة", callback_data="help")]]
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("💬 اكتب: `/talk <رسالتك>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    user_msg = " ".join(context.args)
    msg = await update.message.reply_text("💭 ...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    t0 = time.time()
    try:
        result = ai_ask(f"أجب بإيجاز: {user_msg}", max_tokens=800)
        elapsed = time.time() - t0
        await msg.edit_text(f"{result[:3800]}\n\n_⚡ {elapsed:.1f}s_", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await msg.edit_text(f"❌ {str(e)[:200]}")


async def task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🎯 `/task <مهمتك>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    user_task = " ".join(context.args)
    msg = await update.message.reply_text("⏳ ...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    try:
        result = ai_ask(user_task, max_tokens=1500)
        await msg.edit_text(result[:3800], parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await msg.edit_text(f"❌ {str(e)[:200]}")


async def code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("💻 `/code <وصف>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    desc = " ".join(context.args)
    msg = await update.message.reply_text("💻 ...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    prompt = f"اكتب كود Python لـ: {desc}\n\nقدم الكود فقط مع شرح موجز."
    try:
        result = ai_ask(prompt, max_tokens=1500)
        await msg.edit_text(result[:3800], parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await msg.edit_text(f"❌ {str(e)[:200]}")


async def article(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("📝 `/article <موضوع>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    topic = " ".join(context.args)
    msg = await update.message.reply_text(f"📝 أكتب عن: _{topic}_...", parse_mode=ParseMode.MARKDOWN)
    
    prompt = f"اكتب مقال احترافي عن: {topic}\n500-800 كلمة، عربي فصيح."
    try:
        result = ai_ask(prompt, max_tokens=2000)
        if len(result) > 3800:
            parts = [result[i:i+3800] for i in range(0, len(result), 3800)]
            await msg.edit_text(parts[0], parse_mode=ParseMode.MARKDOWN)
            for p in parts[1:]:
                await update.message.reply_text(p, parse_mode=ParseMode.MARKDOWN)
        else:
            await msg.edit_text(result, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await msg.edit_text(f"❌ {str(e)[:200]}")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🔍 `/search <موضوع>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    query = " ".join(context.args)
    msg = await update.message.reply_text(f"🔍 أبحث عن: _{query}_...", parse_mode=ParseMode.MARKDOWN)
    
    try:
        result = ai_ask(f"قدم معلومات محدثة عن: {query}\n3-5 نقاط رئيسية.", max_tokens=1000)
        await msg.edit_text(result[:3800], parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await msg.edit_text(f"❌ {str(e)[:200]}")


async def airdrop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("📡 ...")
    
    try:
        import json
        data_file = Path.home() / "AETHER_V8" / "airdrops_advanced.json"
        if data_file.exists():
            data = json.loads(data_file.read_text())
            scans = data.get("scans", [])
            if scans:
                last = scans[-1]
                text = "📡 **أحدث الإيردروبات:**\n\n"
                for src, items in last.get("results", {}).items():
                    text += f"*{src}:*\n"
                    for i, item in enumerate(items[:3], 1):
                        text += f"  {i}. {item.get('title', '?')[:70]}\n"
                    text += "\n"
                await msg.edit_text(text[:3800], parse_mode=ParseMode.MARKDOWN)
                return
        
        await msg.edit_text("لا توجد إيردروبات حديثة")
    except Exception as e:
        await msg.edit_text(f"❌ {str(e)[:200]}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    text = "📊 **حالة النظام**\n\n"
    
    try:
        import requests
        for name, url in [("FreeLLM", "3000"), ("Web", "5000"), ("Content", "8000")]:
            try:
                r = requests.get(f"http://localhost:{url}/", timeout=2)
                text += f"✅ {name}\n"
            except:
                text += f"⚠️ {name}\n"
    except:
        pass
    
    text += f"\n👤 **حسابك:**\n"
    text += f"ID: `{user.id}`\n"
    text += f"الاسم: {user.first_name}"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """📖 **الأوامر**

**المحادثة:**
`/talk <رسالة>` — دردشة
`/task <مهمة>` — مهمة

**الإبداع:**
`/code <وصف>` — كود
`/article <موضوع>` — مقال
`/search <موضوع>` — بحث

**النظام:**
`/airdrop` — الإيردروبات
`/status` — الحالة

**أو أرسل رسالة مباشرة!**"""
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def auto_talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رد تلقائي على أي رسالة"""
    if not update.message.text:
        return
    text = update.message.text
    
    msg = await update.message.reply_text("💭 ...")
    
    try:
        result = ai_ask(f"أجب بإيجاز على: {text}", max_tokens=500)
        await msg.edit_text(result[:3800], parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await msg.edit_text(f"❌ {str(e)[:100]}")


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "help":
        await help_cmd(update, context)


def main():
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN غير موجود")
        return
    
    logger.info("🚀 Fast Bot يبدأ...")
    logger.info(f"Token: {BOT_TOKEN[:20]}...")
    
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .build()
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("talk", talk))
    app.add_handler(CommandHandler("task", task))
    app.add_handler(CommandHandler("code", code))
    app.add_handler(CommandHandler("article", article))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("airdrop", airdrop))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_talk))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    logger.info("✅ Fast Bot يعمل!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
