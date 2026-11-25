#!/usr/bin/env python3
"""
Arabic Support Agent — دعم كامل للغة العربية
=====================================================
دعم كامل للغة العربية في النظام
- توطين الواجهات
- دعم RTL
- إضافة المزيد من المحتوى العربي
- ترجمة الأوامر
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

# Base directory for the project
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
BASE_DIR = PROJECT_DIR  # data/logs is under project root, not src/data

# Data files
STATE_FILE = BASE_DIR / "data" / "arabic_support_state.json"
LOG_FILE = BASE_DIR / "data" / "logs" / "arabic_support.log"
MEMORY_FILE = BASE_DIR / "data" / "memory" / "knowledge_base.json"

class ArabicSupport:
    """وكيل دعم اللغة العربية"""

    def __init__(self):
        self.state = {
            "supported_languages": ["ar", "en"],
            "current_language": "ar",
            "rtl_enabled": True,
            "emoji_support": True,
            "arabic_font": "Segoe UI, Tahoma, Geneva, Verdana, sans-serif",
            "commands": {},
            "translations": {},
            "last_updated": None
        }
        self._ensure_state_file()
        self._log("شstarted وكيل دعم اللغة العربية")

    def _ensure_state_file(self):
        """تأكد من وجود ملف الحالة"""
        import os
        os.makedirs(STATE_FILE.parent, exist_ok=True)
        if not STATE_FILE.exists():
            with open(STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)

    def _log(self, message):
        """سجل الرسالة"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with open(LOG_FILE, 'a') as f:
            f.write(log_msg + "\n")

    def add_command(self, ar_name, en_name, command):
        """
        إضافة أمر جديد مع ترجمة
        """
        if ar_name not in self.state["commands"]:
            self.state["commands"][ar_name] = []
        self.state["commands"][ar_name].append({
            "name": en_name,
            "command": command,
            "translated": True
        })
        self._log(f"📝 أُضيف أمر: {ar_name} ({en_name})")
        self._save_state()

    def add_translation(self, key, arabic_text, english_text=None):
        """إضافة ترجمة"""
        if "translations" not in self.state:
            self.state["translations"] = {}
        if key not in self.state["translations"]:
            self.state["translations"][key] = {
                "ar": arabic_text,
                "en": english_text or arabic_text
            }
        else:
            self.state["translations"][key]["ar"] = arabic_text
        self._log(f"🌐 تمت إضافة ترجمة: {key}")
        self._save_state()

    def set_language(self, lang="ar"):
        """تعيين اللغة"""
        if lang in self.state["supported_languages"]:
            self.state["current_language"] = lang
            self._log(f"🌐 تم تغيير اللغة إلى: {lang}")
            self._save_state()
            return True
        return False

    def get_command(self, key):
        """حصول على أمر مع الترجمة"""
        if key in self.state.get("commands", {}):
            return self.state["commands"][key]
        return None

    def get_translation(self, key):
        """حصول على ترجمة"""
        if key in self.state.get("translations", {}):
            return self.state["translations"][key]
        return None

    def set_rtl(self, enabled=True):
        """تفعيل/إلغاء تفعيل RTL"""
        self.state["rtl_enabled"] = enabled
        self._log(f"🔄 تم تعيين RTL إلى: {enabled}")
        self._save_state()

    def set_arabic_font(self, font):
        """تعيين الخط العربي"""
        self.state["arabic_font"] = font
        self._log(f"🔤 تم تعيين الخط العربي: {font}")
        self._save_state()

    def add_emoji_support(self, enabled=True):
        """تفعيل/إلغاء تفعيل الدعم بالأ emoji"""
        self.state["emoji_support"] = enabled
        self._log(f"😊emoji_support: {enabled}")
        self._save_state()

    def get_summary(self):
        """حصول على ملخص"""
        return {
            "current_language": self.state["current_language"],
            "rtl_enabled": self.state["rtl_enabled"],
            "emoji_support": self.state["emoji_support"],
            "arabic_font": self.state["arabic_font"],
            "supported_languages": self.state["supported_languages"],
            "commands_count": len(self.state.get("commands", {})),
            "translations_count": len(self.state.get("translations", {})),
            "last_updated": self.state.get("last_updated")
        }

    def _save_state(self):
        """حفظ الحالة"""
        self.state["last_updated"] = datetime.now().isoformat()
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def run(self):
        """تشغيل الوسيط"""
        self._log("شstarted وكيل الدعم العربي")
        self._log("✅ ودعم اللغة العربية مُفعّل")
        summary = self.get_summary()
        self._log(f"📋 الملخص: {summary}")


if __name__ == "__main__":
    support = ArabicSupport()
    support.run()
