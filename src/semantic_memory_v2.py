# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether — Semantic Memory v2
ذاكرة دلالية مع بحث بالمعنى (بدون مكتبات ثقيلة)
"""
import os
import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

BASE_DIR = Path.home() / "AETHER_V8"
MEM_FILE = BASE_DIR / "semantic_memory_v2.json"

logger = logging.getLogger("semantic_memory")


class SemanticMemory:
    """ذاكرة دلالية بسيطة بدون chromadb"""
    
    def __init__(self):
        self.data = self._load()
    
    def _load(self):
        if MEM_FILE.exists():
            try:
                return json.loads(MEM_FILE.read_text())
            except Exception:
                pass
        return {"facts": [], "conversations": [], "skills": []}
    
    def _save(self):
        MEM_FILE.write_text(json.dumps(self.data, indent=2, ensure_ascii=False))
    
    def _hash(self, text):
        return hashlib.md5(text.encode()).hexdigest()[:12]
    
    # ─────────── إضافة ───────────
    
    def remember(self, content, category="fact", tags=None, importance=0.5):
        """يتذكر معلومة جديدة"""
        item = {
            "id": self._hash(content + str(datetime.now())),
            "content": content,
            "category": category,
            "tags": tags or [],
            "importance": importance,
            "created": datetime.now().isoformat(),
            "accessed": 0,
        }
        key = f"{category}s" if category != "fact" else "facts"
        if key not in self.data:
            self.data[key] = []
        self.data[key].append(item)
        self._save()
        return item["id"]
    
    # ─────────── بحث ───────────
    
    def _similarity(self, a, b):
        """تشابه بسيط بين نصين"""
        a, b = a.lower(), b.lower()
        return SequenceMatcher(None, a, b).ratio()
    
    def search(self, query, limit=5, min_score=0.3):
        """بحث دلالي بسيط"""
        results = []
        all_items = (
            self.data.get("facts", []) +
            self.data.get("conversations", []) +
            self.data.get("skills", [])
        )
        
        for item in all_items:
            content = item.get("content", "")
            # تشابه مباشر
            score = self._similarity(query, content)
            # تشابه مع الكلمات
            query_words = set(query.lower().split())
            content_words = set(content.lower().split())
            if query_words:
                word_score = len(query_words & content_words) / len(query_words)
                score = max(score, word_score)
            # تشابه مع tags
            for tag in item.get("tags", []):
                score = max(score, self._similarity(query, tag))
            
            if score >= min_score:
                item["_score"] = score
                results.append(item)
        
        results.sort(key=lambda x: (x.get("_score", 0), x.get("importance", 0)), reverse=True)
        # تحديث accessed
        for r in results[:limit]:
            r["accessed"] = r.get("accessed", 0) + 1
        self._save()
        return results[:limit]
    
    # ─────────── إحصاءات ───────────
    
    def stats(self):
        return {
            "facts": len(self.data.get("facts", [])),
            "conversations": len(self.data.get("conversations", [])),
            "skills": len(self.data.get("skills", [])),
            "total": sum(len(v) for v in self.data.values() if isinstance(v, list)),
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sm = SemanticMemory()
    
    # إضافة حقائق تجريبية
    sm.remember("EsprieAether يستخدم OpenRouter و Groq و Ollama", "fact", ["ai", "providers"], 0.9)
    sm.remember("البوت يعمل على Telegram ويدعم 28 أداة", "fact", ["telegram", "bot"], 0.8)
    sm.remember("محرك التطور الذاتي self_evolve يعمل تلقائيًا", "fact", ["evolution"], 0.85)
    
    # بحث
    print("📊 إحصاءات:", sm.stats())
    print("\n🔍 بحث عن 'OpenRouter':")
    for r in sm.search("OpenRouter"):
        print(f"  - {r['content'][:60]} (score: {r['_score']:.2f})")
    
    print("\n🔍 بحث عن 'تطور':")
    for r in sm.search("تطور"):
        print(f"  - {r['content'][:60]} (score: {r['_score']:.2f})")
