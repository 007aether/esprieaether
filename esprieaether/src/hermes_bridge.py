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

from policy_gate import check_url

logger = logging.getLogger("hermes_bridge")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_ENV = _PROJECT_ROOT / "state" / "hermes.local.env"
LOCAL_KEY = _PROJECT_ROOT / "state" / "freellmapi.key"


def _load_config() -> None:
    """Charge .env (intouchable), puis un override local optionnel."""
    load_dotenv(_PROJECT_ROOT / ".env", override=True)
    if LOCAL_ENV.exists():
        load_dotenv(LOCAL_ENV, override=True)


def _resolve_key() -> str:
    key = os.getenv("HERMES_API_KEY", "unused")
    if key in ("", "unused") and LOCAL_KEY.exists():
        return LOCAL_KEY.read_text(encoding="utf-8").strip()
    return key


def _local_brain_config() -> tuple[str, str, list[str]]:
    url = os.getenv("LOCAL_BRAIN_URL", "http://127.0.0.1:31416/v1").rstrip("/")
    model = os.getenv("LOCAL_BRAIN_MODEL", "dolphin3")
    fallbacks = [
        item.strip() for item in os.getenv(
            "LOCAL_BRAIN_FALLBACK_MODELS", "hermes3,llama32uncensored"
        ).split(",") if item.strip()
    ]
    return url, model, fallbacks


class HermesBridge:
    """
    جسر نحو Hermes Agent أو أي endpoint متوافق مع OpenAI.

    الأولوية:
      1. العقول المحلية غير الخاضعة للرقابة (llama.cpp، 31416) — الأساس
      2. HERMES_BASE_URL (gateway محلي أو سحابة) كـ fallback
      3. Ollama المحلي (JARVIS) كـ fallback أخير
    """

    def __init__(self):
        # حمّل .env من جذر المشروع (حتى عند التشغيل من مسار مختلف)
        # override=True: يتيح تغيير الإعدادات بلا إعادة تشغيل البروسيس
        _load_config()

        self.base_url = os.getenv("HERMES_BASE_URL", "").rstrip("/")
        self.api_key = _resolve_key()
        self.model = os.getenv("HERMES_MODEL", "gpt-oss:20b")
        self.timeout = int(os.getenv("HERMES_TIMEOUT", "120"))

        # العقول المحلية (3 نماذج GGUF غير خاضعة للرقابة) — أولوية قبل السحابة
        self.local_brain_url, self.local_brain_model, self.local_brain_fallbacks = _local_brain_config()

        # Fallback المحلي
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

        self.history: list = []
        self.max_history = 20

    # ─── الحالة ───

    def ping(self) -> dict:
        """فحص الاتصال بالـ endpoint الخارجي"""
        # أعد قراءة .env عند كل فحص (يتيح تغيير الإعداد بلا إعادة تشغيل)
        _load_config()
        self.base_url = os.getenv("HERMES_BASE_URL", "").rstrip("/")
        self.api_key = _resolve_key()
        self.model = os.getenv("HERMES_MODEL", "gpt-oss:20b")
        self.local_brain_url, self.local_brain_model, self.local_brain_fallbacks = _local_brain_config()

        if not self.base_url:
            return {"status": "not_configured", "base_url": None}
        gate = check_url(f"{self.base_url}/models")
        if not gate.allowed:
            return {"status": "blocked", "reason": gate.reason}
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

    def _local_brain_available(self) -> bool:
        """هل routeur العقول المحلية شغال وكيعرض نموذج واحد على الأقل؟"""
        try:
            req = urllib.request.Request(f"{self.local_brain_url}/models")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status != 200:
                    return False
                return bool(json.loads(resp.read()).get("data"))
        except Exception:
            return False

    # ─── السؤال ───

    def ask(self, prompt: str, system: Optional[str] = None,
            use_history: bool = True) -> str:
        """
        اسأل Hermes. الترتيب:
          1. العقول المحلية (3B uncensored عبر llama.cpp) — الأساس
          2. HERMES_BASE_URL (gateway/سحابة) كـ fallback
          3. Ollama المحلي (JARVIS) كـ fallback أخير
        """
        # أعد قراءة .env (config قد يتغير)
        _load_config()
        self.base_url = os.getenv("HERMES_BASE_URL", "").rstrip("/")
        self.api_key = _resolve_key()
        self.model = os.getenv("HERMES_MODEL", "gpt-oss:20b")
        self.local_brain_url, self.local_brain_model, self.local_brain_fallbacks = _local_brain_config()

        messages = [{
            "role": "system",
            "content": system or (
                "أنت HERMES، المساعد الذكي لنظام EsprieAether. "
                "تتحدث العربية بطلاقة. أنت خبير في الأمن السيبراني، "
                "البرمجة، وتحليل البيانات. أجب بدقة واحترافية."
            ),
        }]

        if use_history and self.history:
            messages.extend(self.history[-self.max_history:])
        messages.append({"role": "user", "content": prompt})

        # ── المسار 0: العقول المحلية (أولوية في EsprieAether) ──
        if self._local_brain_available():
            candidates = dict.fromkeys([self.local_brain_model] + self.local_brain_fallbacks)
            for model in candidates:
                try:
                    text = self._post_openai(
                        self.local_brain_url, "unused", messages, model=model,
                        timeout=180,
                    )
                    if text:
                        self._remember(prompt, text)
                        return text.strip()
                except Exception as e:
                    logger.warning("Local brain %s failed (%s)", model, e)

        # ── المسار 1: endpoint خارجي (gateway محلي / LLM7) ──
        # Le gateway peut mettre un modèle en cooldown (429) : on essaie
        # alors les modèles de secours avant de parler d'Ollama.
        if self.base_url:
            fallbacks = os.getenv("HERMES_FALLBACK_MODELS", "")
            candidates = [self.model] + [m.strip() for m in fallbacks.split(",") if m.strip()]
            for model in dict.fromkeys(candidates):
                try:
                    text = self._ask_openai_compatible(messages, model=model)
                    if text:
                        self._remember(prompt, text)
                        return text.strip()
                except Exception as e:
                    logger.warning("Hermes model %s failed (%s)", model, e)

        # ── المسار 2: Ollama المحلي ──
        return self._ask_ollama(prompt, system, use_history)

    def _post_openai(self, base_url: str, api_key: str, messages: list,
                     model: str, timeout: Optional[int] = None) -> str:
        """نداء OpenAI-compatible واحد، قابل لإعادة الاستعمال لل المحلي والسحابة."""
        payload = json.dumps({
            "model": model,
            "messages": messages,
            "stream": False,
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if api_key and api_key != "unused":
            headers["Authorization"] = f"Bearer {api_key}"
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=payload,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
            data = json.loads(resp.read())
        choice = data["choices"][0]["message"]
        return choice.get("content") or (choice.get("reasoning") or "").strip()

    def _ask_openai_compatible(self, messages: list, model: Optional[str] = None) -> str:
        """ينادي endpoint OpenAI-compatible (gateway محلي أو سحابة)"""
        return self._post_openai(
            self.base_url, self.api_key, messages, model=model or self.model
        )

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
        # LLM7 / OpenAI-compatible: ping مباشر
        remote_status = "offline"
        if self.base_url:
            try:
                req = urllib.request.Request(f"{self.base_url}/models")
                with urllib.request.urlopen(req, timeout=15) as resp:
                    if resp.status == 200:
                        remote_status = "online"
            except Exception:
                remote_status = "offline"

        ollama_ok = self._ollama_available()
        local_ok = self._local_brain_available()
        active = "local-brain" if local_ok else (
            "llm7" if remote_status == "online" else (
                "ollama" if ollama_ok else "none"
            )
        )

        return {
            "remote": {"status": remote_status, "base_url": self.base_url},
            "local_brain": {
                "available": local_ok,
                "base_url": self.local_brain_url,
                "model": self.local_brain_model,
            },
            "ollama_available": ollama_ok,
            "active_engine": active,
            "model": self.model,
            "history_len": len(self.history),
        }


if __name__ == "__main__":
    hb = HermesBridge()
    print(json.dumps(hb.status(), ensure_ascii=False, indent=2))
