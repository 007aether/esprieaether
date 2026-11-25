---
description: ESPRIEAETHER Universal Brain Skill (Reverse-Engineered)
name: universal-brain
category: agent-os-evolution
---

# Universal Brain Skill

## Purpose

This skill provides universal brain capabilities (like DeepSeek Harness):

- Skill expansion (auto-generate new skills from experience)
- Travel mode (online/offline brain switching)
- Cross-agent memory sharing
- 24/7 autonomous monitoring

## 🔑 Features

- **Multi-model routing** — Ollama, Colibri, LLM7, Groq
- **Skill expansion** — skills loaded dynamically
- **Context management** — conversation history maintained
- **Fallback** — cloud fallback when local unavailable
- **Cross-agent sharing** — memory shared across mesh

## 📋 Usage

```python
from src import universal_brain

# Initialize
brain = universal_brain.UniversalBrain()

# Ask a question
response = brain.ask("How do I restart the router?")
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

