#!/usr/bin/env python3
"""
Web Memory Agent — ذاكرة الويب
=====================================================
نظام إدارة الذاكرة الدائمة للمعلومات والبيانات
- حفظ المعرفة والتجارب
- استرجاع المعلومات ذات الصلة
- ربط الأفكار والمعلومات
"""

import json
import os
import hashlib
from datetime import datetime
from pathlib import Path

# Base directory for the project
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
BASE_DIR = PROJECT_DIR  # data/logs is under project root, not src/data

# Data files
MEMORY_DIR = BASE_DIR / "data" / "memory"
STATE_FILE = BASE_DIR / "data" / "memory_state.json"
LOG_FILE = BASE_DIR / "data" / "logs" / "memory_agent.log"

class KnowledgeBase:
    """محرك ذاكرة الويب"""

    def __init__(self):
        self._ensure_memory_dir()
        self._ensure_state_file()
        self._log("شstarted وكيل الذاكرة (Web Memory Agent)")

    def _ensure_memory_dir(self):
        """تأكد من وجود مجلد الذاكرة"""
        os.makedirs(MEMORY_DIR, exist_ok=True)

    def _ensure_state_file(self):
        """تأكد من وجود ملف الحالة"""
        os.makedirs(STATE_FILE.parent, exist_ok=True)
        if not STATE_FILE.exists():
            with open(STATE_FILE, 'w') as f:
                json.dump({
                    "knowledge_base": [],
                    "relationships": [],
                    "entities": {},
                    "last_updated": None
                }, f, indent=2, ensure_ascii=False)

    def _log(self, message):
        """سجل الرسالة"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with open(LOG_FILE, 'a') as f:
            f.write(log_msg + "\n")

    def save_knowledge(self, subject, content, tags=[], source="user"):
        """حفظ معرفة جديدة"""
        knowledge_entry = {
            "id": hashlib.md5(f"{subject}{datetime.now().isoformat()}".encode()).hexdigest()[:12],
            "subject": subject,
            "content": content,
            "tags": tags,
            "source": source,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        # Load existing knowledge
        self._load_memory()

        # Add to knowledge base
        self.knowledge_base["knowledge_base"].append(knowledge_entry)

        # Update entities
        if subject not in self.knowledge_base["entities"]:
            self.knowledge_base["entities"][subject] = {
                "id": hashlib.md5(subject.encode()).hexdigest()[:8],
                "name": subject,
                "type": "unknown",
                "connections": []
            }

        # Save to file
        with open(STATE_FILE, 'w') as f:
            json.dump(self.knowledge_base, f, indent=2, ensure_ascii=False)

        self._log(f"💾 حُفظت المعرفة: {subject}")
        return knowledge_entry["id"]

    def get_knowledge(self, query="", tag=None, limit=10):
        """استرجاع المعرفة"""
        results = []

        for entry in self.knowledge_base.get("knowledge_base", []):
            # Match by subject
            if query and query.lower() in entry["subject"].lower():
                results.append(entry)
                continue

            # Match by tag
            if tag and tag.lower() in [t.lower() for t in entry.get("tags", [])]:
                results.append(entry)
                continue

            # Match by content
            if query and query.lower() in entry["content"].lower():
                results.append(entry)

        # Sort by relevance (most recent first)
        results.sort(key=lambda x: x["updated_at"], reverse=True)

        return results[:limit]

    def link_entities(self, entity1, entity2, relation="connected"):
        """ربط كيانين"""
        if entity1 not in self.knowledge_base["entities"]:
            self.knowledge_base["entities"][entity1] = {
                "id": hashlib.md5(entity1.encode()).hexdigest()[:8],
                "name": entity1,
                "type": "unknown",
                "connections": []
            }
        if entity2 not in self.knowledge_base["entities"]:
            self.knowledge_base["entities"][entity2] = {
                "id": hashlib.md5(entity2.encode()).hexdigest()[:8],
                "name": entity2,
                "type": "unknown",
                "connections": []
            }

        # Add connection
        if relation not in self.knowledge_base["entities"][entity1]["connections"]:
            self.knowledge_base["entities"][entity1]["connections"].append({
                "to": entity2,
                "relation": relation,
                "timestamp": datetime.now().isoformat()
            })

        self._save_state()
        self._log(f"✅ ربط: {entity1} ---({relation})--> {entity2}")

    def get_entity_info(self, entity):
        """حصول على معلومات كيان"""
        return self.knowledge_base["entities"].get(entity, {})

    def list_knowledge(self, tags=None):
        """عرض قائمة بالمعرفة"""
        if tags:
            results = []
            for entry in self.knowledge_base.get("knowledge_base", []):
                if tags[0].lower() in [t.lower() for t in entry.get("tags", [])]:
                    results.append(entry)
            return results
        return self.knowledge_base.get("knowledge_base", [])

    def delete_knowledge(self, knowledge_id):
        """حذف معرفة"""
        self.knowledge_base["knowledge_base"] = [
            k for k in self.knowledge_base.get("knowledge_base", [])
            if k["id"] != knowledge_id
        ]
        self._save_state()
        self._log(f"🗑️ حُذف المعرفة: {knowledge_id}")

    def _load_memory(self):
        """تحميل الذاكرة"""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                    self.knowledge_base = data
            except Exception:
                self.knowledge_base = {
                    "knowledge_base": [],
                    "relationships": [],
                    "entities": {},
                    "last_updated": None
                }

    def _save_state(self):
        """حفظ حالة الذاكرة"""
        self.knowledge_base["last_updated"] = datetime.now().isoformat()
        with open(STATE_FILE, 'w') as f:
            json.dump(self.knowledge_base, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    kb = KnowledgeBase()
    # Example usage
    kb.save_knowledge("Network Monitor", "وكيل لمراقبة الشبكة", ["monitor", "network", "agent"], "phase2")
    kb.save_knowledge("Predictive", "وكيل التنبؤ", ["predictive", "ai", "agent"], "phase2")
    kb.save_knowledge("Security", "وكيل الأمان", ["security", "agent"], "phase2")
    kb.link_entities("Network Monitor", "Predictive", "related")
    print("✅ KnowledgeBase initialized")
