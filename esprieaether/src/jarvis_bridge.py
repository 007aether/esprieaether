# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether - Jarvis Bridge

جسر الاتصال مع الذكاء المحلي. Consigne J88 : une seule adresse locale
(:31416, routeur OpenAI-compatible), un seul timeout partagé, et un seul
retry prudent quand le routeur renvoie 429 (slot occupé). Aucun secret,
aucun appel sortant, aucune réponse inventée.
"""
import json
import logging
import os
import time
from pathlib import Path
from typing import Generator, Optional

import requests
from dotenv import load_dotenv

from egress_guard import assert_loopback_url

load_dotenv(Path(__file__).parent.parent / ".env")

# L'ancien OLLAMA_HOST du .env pointait vers :11434 (arrêté) : il n'est plus
# utilisé. Pour un test explicite, JARVIS_BRIDGE_HOST peut surcharger l'adresse.
DEFAULT_HOST = "http://127.0.0.1:31416"
DEFAULT_MODEL = "dolphin3"
REQUEST_TIMEOUT = float(os.getenv("ESPRIE_LOCAL_TIMEOUT", "120"))
MAX_RETRIES = 1
MAX_RETRY_WAIT = 5.0
LOCAL_HOST = assert_loopback_url(os.getenv("JARVIS_BRIDGE_HOST", DEFAULT_HOST))
LOCAL_MODEL = os.getenv("JARVIS_BRIDGE_MODEL", DEFAULT_MODEL)

logger = logging.getLogger("jarvis_bridge")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


class JarvisBridge:
    """جسر موحّد للتواصل مع الذكاء المحلي"""

    def __init__(self, host: str = LOCAL_HOST, model: str = LOCAL_MODEL):
        self.host = assert_loopback_url(host)
        self.model = model
        self.history: list = []
        self.max_history = 20

    def ping(self) -> dict:
        try:
            r = requests.get(f"{self.host}/v1/models", timeout=5)
            r.raise_for_status()
            models = [m.get("id", "") for m in r.json().get("data", [])]
            return {
                "status": "online",
                "host": self.host,
                "models": models,
                "current_model": self.model,
                "model_ready": any(self.model == m for m in models),
            }
        except Exception as exc:
            return {"status": "offline", "host": self.host, "error": str(exc)}

    @staticmethod
    def _retry_delay(response: requests.Response) -> float:
        try:
            return min(MAX_RETRY_WAIT, max(0.0, float(response.headers.get("Retry-After", "1"))))
        except (TypeError, ValueError):
            return 1.0

    def ask(self, prompt: str, system: Optional[str] = None,
            use_history: bool = True) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        else:
            messages.append({
                "role": "system",
                "content": (
                    "أنت JARVIS، المساعد الذكي لنظام EsprieAether. "
                    "تتحدث العربية بطلاقة وبلغة تقنية واضحة. أنت خبير في الأمن السيبراني، "
                    "الذكاء الاصطناعي، البرمجة، وتحليل البيانات. "
                    "أجب بدقة واحترافية وباختصار مفيد."
                ),
            })

        if use_history and self.history:
            messages.extend(self.history[-self.max_history:])

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 512,
        }

        try:
            for attempt in range(MAX_RETRIES + 1):
                try:
                    r = requests.post(
                        f"{self.host}/v1/chat/completions",
                        json=payload,
                        timeout=REQUEST_TIMEOUT,
                    )
                    if r.status_code == 429 and attempt < MAX_RETRIES:
                        time.sleep(self._retry_delay(r))
                        continue
                    r.raise_for_status()
                    data = r.json()
                    response_text = data["choices"][0]["message"]["content"]
                    break
                except requests.exceptions.HTTPError as exc:
                    if exc.response is not None and exc.response.status_code == 429:
                        return "⚠️ الذكاء المحلي مشغول الآن. أعد المحاولة بعد قليل."
                    return f"⚠️ خطأ من النموذج المحلي: {exc.response.status_code if exc.response else 'unknown'}"
        except requests.exceptions.Timeout:
            logger.error("Timeout after %.0f seconds", REQUEST_TIMEOUT)
            return f"⚠️ انتهت المهلة ({REQUEST_TIMEOUT:.0f} ثانية). قلّل طول السؤال."
        except requests.exceptions.ConnectionError:
            logger.error("Connection error")
            return "⚠️ فشل الاتصال بالدماغ المحلي :31416. تأكد من تشغيل ESPRIEATHER 24/7."
        except requests.exceptions.RequestException as exc:
            logger.error("Request error: %s", exc)
            return f"⚠️ خطأ في الطلب: {exc}"
        except (KeyError, IndexError, TypeError, ValueError):
            return "⚠️ ردّ غير صالح من النموذج المحلي."

        self.history.append({"role": "user", "content": prompt})
        self.history.append({"role": "assistant", "content": response_text})
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-self.max_history * 2:]
        return response_text.strip()

    def stream(self, prompt: str, system: Optional[str] = None) -> Generator[str, None, None]:
        """.diffusion locale : même route, même timeout, sans clé."""
        messages = ([{"role": "system", "content": system or "أجب بالدارجة."}]
                    if system else [])
        messages.append({"role": "user", "content": prompt})
        try:
            with requests.post(
                f"{self.host}/v1/chat/completions",
                json={"model": self.model, "messages": messages, "stream": True},
                stream=True, timeout=REQUEST_TIMEOUT,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data:"):
                        continue
                    chunk = line[5:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        delta = json.loads(chunk)["choices"][0]["delta"].get("content", "")
                    except (ValueError, KeyError, IndexError):
                        continue
                    if delta:
                        yield delta
        except requests.exceptions.RequestException as exc:
            logger.error("Stream error: %s", exc)
            yield "⚠️ فشل البث من النموذج المحلي."


if __name__ == "__main__":
    bridge = JarvisBridge()
    print(bridge.ping())
