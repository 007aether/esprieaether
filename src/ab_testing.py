"""⚡ EsprieAether — A/B Testing"""
import os
import json
import logging
import random
from datetime import datetime
from pathlib import Path

BASE_DIR = Path.home() / "AETHER_V8"
AB_FILE = BASE_DIR / "ab_testing.json"

logger = logging.getLogger("ab_testing")


class ABTesting:
    def __init__(self):
        self.data = self._load()
    
    def _load(self):
        if AB_FILE.exists():
            try:
                return json.loads(AB_FILE.read_text())
            except Exception:
                pass
        return {"experiments": {}}
    
    def _save(self):
        AB_FILE.write_text(json.dumps(self.data, indent=2, ensure_ascii=False))
    
    def create(self, name, variants):
        """ينشئ تجربة جديدة"""
        self.data["experiments"][name] = {
            "variants": variants,  # ['A', 'B']
            "results": {v: {"wins": 0, "losses": 0, "total": 0} for v in variants},
            "created": datetime.now().isoformat(),
        }
        self._save()
        return name
    
    def choose(self, name):
        """يختار variant عشوائيًا (50/50)"""
        exp = self.data["experiments"].get(name)
        if not exp:
            return None
        return random.choice(exp["variants"])
    
    def record(self, name, variant, success):
        """يسجل نتيجة"""
        exp = self.data["experiments"].get(name)
        if not exp:
            return
        r = exp["results"][variant]
        r["total"] += 1
        if success:
            r["wins"] += 1
        else:
            r["losses"] += 1
        self._save()
    
    def best(self, name):
        """يعيد أفضل variant"""
        exp = self.data["experiments"].get(name)
        if not exp:
            return None
        best = None
        best_rate = -1
        for v, r in exp["results"].items():
            if r["total"] > 0:
                rate = r["wins"] / r["total"]
                if rate > best_rate:
                    best_rate = rate
                    best = v
        return best
    
    def report(self, name):
        exp = self.data["experiments"].get(name)
        if not exp:
            return None
        report = {"name": name, "variants": {}}
        for v, r in exp["results"].items():
            rate = r["wins"] / r["total"] if r["total"] > 0 else 0
            report["variants"][v] = {"rate": f"{rate:.2%}", **r}
        report["best"] = self.best(name)
        return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ab = ABTesting()
    
    # تجربة: استخدام Groq vs OpenRouter للمهام البسيطة
    ab.create("simple_tasks_model", ["groq", "openrouter"])
    
    # محاكاة 20 مهمة
    for _ in range(20):
        variant = ab.choose("simple_tasks_model")
        success = random.random() > 0.3 if variant == "groq" else random.random() > 0.4
        ab.record("simple_tasks_model", variant, success)
    
    print("📊 تقرير A/B Testing:")
    print(json.dumps(ab.report("simple_tasks_model"), ensure_ascii=False, indent=2))
