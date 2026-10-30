# ⚡ EsprieAether — Sovereign Local AI

**نظام سيبراني محلي متكامل** | Local-first multi-agent AI system  
**Owner:** [007aether](https://github.com/007aether)  
**Status:** Production Ready · Self-Heal ON · Autonomous 24/7

> Sees without cameras. Acts without constant human input. Heals itself.

---

## What is EsprieAether?

A **sovereign local AI stack** that runs primarily on your machine:

| Component | Port / Location | Role |
|-----------|-----------------|------|
| **Ollama (JARVIS)** | 11434 | Local LLM (qwen2.5:3b or better) |
| **AI Router** | 11435 | Multi-brain routing (local → cloud fallback) |
| **Orchestrator** | 11436 | 7-agent orchestration |
| **Web Dashboard** | 5000 | Flask control center |
| **Cloud Desktop** | 5001 | Remote access + tunnel |
| **Telegram Bot** | — | `@Esprieaether_bot` (50+ commands) |
| **Trade Cycle** | work/agents/trade_cycle | 6-agent paper trading flywheel |
| **Watchdog / Self-Heal** | — | Restarts dead services automatically |
| **Knowledge** | Obsidian + vector memory | Persistent memory |

**Core principle:** Local-first (≥70% offline capable). Paper trading by default. No real money without explicit opt-in.

---

## Quick Start

### 1. Requirements
- Python 3.10+
- Ollama installed + model pulled (`ollama pull qwen2.5:3b`)
- Windows / Linux / macOS

### 2. Setup
```bash
git clone https://github.com/007aether/esprieaether.git
cd esprieaether
cp .env.example .env
# Edit .env — fill TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GITHUB_TOKEN if needed

pip install -r requirements.txt   # or: uv sync
```

### 3. Start everything (recommended)
```bash
python start_all.py
# or on Windows:
# .\AetherStartup.ps1
```

### 4. Useful individual services
```bash
# Core autonomous loop
python src/autonome_evolve.py --daemon

# Trade Cycle (paper only)
python work/agents/trade_cycle/loop.py --once     # one cycle
python work/agents/trade_cycle/loop.py --daemon   # every hour

# Web dashboard
python src/web_interface.py

# Telegram bot
python src/bot.py

# Watchdog / self-heal
python src/watchdog.py
```

### 5. Health check
```bash
python -m src.system_health
# or open http://localhost:5000/health
```

---

## Architecture (Clean View)

```
Telegram / CLI / Web
        ↓
   Command Router / Hermes
        ↓
   AI Router (11435)  ←→  Ollama + cloud fallbacks
        ↓
   Orchestrator + Agent Mesh
        ↓
┌──────────────┬──────────────┬──────────────┐
│  Trade Cycle │  Knowledge   │  50+ Agents  │
│  (6 agents)  │  (Obsidian)  │  & Robots    │
└──────────────┴──────────────┴──────────────┘
        ↓
   Watchdog + Self-Heal + System Health
```

See **[STRUCTURE.md](STRUCTURE.md)** for the full recommended folder layout and cleanup plan.

---

## Trade Cycle (Paper Trading)

6 cooperating agents sharing one SQLite DB:

1. **Research (Jim)** — opportunities + red flags
2. **Risk (Bob)** — pure Python rules (no LLM)
3. **Trading (Doug)** — paper execution only by default
4. **Records (Jill)** — P&L + daily summary
5. **CEO (Bill)** — reviews rules
6. **Feedback** — periodic external review

```bash
cd work/agents/trade_cycle
python loop.py --once
```

**Safety:** `PAPER_ONLY = True` in `config.py`. Real trading requires explicit env + code change.

---

## Environment Variables

Copy `.env.example` → `.env`:

```env
# Required for Telegram reports
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Optional
GITHUB_TOKEN=
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
WEB_PORT=5000

# Trade Cycle (paper by default)
PAPER_ONLY=True
TRADE_API_TOKEN=
```

**Never commit real secrets.**

---

## Key Commands (Telegram)

- `/status` — system health
- `/trade` / `/flywheel` — trade cycle controls
- `/heal` — trigger self-heal
- `/report` — daily digest
- And 50+ more (see `src/bot.py`)

---

## Development Roadmap (Clean Path)

| Priority | Task | Status |
|----------|------|--------|
| High | Clean structure + archive dead code | In progress (this branch) |
| High | Unified System Health | ✅ Added |
| High | Trade Cycle reliability + better reports | ✅ Improved |
| Medium | Real trading opt-in (with kill-switch) | Planned |
| Medium | Docker Compose one-command start | Planned |
| Low | Plugin system for new agents | Planned |

---

## Safety Rules

1. **Paper trading by default** — no real money unless you deliberately enable it.
2. **Local-first** — system must work offline as much as possible.
3. **Secrets only in `.env`** — never in code or commits.
4. **Watchdog always on** in production.
5. **No destructive actions** without confirmation on critical paths.

---

## License & Contact

Private / personal project of **007aether**.  
GitHub: https://github.com/007aether/esprieaether

---

**Last major cleanup & docs:** 2026-10-30 (branch `cleanup-improve-v1`)
