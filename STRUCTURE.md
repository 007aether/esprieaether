# EsprieAether — Clean Structure Guide

This document defines the **target clean architecture** and the cleanup plan for the repository.

## Target Layout (Recommended)

```
esprieaether/
├── README.md                 # Main entry (human + AI)
├── STRUCTURE.md              # This file
├── AGENTS.md                 # Multi-harness topology
├── CLAUDE.md                 # Guidance for AI coding assistants
├── .env.example              # All env vars documented
├── requirements.txt          # Or pyproject.toml + uv.lock
├── start_all.py              # One-command launcher
│
├── src/                      # Core Python package
│   ├── __init__.py
│   ├── system_health.py      # Unified health checks (NEW)
│   ├── ai_router.py
│   ├── orchestrator.py
│   ├── agent_mesh.py
│   ├── agent_kernel.py
│   ├── bot.py                # Telegram
│   ├── web_interface.py
│   ├── watchdog.py
│   ├── autonome_evolve.py
│   ├── cloud_desktop_agent.py
│   ├── agents/               # Domain agents (security, market, ...)
│   ├── knowledge/            # knowledge_router, memory, obsidian helpers
│   ├── integrations/
│   ├── templates/            # Flask templates
│   └── static/
│
├── work/
│   ├── agents/
│   │   └── trade_cycle/      # 6-agent paper trading system
│   │       ├── config.py
│   │       ├── database.py
│   │       ├── loop.py
│   │       ├── flywheel.py
│   │       └── agents/
│   ├── data/                 # Runtime DBs, logs (gitignored where needed)
│   └── autonomous/
│
├── bots/                     # Lightweight helper bots / launchers
├── scripts/                  # One-off maintenance scripts
├── docs/                     # Architecture, runbooks
├── tests/                    # Unit + integration tests
│
├── archive/                  # Old / experimental code (do not import from here)
│   ├── _fix_*.py
│   ├── code_old/
│   └── ...
│
└── .github/workflows/        # CI
```

## What to Archive / Clean

Move (do not delete yet) into `archive/`:

- Root-level junk: `=0.7.0`, `=0.8.0`, `1000`, `G0DM0D3` (submodule noise)
- One-off fix scripts: `_add_bot_*.py`, `_fix_bot_*.py`
- Duplicate / backup files: `src/web_interface.py.bak`, old STATUS copies
- Experimental reports that are no longer the source of truth
- Temporary bots: `bots/.hermes-tmp.*`

Keep only production-relevant scripts at root (`start_all.py`, PowerShell helpers if still used).

## Import Rules (after cleanup)

- Prefer absolute imports from `src.*`
- Trade cycle stays self-contained under `work/agents/trade_cycle`
- No code outside `src/` and `work/` should be imported by the main runtime
- Runtime data (SQLite, logs, state JSON) lives under `work/data/` or `data/` and is gitignored

## Service Ports (canonical)

| Service | Port |
|---------|------|
| Ollama | 11434 |
| AI Router | 11435 |
| Orchestrator | 11436 |
| Web Dashboard | 5000 |
| Cloud Desktop | 5001 |
| Integrations | 8080 |
| Kanban (if used) | 5103 |

## Health Contract

Every long-running service should answer a simple health check (file, HTTP, or function) so `system_health.py` and the watchdog can report status uniformly.

## Next Cleanup Steps (manual or PR)

1. Create `archive/` and move listed junk.
2. Add `src/__init__.py` if missing.
3. Split giant `bot.py` into packages when time allows.
4. Add `tests/test_trade_cycle.py` and `tests/test_system_health.py`.
5. Add `docker-compose.yml` for one-command demo.

---

Updated: 2026-10-30 — branch `cleanup-improve-v1`
