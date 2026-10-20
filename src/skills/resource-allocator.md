---
description: Resource allocation and monitoring for system components
name: resource-allocator
category: agent-os-evolution
---

# Resource Allocator Skill

## Purpose

Manages system resources (CPU, RAM, disk, network).
Provides real-time monitoring and allocation control.

## 📊 Resource Monitor

| Resource | Source | Interval |
|---|---|---|
| CPU | psutil | 5s |
| RAM | psutil | 5s |
| Disk | psutil | 30s |
| Network | psutil | 10s |
| Services | systemctl | 60s |

## 🔑 Features

- **Real-time monitoring** — live resource usage
- **Threshold alerts** — notify when resources exceed limits
- **Auto-scaling** — adjust resources based on load
- **Report generation** — daily resource report

## 📖 Usage

```python
from src import resource_allocator

# Get current usage
usage = resource_allocator.get_usage()
print(f"CPU: {usage['cpu']}%")
print(f"RAM: {usage['ram']}%")

# Set threshold
resource_allocator.set_threshold("cpu", 80)
```

## 📊 Report Format

```
📊 Resource Report
• CPU: 45%
• RAM: 62%
• Disk: 34%
• Network: 12 Mbps
```

