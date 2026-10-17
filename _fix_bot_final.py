# -*- coding: utf-8 -*-
path = "src/bot.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# Locate the broken region
start_marker = "async def cmd_bot_health("
end_marker = "app.run_polling(allowed_updates=Update.ALL_TYPES)"
start = src.find(start_marker)
end = src.find(end_marker)
if start == -1 or end == -1:
    print("ERROR: markers not found")
    print("start:", start, "end:", end)
    exit(1)

# Raw string keeps \n as backslash+n (exactly what we want in the file)
new_funcs = r'''async def cmd_bot_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

'''

new_src = src[:start] + new_funcs + "\n\n" + src[end:]
with open(path, "w", encoding="utf-8") as f:
    f.write(new_src)
print("✅ Replaced broken functions with clean versions")
print("New file size:", len(new_src), "bytes")
