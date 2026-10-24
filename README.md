# ⚡ EsprieAether — Sovereign Local AI
**نظام سيبراني محلي متكامل مع JARVIS Command Center + trade-cycle autonomy.**  
**State:** PROD READY · Self-Heal ON · Autonomous 24/7

## المكونات
| المكوّن | الحالة | التفاصيل |
|--------|--------|----------|
| 🤖 JARVIS (Ollama qwen2.5:3b) | ✅ | 11434 |
| 💬 Telegram Bot | ✅ | @Esprieaether_bot (50+ أمر) |
| 🌐 Web Dashboard | ✅ | Flask على localhost:5000 |
| 📡 Trade Cycle (Flywheel) | ✅ | 6 وكلاء ورقي فقط (PAPER_ONLY=True) |
| ⌂ Self-Heal Daemon | ✅ | يربط trade_cycle + services (24/7) |
| 📊 Autonomous Loop | ✅ | cycles 58+, self-improve |
| 🤖 Knowledge Base | ✅ | Obsidian (vault) |
| 🔐 Security Agent | ✅ | Windows/auth |

## روابط سريعة
- **Dashboard:** http://localhost:5000
- **Telegram:** @Esprieaether_bot
- **Trade Cycle DB:** work/data/trade_cycle.db
- **GitHub:** https://github.com/007aether/esprieaether
- **Docs:** https://github.com/007aether/esprieaether/blob/main/README.md

## التشغيل
```bash
python src/autonome_evolve.py --daemon
python work/agents/trade_cycle/loop.py --daemon
```

**آخر تحديث تلقائي:** 2026-10-24  
**State:** Autonomous & Healing (no manual restart required)
