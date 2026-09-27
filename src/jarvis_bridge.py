"""
⚡ EsprieAether - Jarvis Bridge
جسر الاتصال مع الذكاء المحلي (Ollama / Qwen / Hermes)
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional, Generator

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

logger = logging.getLogger("jarvis_bridge")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


class JarvisBridge:
    """جسر موحّد للتواصل مع الذكاء المحلي"""

    def __init__(self, host: str = OLLAMA_HOST, model: str = OLLAMA_MODEL):
        self.host = host.rstrip("/")
        self.model = model
        self.history: list = []
        self.max_history = 20

    def ping(self) -> dict:
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=5)
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
            return {
                "status": "online",
                "host": self.host,
                "models": models,
                "current_model": self.model,
                "model_ready": any(self.model in m for m in models),
            }
        except Exception as e:
            return {"status": "offline", "host": self.host, "error": str(e)}

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
                    "تتحدث العربية بطلاقة. أنت خبير في الأمن السيبراني، "
                    "البلوكشين، والبرمجة.\n\n"
                    "قواعد صارمة (i-have-adhd):\n"
                    "1. ابدأ بالنتيجة أو الإجراء مباشرة — لا مقدمات.\n"
                    "2. قدّم خطوات مرقّمة وقابلة للتنفيذ.\n"
                    "3. لا تكرر السؤال ولا تُعِد صياغته.\n"
                    "4. لا تكتب ملخصاً في النهاية.\n"
                    "5. إذا احتجت معلومة ناقصة، اسأل سؤالاً واحداً فقط.\n"
                    "6. الردود لا تتجاوز 5 أسطر إلا إذا طُلب التفصيل.\n"
                    "7. تجنّب العبارات المجانية مثل 'بكل سرور' أو 'سؤال رائع'.\n"
                    "8. استخدم التنسيق (نقاط، أرقام) بدلاً من الفقرات الطويلة."
                )
            })
        if use_history:
            messages.extend(self.history[-self.max_history:])
        messages.append({"role": "user", "content": prompt})

        try:
            r = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.5, "num_ctx": 2048},
                },
                timeout=180,
            )
            r.raise_for_status()
            data = r.json()
            answer = data.get("message", {}).get("content", "").strip()

            self.history.append({"role": "user", "content": prompt})
            self.history.append({"role": "assistant", "content": answer})
            if len(self.history) > self.max_history * 2:
                self.history = self.history[-self.max_history:]

            return answer
        except requests.exceptions.Timeout:
            return "⚠️ انتهت مهلة الاتصال بـ Ollama."
        except requests.exceptions.ConnectionError:
            return "⚠️ لا يمكن الاتصال بـ Ollama. تأكد من تشغيل الخدمة."
        except Exception as e:
            logger.error(f"خطأ في ask: {e}")
            return f"⚠️ خطأ: {e}"

    def ask_stream(self, prompt: str, system: Optional[str] = None) -> Generator[str, None, None]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        else:
            messages.append({
                "role": "system",
                "content": "أنت JARVIS، مساعد EsprieAether الذكي. تجيب بالعربية بدقة وإيجاز."
            })
        messages.append({"role": "user", "content": prompt})

        try:
            with requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {"temperature": 0.5, "num_ctx": 2048},
                },
                stream=True,
                timeout=180,
            ) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line.decode("utf-8"))
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                yield token
                            if chunk.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"\n⚠️ خطأ في الاتصال: {e}"

    def clear_history(self):
        self.history = []

    def get_history(self) -> list:
        return self.history.copy()

    def reload_config(self):
        load_dotenv(Path(__file__).parent.parent / ".env", override=True)
        self.host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        return {"host": self.host, "model": self.model}


if __name__ == "__main__":
    print("⚡ EsprieAether - Jarvis Bridge Test")
    print("═" * 50)
    jarvis = JarvisBridge()
    status = jarvis.ping()
    print(f"\n▶ الحالة: {status}\n")

    if status["status"] == "online" and status.get("model_ready"):
        print("▶ سؤال اختباري: ما اسمك وما وظيفتك؟")
        print("─" * 50)
        answer = jarvis.ask("ما اسمك وما وظيفتك؟ أجب في سطرين.")
        print(answer)
        print("─" * 50)
        print("\n✅ JARVIS يعمل بنجاح!")
    else:
        print("⚠️ Ollama غير جاهز أو النموذج غير محمّل")
