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
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

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
        # حمّل .env من جذر المشروع (حتى عند التشغيل من مسار مختلف)
        # override=True: يتيح تغيير الإعدادات بلا إعادة تشغيل البروسيس
        load_dotenv(Path(__file__).parent.parent / ".env", override=True)

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
        # أعد قراءة .env عند كل فحص (يتيح تغيير الإعداد بلا إعادة تشغيل)
        load_dotenv(Path(__file__).parent.parent / ".env", override=True)
        self.base_url = os.getenv("HERMES_BASE_URL", "").rstrip("/")
        self.api_key = os.getenv("HERMES_API_KEY", "unused")
        self.model = os.getenv("HERMES_MODEL", "gpt-oss:20b")

        if not self.base_url:
            return {"status": "not_configured", "base_url": None}
        # جرّب مرتين (الـ proxy المحلي قد يكون بطيئة في أول نداء)
        last_err = None
        for attempt in range(2):
            try:
                req = urllib.request.Request(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read())
                models = [m.get("id") for m in data.get("data", [])]
                return {
                    "status": "online",
                    "base_url": self.base_url,
                    "model": self.model,
                    "model_ready": any(self.model in (m or "") for m in models),
                    "models_count": len(models),
                }
            except Exception as e:
                last_err = e
                if attempt == 0:
                    time.sleep(2)
        return {"status": "offline", "error": str(last_err)}

    def _ollama_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.ollama_host}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    # ─── السؤال ───

    def ask(self, prompt: str, system: Optional[str] = None,
            use_history: bool = True) -> str:
        """
        اسأل Hermes. إذا فشل/غير مُعد، يرجع تلقائياً لـ Ollama المحلي.
        """
        # أعد قراءة .env (config قد يتغير)
        load_dotenv(Path(__file__).parent.parent / ".env", override=True)
        self.base_url = os.getenv("HERMES_BASE_URL", "").rstrip("/")
        self.api_key = os.getenv("HERMES_API_KEY", "unused")
        self.model = os.getenv("HERMES_MODEL", "gpt-oss:20b")

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
                payload = json.dumps({
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                }).encode("utf-8")
                req = urllib.request.Request(
                    f"{self.base_url}/chat/completions",
                    data=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read())
                text = data["choices"][0]["message"].get("content") or ""
                if not text:
                    text = (data["choices"][0]["message"].get("reasoning") or "").strip()
                self._remember(prompt, text)
                return text.strip()
            except urllib.error.URLError as e:
                logger.warning("Hermes failed (%s) — falling back to Ollama", e)
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
            payload = json.dumps({
                "model": self.ollama_model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.7},
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{self.ollama_host}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read())
            text = data.get("message", {}).get("content", "")
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
