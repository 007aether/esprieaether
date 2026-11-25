#!/usr/bin/env python3
"""
SMART ROUTER — Yqarrer ach men engine ykhdem
"""

import re


# Security keywords → Metasploit
SECURITY_KEYWORDS = [
    "scan", "exploit", "vulnerability", "cve", "payload",
    "metasploit", "msf", "session", "shell", "reverse",
    "port", "nmap", "recon", "reconnaissance", "pentest",
    "penetration", "attack", "target", "victim", "backdoor",
    "meterpreter", "bypass", "privesc", "privilege escalation",
    "s7ab", "tkhreq", "9nt", "sécurité", "hack"
]

# Reasoning keywords → DeepSeek
REASONING_KEYWORDS = [
    "why", "how", "explain", "analyze", "step by step",
    "compare", "solve", "calculate", "math", "logic",
    "3lach", "kifach", "chrah", "fassar", "9aren", "7ell"
]

# Creative keywords → Dolphin
CREATIVE_KEYWORDS = [
    "write", "story", "poem", "creative", "imagine",
    "design", "art", "song", "novel", "script",
    "ktb", "ch3r", "9issa", "khayal"
]

# Code keywords → Cloud Code
CODE_KEYWORDS = [
    "code", "function", "script", "program", "debug",
    "compile", "error", "bug", "python", "javascript",
    "kotlin", "bash", "sql", "api", "class"
]

# Planning keywords → Kanban
PLANNING_KEYWORDS = [
    "plan", "goal", "task", "project", "organize",
    "todo", "schedule", "kanban", "workflow", "steps"
]


def route(query):
    """
    Returns: (engine, reason)
    Engines: 'hermes', 'dolphin', 'deepseek', 'metasploit', 'cloud_code', 'kanban'
    """
    q = query.lower()
    
    # Security → Metasploit (highest priority)
    security_score = sum(1 for kw in SECURITY_KEYWORDS if kw in q)
    if security_score >= 1:
        return "metasploit", f"Security keywords detected ({security_score})"
    
    # Code → Cloud Code
    code_score = sum(1 for kw in CODE_KEYWORDS if kw in q)
    if code_score >= 2:
        return "cloud_code", f"Code keywords detected ({code_score})"
    
    # Planning → Kanban
    plan_score = sum(1 for kw in PLANNING_KEYWORDS if kw in q)
    if plan_score >= 2:
        return "kanban", f"Planning keywords detected ({plan_score})"
    
    # Reasoning → DeepSeek
    reason_score = sum(1 for kw in REASONING_KEYWORDS if kw in q)
    if reason_score >= 1 or len(query) > 200:
        return "deepseek", f"Reasoning needed ({reason_score} keywords)"
    
    # Creative → Dolphin
    creative_score = sum(1 for kw in CREATIVE_KEYWORDS if kw in q)
    if creative_score >= 1:
        return "dolphin", f"Creative task ({creative_score} keywords)"
    
    # Default → Hermes (conversation)
    return "hermes", "Default: conversation"
