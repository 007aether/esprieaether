"""
ESPRIE AETHER — Stars Bot (البوت الجديد للعملاء)
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=str(Path.home() / "AETHER_V8" / ".env"), override=True)

sys.path.insert(0, str(Path(__file__).parent))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    PreCheckoutQueryHandler, MessageHandler, filters, ContextTypes
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("stars_bot")

# ═══════════════════════════════════════════════════════════
#  التوكن (العميل الجديد أو القديم)
# ═══════════════════════════════════════════════════════════
BOT_TOKEN = os.getenv("TELEGRAM_CLIENT_BOT_TOKEN", "") or os.getenv("TELEGRAM_BOT_TOKEN", "")

# ═══════════════════════════════════════════════════════════
#  خطط الاشتراك (Telegram Stars)
# ═══════════════════════════════════════════════════════════
PLANS = {
    "basic": {"name": "Basic", "stars": 100, "tasks": 100, "days": 30},
    "pro": {"name": "Pro", "stars": 500, "tasks": 1000, "days": 30},
    "business": {"name": "Business", "stars": 2000, "tasks": -1, "days": 30},
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """🌟 **AETHER AI** — بوت ذكي متعدد المهام

مرحباً! أنا بوت AI متقدم:

🤖 **المهام:**
• كتابة مقالات (1000+ كلمة)
• توليد أكواد Python
• تحليل بيانات
• بحث سوق
• مراقبة الإيردروبات

💎 **الاشتراكات:**
/plans — عرض الخطط
/subscribe — الاشتراك بـ Stars

🎯 **مهام فورية:**
/task <مهمتك> — نفّذ مهمة الآن

📊 **معلومات:**
/status — حالة حسابك
/help — المساعدة

⚡ Powered by ESPRIE AETHER V8"""
    
    keyboard = [
        [InlineKeyboardButton("💎 عرض الخطط", callback_data="plans")],
        [InlineKeyboardButton("🎯 مهمة تجريبية", callback_data="demo")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "💎 **خطط الاشتراك**\n\n"
    for key, plan in PLANS.items():
        tasks_display = f"{plan['tasks']}" if plan['tasks'] > 0 else "غير محدود"
        text += f"*{plan['name']}* — {plan['stars']} ⭐\n"
        text += f"  • {tasks_display} مهمة/شهر\n"
        text += f"  • {plan['days']} يوم\n"
        text += f"  → /subscribe_{key}\n\n"
    
    text += "\n💡 **جرّب مجاناً:** /task اكتب مقال عن AI"
    await update.message.reply_text(text, parse_mode="Markdown")


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    plan_key = args[0] if args else "basic"
    
    if plan_key not in PLANS:
        await update.message.reply_text("❌ خطة غير معروفة. استخدم /plans")
        return
    
    plan = PLANS[plan_key]
    
    try:
        await context.bot.send_invoice(
            chat_id=update.effective_chat.id,
            title=f"AETHER AI — {plan['name']}",
            description=f"اشتراك {plan['name']} لمدة {plan['days']} يوم",
            payload=f"sub_{plan_key}",
            provider_token="",
            currency="XTR",
            prices=[{"label": plan['name'], "amount": plan['stars']}],
        )
    except Exception as e:
        logger.error(f"خطأ في الفاتورة: {e}")
        await update.message.reply_text(f"⚠️ الدفع غير مفعّل. تواصل مع الدعم.")


async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    logger.info(f"💎 دفع: {payment.invoice_payload} — {payment.total_amount} Stars")
    
    await update.message.reply_text(
        f"✅ **تم الدفع بنجاح!**\n\n"
        f"💎 الاشتراك: {payment.invoice_payload.replace('sub_', '').title()}\n"
        f"⭐ المبلغ: {payment.total_amount} Stars\n\n"
        f"🎉 تم تفعيل حسابك! استخدم /task لبدء المهام.",
        parse_mode="Markdown"
    )


async def task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "استخدم: /task <مهمتك>\n\n"
            "مثال:\n`/task اكتب مقال عن الذكاء الاصطناعي`",
            parse_mode="Markdown"
        )
        return
    
    user_task = " ".join(context.args)
    msg = await update.message.reply_text(f"⏳ جاري التنفيذ...\n\n📝 {user_task[:100]}")
    
    try:
        from inference_router import ask
        result = ask(user_task)
        await msg.edit_text(f"✅ **النتيجة:**\n\n{result[:3000]}")
    except Exception as e:
        logger.error(f"خطأ: {e}")
        await msg.edit_text(f"❌ خطأ: {str(e)[:200]}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(
        f"📊 **حالة حسابك**\n\n"
        f"👤 ID: `{user_id}`\n"
        f"📅 الاشتراك: Free\n"
        f"🎯 المهام المتاحة: 10/شهر\n\n"
        f"💎 للترقية: /plans",
        parse_mode="Markdown"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """📖 **المساعدة**

**الأوامر:**
/start — البداية
/plans — الخطط
/subscribe_basic — اشتراك Basic (100⭐)
/subscribe_pro — اشتراك Pro (500⭐)
/subscribe_business — اشتراك Business (2000⭐)
/task <مهمة> — نفّذ مهمة
/status — الحالة
/help — المساعدة

**أمثلة:**
`/task اكتب مقال عن AI`
`/task اكتب دالة Python للبحث الثنائي`

**الدفع:**
Telegram Stars — آمن 100%

**الدعم:**
@Esprieaether"""
    await update.message.reply_text(text, parse_mode="Markdown")


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "plans":
        await plans(update, context)
    elif query.data == "demo":
        await query.message.reply_text(
            "🎯 جرّب مهمة تجريبية:\n\n"
            "`/task اكتب فقرة قصيرة عن الذكاء الاصطناعي`",
            parse_mode="Markdown"
        )


def main():
    if not BOT_TOKEN:
        logger.error("❌ لا يوجد توكن في .env")
        return
    
    logger.info(f"🚀 بدء AETHER AI Bot...")
    logger.info(f"Token: {BOT_TOKEN[:20]}...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("plans", plans))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("task", task))
    
    # subscribe_basic, subscribe_pro, subscribe_business
    app.add_handler(CommandHandler("subscribe_basic", subscribe))
    app.add_handler(CommandHandler("subscribe_pro", subscribe))
    app.add_handler(CommandHandler("subscribe_business", subscribe))
    
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    logger.info("✅ AETHER AI Bot يعمل!")
    app.run_polling()


if __name__ == "__main__":
    main()
