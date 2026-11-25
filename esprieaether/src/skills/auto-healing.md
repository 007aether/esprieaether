---
description: Auto-Healing Supervisor System
name: auto-healing
category: agent-os-evolution
---

# Auto-Healing Skill

## Purpose

Supervisor monitors services (60s interval).
Auto-restarts crashed services. Ensures 24/7 operation.

## 🔧 Supervisor Tasks

- **Health check** — monitor all services every 60s
- **Auto-restart** — restart crashed services automatically
- **Alerting** — send Telegram notifications on failure
- **Recovery** — restore system to healthy state

## 📋 Monitored Services

| Service | Port | Health Check |
|---|---|---|
| Agent Mesh | 11437 | /health endpoint |
| Router | 11435 | /health endpoint |
| Web Interface | 5000 | HTTP 200 |
| Jarvis API | 8000 | /health endpoint |
| Sunna API | 5100 | HTTP 200 |
| Kanban | 5103 | HTTP 200 |
| Jarvis FE | 3000 | HTTP 200 |

## 📖 Usage

```python
from src import agent_kernel

# Check service health
result = agent_kernel.check_service("agent_mesh")
if result["status"] == "down":
    agent_kernel.restart_service("agent_mesh")
```

## 🔑 Key Features

- **Automated recovery** — no human intervention needed
- **Multi-service monitoring** — all services checked every 60s
- **Telegram alerts** — instant notifications on failure
- **Graceful degradation** — system continues on partial failure

