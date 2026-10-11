# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether - Hermes Bridge Agent
يربط EsprieAether بمحرك Hermes Agent (أو أي OpenAI-compatible endpoint).
يسمح باستخدام موديلات سحابية قوية (Claude, GPT, Gemini, Qwen...)
كبديل/احتياطي عندما يكون JARVIS المحلي (Ollama) offline أو ضعيف.
"""

import os
import json
import logging
import time
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger("hermes_bridge")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


class HermesBridge:
    """
    جسر نحو Hermes Agent أو أي endpoint متوافق مع OpenAI.

    الأولوية:
      1. HERMES_BASE_URL (endpoint خارجي — سحابة أو gateway محلي)
      2. Ollama المحلي (JARVIS) كـ fallback تلقائي
    """

    def __init__(self):
        self.base_url = os.getenv("HERMES_BASE_URL", "").rstrip("/")
        self.api_key = os.getenv("HERMES_API_KEY", "unused")
        self.model = os.getenv("HERMES_MODEL", "gpt-oss:20b")
        self.timeout = int(os.getenv("HERMES_TIMEOUT", "120"))

        # Fallback المحلي
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

        self.history: list = []
        self.max_history = 20

    # ─── الحالة ───

    def ping(self) -> dict:
        """فحص الاتصال بالـ endpoint الخارجي"""
        if not self.base_url:
            return {"status": "not_configured", "base_url": None}
        try:
            r = requests.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            if r.status_code == 200:
                models = [m.get("id") for m in r.json().get("data", [])]
                return {
                    "status": "online",
                    "base_url": self.base_url,
                    "model": self.model,
                    "model_ready": any(self.model in (m or "") for m in models),
                    "models_count": len(models),
                }
            return {"status": "error", "code": r.status_code}
        except Exception as e:
            return {"status": "offline", "error": str(e)}

    def _ollama_available(self) -> bool:
        try:
            r = requests.get(f"{self.ollama_host}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    # ─── السؤال ───

    def ask(self, prompt: str, system: Optional[str] = None,
            use_history: bool = True) -> str:
        """
        اسأل Hermes. إذا فشل/غير مُعد، يرجع تلقائياً لـ Ollama المحلي.
        """
        messages = [{
            "role": "system",
            "content": system or (
                "أنت HERMES، المحرك السحابي لنظام EsprieAether. "
                "تتحدث العربية بطلاقة. أنت خبير في الأمن السيبراني، "
                "البرمجة، وتحليل البيانات. أجب بدقة واحترافية."
            ),
        }]

        if use_history and self.history:
            messages.extend(self.history[-self.max_history:])
        messages.append({"role": "user", "content": prompt})

        # ── المسار 1: endpoint خارجي (Hermes / gateway) ──
        if self.base_url:
            try:
                r = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                    },
                    timeout=self.timeout,
                )
                r.raise_for_status()
                text = r.json()["choices"][0]["message"]["content"]
                self._remember(prompt, text)
                return text.strip()
            except requests.exceptions.Timeout:
                logger.warning("Hermes timeout — falling back to Ollama")
            except Exception as e:
                logger.warning("Hermes failed (%s) — falling back to Ollama", e)

        # ── المسار 2: Ollama المحلي ──
        return self._ask_ollama(prompt, system, use_history)

    def _ask_ollama(self, prompt: str, system: Optional[str],
                    use_history: bool) -> str:
        if not self._ollama_available():
            return "⚠️ لا يوجد محرك متاح: HERMES_BASE_URL غير مُعد و Ollama offline."

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        else:
            messages.append({
                "role": "system",
                "content": "أنت JARVIS المحلي لنظام EsprieAether. أجب بالعربية.",
            })
        if use_history and self.history:
            messages.extend(self.history[-self.max_history:])
        messages.append({"role": "user", "content": prompt})

        try:
            r = requests.post(
                f"{self.ollama_host}/api/chat",
                json={
                    "model": self.ollama_model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.7},
                },
                timeout=180,
            )
            r.raise_for_status()
            text = r.json().get("message", {}).get("content", "")
            self._remember(prompt, text)
            return text.strip()
        except Exception as e:
            logger.error("Ollama failed: %s", e)
            return f"⚠️ فشل المحرك المحلي أيضاً: {e}"

    def _remember(self, prompt: str, response: str):
        self.history.append({"role": "user", "content": prompt})
        self.history.append({"role": "assistant", "content": response})
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-self.max_history * 2:]

    def clear_history(self):
        self.history = []

    # ─── أدوات مساعدة ───

    def status(self) -> dict:
        """تقرير حالة كامل"""
        remote = self.ping()
        return {
            "remote": remote,
            "ollama_available": self._ollama_available(),
            "active_engine": "hermes" if remote.get("status") == "online" else (
                "ollama" if self._ollama_available() else "none"
            ),
            "model": self.model,
            "history_len": len(self.history),
        }


if __name__ == "__main__":
    hb = HermesBridge()
    print(json.dumps(hb.status(), ensure_ascii=False, indent=2))
