# -*- coding: utf-8 -*-
import sys

path = "src/bot.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

marker = """    app.add_handler(CommandHandler("sunnakanban", cmd_sunnakanban))
    app.add_handler(CommandHandler("obsidian", cmd_obsidian))
"""

new_commands = """
    # ─── NEW: Bot self-maintenance commands (3) ───
    app.add_handler(CommandHandler("bothealth", cmd_bot_health))
    app.add_handler(CommandHandler("botlog", cmd_bot_log))
    app.add_handler(CommandHandler("botrestart", cmd_bot_restart))
"""

if marker not in src:
    print("ERROR: marker not found in bot.py")
    print("--- tail of file ---")
    print(src[-400:])
    sys.exit(1)

src = src.replace(marker, new_commands, 1)
with open(path, "w", encoding="utf-8") as f:
    f.write(src)

print("OK: Added 3 new commands (/bothealth /botlog /botrestart)")
print("Total CommandHandlers:", src.count("CommandHandler("))
