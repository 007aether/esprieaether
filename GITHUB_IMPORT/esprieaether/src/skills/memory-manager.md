---
description: Cross-agent memory sharing and persistence (MEMORY.md / agent_board.json sync)
name: memory-manager
category: agent-os-evolution
---

# Memory Manager Skill

## Purpose

Cross-agent memory sharing and persistence.
Syncs MEMORY.md + agent_board.json for shared context.

## 🧠 Memory Architecture

### Short-term Memory (Board)
- **File**: `data/agent_board.json`
- **Capacity**: 200 messages
- **Used by**: Agent mesh for conversation history
- **Lifetime**: Until cleaned or overwritten

### Long-term Memory (Vector)
- **File**: `data/vector_memory.db`
- **Type**: SQLite + semantic search
- **Used by**: Ask agent, mesh agents
- **Lifetime**: Persistent

## 🔄 Sync Process

```
Agent → write to board → mesh shares → memory manager persists
```

## 📋 Usage

```python
from src import memory_manager

# Save a memory
memory_manager.save_memory(
    "Agent mesh is healthy",
    context={"agent": "security", "timestamp": "2026-10-20"}
)

# Recall relevant memories
hits = memory_manager.recall(
    "system health",
    limit=5
)
```

## 🛡️ Memory Safety

- **Scope**: agents can only access allowed contexts
- **Cleanup**: old messages removed after 200 limit
- **Audit**: all memory writes logged
