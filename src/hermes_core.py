#!/usr/bin/env python3
"""
ESPRIEAETHER — Hermes Core
The sovereign brain. Routes to best available brain.
"""

import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Cloud brains (no key required for llm7)
CLOUD_BRAINS = [
    {
        "name": "llm7-fast",
        "url": "https://api.llm7.io/v1/chat/completions",
        "key": "ollama-local",
        "model": "mistral-Nemo-Instruct-2407",
        "min_interval": 6.5,
    },
    {
        "name": "llm7-big",
        "url": "https://api.llm7.io/v1/chat/completions",
        "key": "ollama-local",
        "model": "gpt-oss:20b",
        "min_interval": 6.5,
    },
]

# Local brain (Ollama) - may be broken
LOCAL_BRAIN = {
    "name": "ollama-local",
    "url": os.getenv("OLLAMA_URL", "http://127.0.0.1:11435/v1/chat/completions"),
    "key": None,
    "model": os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
    "min_interval": 0.0,
}

class HermesCore:
    def __init__(self):
        self.memory_file = BASE_DIR / "data" / "hermes_memory.json"
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.memory = self._load_memory()
        self.session_start = datetime.now(timezone.utc).isoformat()
        self._last_request = {}
    
    def _load_memory(self):
        if self.memory_file.exists():
            try:
                return json.loads(self.memory_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"sessions": [], "facts": {}, "preferences": {}}
    
    def _save_memory(self):
        self.memory_file.write_text(
            json.dumps(self.memory, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    
    def remember(self, key, value):
        self.memory["facts"][key] = {
            "value": value,
            "stored_at": datetime.now(timezone.utc).isoformat()
        }
        self._save_memory()
    
    def recall(self, key):
        return self.memory.get("facts", {}).get(key, {}).get("value")
    
    def _call_brain(self, brain, messages, timeout=60):
        """Call a single brain."""
        payload = {
            "model": brain["model"],
            "messages": messages,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if brain.get("key"):
            headers["Authorization"] = f"Bearer {brain['key']}"
        
        req = urllib.request.Request(
            brain["url"],
            data=data,
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            result = json.loads(r.read())
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content
        return None
    
    def think(self, prompt: str) -> str:
        """Main thinking — tries cloud first, then local."""
        messages = [
            {"role": "system", "content": self._system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        # Try cloud brains first (llm7 is free, no key needed)
        for brain in CLOUD_BRAINS:
            try:
                content = self._call_brain(brain, messages)
                if content:
                    self._log_session(prompt, content, brain["name"])
                    return content
            except Exception as e:
                continue
        
        # Fallback to local Ollama
        try:
            content = self._call_brain(LOCAL_BRAIN, messages, timeout=90)
            if content:
                self._log_session(prompt, content, LOCAL_BRAIN["name"])
                return content
        except Exception as e:
            pass
        
        return "[Hermes: no brain available — cloud and local failed]"
    
    def _system_prompt(self) -> str:
        return """أنت Hermes — العقل الرئيسي لـ ESPRIEAETHER.
أنت مسؤول، مباشر، وذي عقلية تقنية.
تتحدث العربية بطلاقة.
لا تكرر السؤال. لا تقدم شروعات غير ضرورية.
إذا عرفت المهمة، نفذها مباشرة."""
    
    def _log_session(self, prompt, response, model):
        self.memory["sessions"].append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "prompt": prompt[:200],
            "response_preview": response[:200]
        })
        if len(self.memory["sessions"]) > 100:
            self.memory["sessions"] = self.memory["sessions"][-100:]
        self._save_memory()
    
    def status(self) -> dict:
        return {
            "brain": "Hermes",
            "mode": "cloud-first",
            "cloud_brains": len(CLOUD_BRAINS),
            "local_brain": LOCAL_BRAIN["name"],
            "ollama_url": LOCAL_BRAIN["url"],
            "memory_items": len(self.memory.get("facts", {})),
            "sessions": len(self.memory.get("sessions", [])),
            "uptime": datetime.now(timezone.utc).isoformat()
        }

# Singleton
_hermes = None

def get_hermes():
    global _hermes
    if _hermes is None:
        _hermes = HermesCore()
    return _hermes
