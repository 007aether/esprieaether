# AGENTS.md — EsprieAether Operator Topology

This repository is operated by a multi-harness agent system. Each harness has a
distinct role and they share the ECC substrate (skills, hooks, memory vault).

## Harness Roles

| Harness | Role | Config | Skills Source |
|---|---|---|---|
| **Hermes** | Operator shell (front door) | `~/.hermes/config.yaml` | `~/.hermes/skills/` + ECC external |
| **ECC** | Reusable workflow substrate | `.ecc/` | `ECC_repo/skills/` (311) |
| **Sunna** | Team workspace (veille, bots) | `Sunna-Equipe-Industrial/` | local bots |
| **DSH** | DeepSeek Harness (desktop UI + headless) | `~/.dsh/profiles/` | aether router |
| **EsprieAether** | Local AI stack (router, orch, bots, robots) | `src/` | 60 robots + 7 agents |

## Architecture

```
Telegram / CLI / TUI
        ↓
      Hermes
        ↓
 ECC skills + hooks + memory vault
        ↓
 EsprieAether router (Ollama + LLM7 + Groq + MiniMax)
        ↓
 60 robots · 7 agents · Telegram bot · Cloud desktop
        ↓
 Sunna team · DSH headless · GitHub · research APIs
```

## Services (24/7, watchdog-managed)

| Service | Port | Purpose |
|---|---|---|
| Ollama | 11434 | Local LLM (qwen2.5:3b) |
| Aether Router | 11435 | 5 brains, 12 virtual models, 7 agents |
| Orchestrator | 11436 | 7-agent orchestration (OpenAI-compatible) |
| Web Interface | 5000 | Flask dashboard |
| Cloud Desktop | 5001 | Remote access + group + SSH tunnel |
| Telegram Bot | — | 50+ commands |
| Watchdog | — | Self-healing (restarts dead services) |
| TraffMonetizer | — | Bandwidth sharing (24/7) |
| GitHub Desktop | — | Git GUI |

## ECC Integration

- **Skills**: 311 ECC skills loaded via `~/.hermes/config.yaml` → `skills.external_dirs`
- **Agents**: 71 ECC agents in `~/.hermes/agents/`
- **Commands**: 97 ECC commands in `~/.hermes/commands/`
- **Hooks**: ECC hooks in `~/.hermes/hooks/`
- **Memory Vault**: `.ecc/memory/` — shared context across harnesses

## Memory Vault Rules

- Markdown files are the source of truth
- Every entry is `trust: "unreviewed"` until promoted
- Writes are create-only (never overwrite an existing memory ID)
- Credential shapes and private keys are rejected before writing

## Shared Memory Across Harnesses

Initialize the vault from the repository that the agents share:

```bash
ecc memory init --scope project --scope team
```

- `project` — repo-local state
- `team` — memories a human inspects before committing
- `user` — private operator context (explicit request only)

## Handoff Protocol

A Hermes-to-Codex (or DSH) handoff without putting the body in the process list:

```bash
printf '%s\n' 'Research is complete. Verify the cited sources and implement the parser.' | \
  ecc memory handoff \
    --from hermes \
    --target codex \
    --title "Implement the research parser" \
    --tag research \
    --stdin
```
