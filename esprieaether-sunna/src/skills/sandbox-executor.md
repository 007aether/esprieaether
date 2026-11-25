---
description: Sandbox execution environment for agent actions (isolated process boundaries)
name: sandbox-executor
category: agent-os-evolution
---

# Sandbox Executor Skill

Part of ESPRIEAETHER Agent OS Evolution (Next Phase).
Provides sandbox execution capabilities for autonomous operation.

## 🔒 Safety Sandbox

The sandbox executes agent actions in isolated processes:

- **File sandbox**: agents can read/write only in ALLOWED_DIRS
- **Network sandbox**: no outbound connections without approval
- **Memory sandbox**: agents can only access allowed memory contexts
- **Process sandbox**: no long-running processes without approval

## 🔑 Permissions

| Permission | Level | Description |
|---|---|---|
| `read` | `public` | Read any file |
| `write` | `private` | Write to private files |
| `execute` | `sandboxed` | Execute commands in sandbox |
| `network` | `restricted` | Limited network access |
| `admin` | `owner` | Full access (owner only) |

## 📋 Usage

```python
from skills.sandbox_executor import SandboxExecutor

sandbox = SandboxExecutor(
    allowed_dirs=["data/", "src/"],
    allowed_commands=["python", "npm", "git"],
    timeout=30
)

# Execute with permission
result = sandbox.execute(
    command=["python", "src/test.py"],
    permission="sandboxed",
    context="agent_os_kernel"
)
```

## 🛡️ Security Policy

- No destructive commands without approval
- No network access without explicit permission
- No writing to system directories
- All actions logged to `data/agent_kernel.log`

