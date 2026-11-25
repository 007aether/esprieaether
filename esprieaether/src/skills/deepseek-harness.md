---
description: DeepSeek Universal Brain + Skill Expander
name: deepseek-harness
category: agent-os-evolution
---

# DeepSeek Harness Skill

## Purpose

Reverse-engineered from DeepSeek AI harness.
Provides universal brain capabilities and skill expansion.

## 🧠 Universal Brain

The Universal Brain is a centralized AI brain that:
- Routes requests to appropriate models (local/remote)
- Manages context across conversations
- Provides consistent responses

## 🔑 Features

- **Multi-model routing** — Ollama, Colibri, LLM7, Groq
- **Skill expansion** — skills loaded dynamically
- **Context management** — conversation history maintained
- **Fallback** — cloud fallback when local unavailable

## 📋 Usage

```python
from src import deepseek_harness

# Initialize
brain = deepseek_harness.UniversalBrain()

# Ask a question
response = brain.ask(
    "How do I restart the router?",
    model="aether-auto"
)

print(response["answer"])
```

## ⚡ Performance

| Model | Speed | Capability |
|---|---|---|
| qwen2.5:3b | ⭐⭐⭐⭐⭐ | Fast, local |
| gpt-oss:20b | ⭐⭐⭐⭐☆ | Strong |
| aether-evolve | ⭐⭐⭐⭐☆ | Autonomous |

## 🛡️ Safety

- All actions logged to `data/agent_kernel.log`
- Policy validation via Agent Kernel
- Audit trail for every action

