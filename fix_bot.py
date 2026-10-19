import sys

path = 'C:/Users/ESPRIEAETHER/Desktop/esprieaether/src/bot.py'
with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

null_router = '''
class _NullBotRouter:
    """Stub router that neutralises legacy @router.message decorators left in
    the module (they reference a name that no longer exists). The decorators
    become no-ops so the functions remain defined but are never registered as
    handlers -- they are all registered via main() instead."""
    def message(self, *args, **kwargs):
        def deco(func):
            return func
        return deco
    def __getattr__(self, name):
        return lambda *args, **kwargs: None

router = _NullBotRouter()

'''

anchor = '''from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)
'''
assert anchor in src, "import block not found"
src = src.replace(anchor, anchor + null_router, 1)

stray = '''    main()


# REA Tools Commands
'''
assert stray in src, "stray main block not found"
src = src.replace(stray, '''# REA Tools Commands
''', 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)

print("patched OK")
print("_NullBotRouter present:", "_NullBotRouter" in src)
print("router = _NullBotRouter present:", "router = _NullBotRouter" in src)
print("stray-main-removal done:", src.count("    main()\n\n\n# REA Tools Commands") == 0)
