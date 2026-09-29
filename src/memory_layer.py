# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether - Semantic Memory
طبقة الذاكرة الدلالية
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

BASE_DIR = Path.home() / "AETHER_V8"
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("memory")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

MEMORY_FILE = BASE_DIR / "semantic_memory.json"


class SemanticMemory:
    """الذاكرة الدلالية"""

    def __init__(self):
        self.memory = self._load_memory()

    def _load_memory(self) -> dict:
        if MEMORY_FILE.exists():
            try:
                return json.loads(MEMORY_FILE.read_text())
            except Exception:
                pass
        return {
            "facts": [],       # حقائق دائمة
            "experiences": [],  # تجارب
            "patterns": [],    # أنماط
            "created_at": datetime.now().isoformat(),
        }

    def _save_memory(self):
        MEMORY_FILE.write_text(
            json.dumps(self.memory, indent=2, ensure_ascii=False)
        )

    # ─────────────────────────────────────
    #  تخزين
    # ─────────────────────────────────────
    def remember_fact(self, key: str, value: str, importance: float = 0.5):
        """تخزين حقيقة"""
        # حذف القديمة
        self.memory["facts"] = [
            f for f in self.memory["facts"] if f["key"] != key
        ]
        self.memory["facts"].append({
            "key": key,
            "value": value,
            "importance": importance,
            "timestamp": datetime.now().isoformat(),
        })
        # احتفظ بأهم 100
        self.memory["facts"] = sorted(
            self.memory["facts"],
            key=lambda x: -x["importance"]
        )[:100]
        self._save_memory()
        logger.info("💾 fact: " + key)

    def remember_experience(self, action: str, result: str, success: bool):
        """تخزين تجربة"""
        self.memory["experiences"].append({
            "action": action[:200],
            "result": result[:300],
            "success": success,
            "timestamp": datetime.now().isoformat(),
        })
        # احتفظ بآخر 500
        self.memory["experiences"] = self.memory["experiences"][-500:]
        self._save_memory()

    def remember_pattern(self, pattern: str, count: int = 1):
        """تخزين نمط"""
        # ابحث عن النمط
        found = False
        for p in self.memory["patterns"]:
            if p["pattern"] == pattern:
                p["count"] += count
                p["last_seen"] = datetime.now().isoformat()
                found = True
                break

        if not found:
            self.memory["patterns"].append({
                "pattern": pattern[:200],
                "count": count,
                "first_seen": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
            })

        self._save_memory()

    # ─────────────────────────────────────
    #  استرجاع
    # ─────────────────────────────────────
    def recall_fact(self, key: str) -> Optional[str]:
        """استرجاع حقيقة"""
        for f in self.memory["facts"]:
            if f["key"] == key:
                return f["value"]
        return None

    def recall_similar(self, context: str, limit: int = 5) -> list:
        """استرجاع تجارب مشابهة"""
        context_lower = context.lower()
        keywords = [w for w in context_lower.split() if len(w) > 3]

        scored = []
        for exp in self.memory["experiences"]:
            score = 0
            action_lower = exp["action"].lower()
            for kw in keywords:
                if kw in action_lower:
                    score += 1
            if score > 0:
                scored.append((score, exp))

        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:limit]]

    def recall_patterns(self, min_count: int = 3) -> list:
        """استرجاع الأنماط المتكررة"""
        return [
            p for p in self.memory["patterns"]
            if p["count"] >= min_count
        ]

    # ─────────────────────────────────────
    #  تحليل
    # ─────────────────────────────────────
    def get_stats(self) -> dict:
        """إحصائيات الذاكرة"""
        facts = len(self.memory["facts"])
        experiences = len(self.memory["experiences"])
        patterns = len(self.memory["patterns"])
        success_count = len([e for e in self.memory["experiences"] if e["success"]])
        total_exp = experiences or 1
        success_rate = round(success_count / total_exp * 100, 1)

        return {
            "facts": facts,
            "experiences": experiences,
            "patterns": patterns,
            "success_count": success_count,
            "failure_count": experiences - success_count,
            "success_rate": success_rate,
        }

    def format_telegram(self) -> str:
        """تنسيق للتلغرام"""
        s = self.get_stats()
        text = "🧠 *Semantic Memory*" + chr(10) + chr(10)
        text += "📚 حقائق: `" + str(s["facts"]) + "`" + chr(10)
        text += "🎓 تجارب: `" + str(s["experiences"]) + "`" + chr(10)
        text += "🔄 أنماط: `" + str(s["patterns"]) + "`" + chr(10)
        text += "✅ نجاح: `" + str(s["success_count"]) + "`" + chr(10)
        text += "❌ فشل: `" + str(s["failure_count"]) + "`" + chr(10)
        text += "📊 معدل النجاح: `" + str(s["success_rate"]) + "%`" + chr(10)

        # الأنماط المتكررة
        patterns = self.recall_patterns(min_count=3)
        if patterns:
            text += chr(10) + "*أنماط متكررة:*" + chr(10)
            for p in patterns[:5]:
                text += "• " + p["pattern"][:60] + " (" + str(p["count"]) + " مرة)" + chr(10)

        return text

    # ─────────────────────────────────────
    #  التعلم من الاقتراحات
    # ─────────────────────────────────────
    def learn_from_suggestion(self, suggestion: dict, result: dict):
        """تعلم من اقتراح"""
        action = suggestion.get("action", "")
        status = result.get("status", "unknown")

        # تخزين التجربة
        self.remember_experience(
            action=action,
            result=str(result)[:200],
            success=(status == "ok"),
        )

        # استخرج نمط
        if status == "ok":
            # نمط: "تعديل رقمي في X"
            if "timeout" in action.lower():
                self.remember_pattern("تعديل timeout")
            elif "retry" in action.lower():
                self.remember_pattern("تعديل retry")
            elif "sleep" in action.lower():
                self.remember_pattern("تعديل sleep")
            else:
                self.remember_pattern("تعديل رقمي")
        elif status == "skipped":
            self.remember_pattern("فشل: " + action[:50])

    def suggest_next(self, limit: int = 3) -> list:
        """اقتراح الخطوات التالية"""
        patterns = self.recall_patterns(min_count=2)
        return patterns[:limit]


if __name__ == "__main__":
    print("═" * 60)
    print("🧠 Semantic Memory Test")
    print("═" * 60)

    m = SemanticMemory()

    # اختبار 1: تخزين حقائق
    print()
    print("▶ اختبار 1: تخزين حقائق")
    m.remember_fact("user_name", "007aether", 0.9)
    m.remember_fact("preferred_model", "qwen2.5:3b", 0.7)
    print("  ✅ تم التخزين")

    # اختبار 2: تجارب
    print()
    print("▶ اختبار 2: تخزين تجارب")
    m.remember_experience("timeout 120→180 في jarvis", "نجح", True)
    m.remember_experience("retry mechanism", "فشل", False)
    m.remember_experience("sleep 60→300", "نجح", True)
    print("  ✅ تم التخزين")

    # اختبار 3: أنماط
    print()
    print("▶ اختبار 3: أنماط")
    m.remember_pattern("تعديل timeout")
    m.remember_pattern("تعديل timeout")
    m.remember_pattern("تعديل timeout")
    print("  ✅ تم التخزين")

    # التقرير
    print()
    print(m.format_telegram())
