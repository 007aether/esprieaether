# -*- coding: utf-8 -*-
path = "src/bot.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# Fix 1: reply_text("\n".join(lines) -> was split across lines
old1 = 'reply_text("' + "\n" + '"'
new1 = r'reply_text("\n".join(lines), parse_mode="Markdown")'

# Fix 2: log out join - may also have split
old2 = 'out = "' + "\n" + '"'
new2 = r'out = "\n".join(f"{i+1:>4} | {l}" for i, l in enumerate(reversed(last)))'

if old1 in src:
    src = src.replace(old1, new1, 1)
    print("Fixed fix-1 (reply_text)")
else:
    print("WARNING: fix-1 pattern not found")

if old2 in src:
    src = src.replace(old2, new2, 1)
    print("Fixed fix-2 (log out join)")
else:
    print("WARNING: fix-2 pattern not found")

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Done")
