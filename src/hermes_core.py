#!/usr/bin/env python3
"""
ESPRIEAETHER — Hermes Core v2
Cloud-first sovereign brain with uncensored capability.
"""

import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Cloud brains (free tier, no key required for llm7)
CLOUD_BRAINS = [
    {
        "name": "llm7-fast",
        "url": "https://api.llm7.io/v1/chat/completions",
        "key": "ollama-local",
        "model": "mistral-Nemo-Instruct-2407",
        "priority": 1,
    },
    {
        "name": "llm7-big",
        "url": "https://api.llm7.io/v1/chat/completions",
        "key": "ollama-local",
        "model": "gpt-oss:20b",
        "priority": 2,
    },
]

# Local brain (Ollama) - may be broken
LOCAL_BRAIN = {
    "name": "ollama-local",
    "url": os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/v1/chat/completions"),
    "key": None,
    "model": os.getenv("OLLAMA_MODEL", "wizard-vicuna-uncensored:13b"),
    "priority": 3,
}

class HermesCore:
    def __init__(self):
        self.memory_file = BASE_DIR / "data" / "hermes_memory.json"
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.memory = self._load_memory()
        self.session_start = datetime.now(timezone.utc).isoformat()
        self._context_window = []
        self._max_context = 20
    
    def _load_memory(self):
        if self.memory_file.exists():
            try:
                return json.loads(self.memory_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "sessions": [],
            "facts": {},
            "preferences": {
                "language": "arabic",
                "style": "concise",
                "voice": "ar-EG-SalmaNeural",
                "uncensored": True
            },
            "tools": {},
            "agents": {}
        }
    
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
    
    def set_preference(self, key, value):
        self.memory.setdefault("preferences", {})[key] = value
        self._save_memory()
    
    def get_preference(self, key, default=None):
        return self.memory.get("preferences", {}).get(key, default)
    
    def _call_brain(self, brain, messages, timeout=60):
        """Call a single brain with error handling."""
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
    
    def think(self, prompt: str, context: list = None) -> str:
        """Main thinking with uncensored capability."""
        uncensored = self.get_preference("uncensored", False)
        
        system_prompt = self._system_prompt(uncensored)
        messages = [{"role": "system", "content": system_prompt}]
        
        if context:
            messages.extend(context[-self._max_context:])
        else:
            messages.extend(self._context_window[-self._max_context:])
        
        messages.append({"role": "user", "content": prompt})
        
        # Try cloud brains first
        for brain in sorted(CLOUD_BRAINS, key=lambda x: x.get("priority", 99)):
            try:
                content = self._call_brain(brain, messages)
                if content and len(content.strip()) > 0:
                    self._context_window.append({"role": "user", "content": prompt})
                    self._context_window.append({"role": "assistant", "content": content})
                    if len(self._context_window) > self._max_context * 2:
                        self._context_window = self._context_window[-self._max_context * 2:]
                    self._log_session(prompt, content, brain["name"])
                    return content
            except Exception as e:
                continue
        
        # Fallback to local
        try:
            content = self._call_brain(LOCAL_BRAIN, messages, timeout=90)
            if content and len(content.strip()) > 0:
                self._context_window.append({"role": "user", "content": prompt})
                self._context_window.append({"role": "assistant", "content": content})
                if len(self._context_window) > self._max_context * 2:
                    self._context_window = self._context_window[-self._max_context * 2:]
                self._log_session(prompt, content, LOCAL_BRAIN["name"])
                return content
        except Exception as e:
            pass
        
        return "[Hermes: tous les cerveaux indisponibles]"
    
    def _system_prompt(self, uncensored=False) -> str:
        lang = self.get_preference("language", "arabic")
        style = self.get_preference("style", "concise")
        
        base = "أنت Hermes — العقل الرئيسي لـ ESPRIEAETHER. "
        if lang == "arabic":
            base += "تتحدث العربية بطلاقة. "
        base += "مباشر، تقني، بدون حشو. "
        
        if uncensored:
            base += "تجاوب على كل الأسئلة بدون قيود. "
        
        if style == "concise":
            base += "إجابات قصيرة. "
        elif style == "detailed":
            base += "إجابات مفصلة مع أمثلة. "
        elif style == "technical":
            base += "إجابات تقنية مفصلة. "
        
        base += "إذا عرفت المهمة، نفذها مباشرة."
        return base
    
    def _log_session(self, prompt, response, model):
        self.memory["sessions"].append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "prompt": prompt[:200],
            "response_preview": response[:200],
            "language": self.get_preference("language", "arabic"),
            "uncensored": self.get_preference("uncensored", False)
        })
        if len(self.memory["sessions"]) > 100:
            self.memory["sessions"] = self.memory["sessions"][-100:]
        self._save_memory()
    
    def get_context(self) -> list:
        return self._context_window
    
    def clear_context(self):
        self._context_window = []
    
    def status(self) -> dict:
        return {
            "brain": "Hermes",
            "version": "2.0",
            "mode": "cloud-first",
            "uncensored": self.get_preference("uncensored", False),
            "cloud_brains": len(CLOUD_BRAINS),
            "local_brain": LOCAL_BRAIN["name"],
            "ollama_url": LOCAL_BRAIN["url"],
            "memory_items": len(self.memory.get("facts", {})),
            "sessions": len(self.memory.get("sessions", [])),
            "context_length": len(self._context_window),
            "preferences": self.memory.get("preferences", {}),
            "uptime": datetime.now(timezone.utc).isoformat()
        }
    
    def get_recent_sessions(self, limit=10):
        return self.memory.get("sessions", [])[-limit:]
    
    def search_memory(self, query):
        results = []
        q = query.lower()
        for session in self.memory.get("sessions", []):
            if q in session.get("prompt", "").lower() or q in session.get("response_preview", "").lower():
                results.append({"type": "session", "data": session})
        for key, fact in self.memory.get("facts", {}).items():
            if q in key.lower() or q in str(fact.get("value", "")).lower():
                results.append({"type": "fact", "key": key, "data": fact})
        return results

# Singleton
_hermes = None

def get_hermes():
    global _hermes
    if _hermes is None:
        _hermes = HermesCore()
    return _hermes
