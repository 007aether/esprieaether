#!/usr/bin/env python3
"""
📚 Knowledge Base Agent — وكيل قاعدة المعرفة
================================================================================

يقوم هاد الوكيل ببناء وصيانة قاعدة معرفة النظام
وتخزين واسترجاع المعلومات المهمة.

المزايا:
  1. تخزين المعلومات المهمة
  2. استرجاع المعلومات بناءً على استفسار
  3. ربط المعرفة بين الكيانات
  4. تعديل المعلومات الديناميكية
"""

import json
import os
import logging
import time
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
STATE_FILE = DATA_DIR / "knowledge_base_state.json"
LOG_FILE = LOGS_DIR / "knowledge_base.log"

# إعدادات التسجيل
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("knowledge_base")


class KnowledgeBase:
    """قاعدة معرفة النظام"""

    def __init__(self):
        self.knowledge = {
            "entities": {},
            "relationships": {},
            "skills": {},
            "documents": {},
            "usage_stats": {},
            "last_run": None,
            "status": "idle",
        }
        self._ensure_data_files()
        self._log("شبدأ وكيل قاعدة المعرفة")

    def _ensure_data_files(self):
        """تأكد من وجود ملفات البيانات"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        if not STATE_FILE.exists():
            with open(STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge, f, indent=2, ensure_ascii=False)

    def _log(self, message):
        """سجل الرسالة"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + "\n")

    def add_entity(self, name, entity_type, data=None):
        """إضافة كيان إلى قاعدة المعرفة"""
        self.knowledge["entities"][name] = {
            "type": entity_type,
            "data": data or {},
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
        }
        self._log(f"📦 إضافة كيان: {name} ({entity_type})")
        self._save_state()

    def add_relationship(self, entity1, entity2, relationship):
        """إضافة علاقة بين كيانين"""
        if entity1 not in self.knowledge["relationships"]:
            self.knowledge["relationships"][entity1] = {}
        if entity2 not in self.knowledge["relationships"][entity1]:
            self.knowledge["relationships"][entity1][entity2] = []
        self.knowledge["relationships"][entity1][entity2].append({
            "relationship": relationship,
            "timestamp": datetime.now().isoformat(),
        })
        self._log(f"🔗 ربط: {entity1} ↔ {entity2} ({relationship})")
        self._save_state()

    def get_entity(self, name):
        """استرجاع كيان"""
        return self.knowledge["entities"].get(name, None)

    def get_relationships(self, entity):
        """استرجاع العلاقات للكيان"""
        return self.knowledge["relationships"].get(entity, {})

    def add_skill(self, name, description, category):
        """إضافة مهارة إلى القاعدة"""
        self.knowledge["skills"][name] = {
            "description": description,
            "category": category,
            "usage_count": 0,
            "last_used": None,
        }
        self._log(f"🛠  إضافة مهارة: {name}")
        self._save_state()

    def use_skill(self, name):
        """تسجيل استخدام مهارة"""
        if name in self.knowledge["skills"]:
            self.knowledge["skills"][name]["usage_count"] += 1
            self.knowledge["skills"][name]["last_used"] = datetime.now().isoformat()
            self._save_state()

    def add_document(self, name, content, category):
        """إضافة مستند إلى قاعدة المعرفة"""
        self.knowledge["documents"][name] = {
            "content": content,
            "category": category,
            "created": datetime.now().isoformat(),
            "size": len(content),
        }
        self._log(f"📄 إضافة مستند: {name}")
        self._save_state()

    def search_knowledge(self, query):
        """بحث في قاعدة المعرفة"""
        results = []
        query_lower = query.lower()

        # البحث في الكيانات
        for entity, data in self.knowledge["entities"].items():
            if query_lower in entity.lower():
                results.append({
                    "type": "entity",
                    "name": entity,
                    "data": data,
                })

        # البحث في المهارات
        for skill, data in self.knowledge["skills"].items():
            if query_lower in skill.lower():
                results.append({
                    "type": "skill",
                    "name": skill,
                    "data": data,
                })

        # البحث في المستندات
        for doc, data in self.knowledge["documents"].items():
            if query_lower in doc.lower():
                results.append({
                    "type": "document",
                    "name": doc,
                    "data": data,
                })

        self._log(f"🔍 بحث عن '{query}': {len(results)} نتائج")
        return results

    def update_document(self, name, content):
        """تحديث مستند"""
        self.knowledge["documents"][name] = {
            "content": content,
            "updated": datetime.now().isoformat(),
            "size": len(content),
        }
        self._save_state()
        self._log(f"📝 تحديث المستند: {name}")

    def get_document(self, name):
        """استرجاع مستند"""
        return self.knowledge["documents"].get(name, None)

    def get_all_skills(self):
        """استرجاع جميع المهارات"""
        return self.knowledge["skills"]

    def _save_state(self):
        """حفظ الحالة"""
        self.knowledge["last_run"] = datetime.now().isoformat()
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.knowledge, f, indent=2, ensure_ascii=False)

    def run(self):
        """تنفيذ الوكيل"""
        self._log("=" * 60)
        self._log("📚 وكيل قاعدة المعرفة - Knowledge Base")
        self._log("=" * 60)
        self._log("")

        # إظهار الإحصائيات
        self._log("📊 الإحصائيات:")
        self._log(f"   كيانات: {len(self.knowledge['entities'])}")
        self._log(f"   علاقات: {len(self.knowledge['relationships'])}")
        self._log(f"   مهارات: {len(self.knowledge['skills'])}")
        self._log(f"   مستندات: {len(self.knowledge['documents'])}")

        self._log("")
        self._log("✅ وكيل قاعدة المعرفة مكتمل!")
        self._log("=" * 60)


if __name__ == "__main__":
    kb = KnowledgeBase()
    kb.run()
