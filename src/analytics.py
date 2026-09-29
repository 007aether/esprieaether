# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""⚡ EsprieAether — Analytics Dashboard"""
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path.home() / "AETHER_V8"
ANALYTICS_FILE = BASE_DIR / "analytics.json"
logger = logging.getLogger("analytics")


class Analytics:
    def __init__(self):
        self.data = self._load()
    
    def _load(self):
        if ANALYTICS_FILE.exists():
            try:
                return json.loads(ANALYTICS_FILE.read_text())
            except Exception:
                pass
        return {"events": [], "daily_stats": {}}
    
    def _save(self):
        ANALYTICS_FILE.write_text(json.dumps(self.data, indent=2, ensure_ascii=False))
    
    def track(self, event_type, details=None):
        """يتتبع حدثًا"""
        event = {
            "type": event_type,
            "details": details or {},
            "timestamp": datetime.now().isoformat(),
        }
        self.data["events"].append(event)
        # احتفظ بآخر 1000 حدث فقط
        self.data["events"] = self.data["events"][-1000:]
        
        # إحصاءات يومية
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.data["daily_stats"]:
            self.data["daily_stats"][today] = {}
        self.data["daily_stats"][today][event_type] = self.data["daily_stats"][today].get(event_type, 0) + 1
        
        self._save()
    
    def report(self, days=7):
        """تقرير آخر N أيام"""
        report = {"period_days": days, "total_events": len(self.data["events"]), "by_type": {}, "daily": {}}
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        recent = [e for e in self.data["events"] if e["timestamp"] >= cutoff]
        for e in recent:
            report["by_type"][e["type"]] = report["by_type"].get(e["type"], 0) + 1
        # آخر N أيام
        for i in range(days):
            day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            if day in self.data["daily_stats"]:
                report["daily"][day] = self.data["daily_stats"][day]
        return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    a = Analytics()
    # محاكاة أحداث
    a.track("task_received", {"source": "telegram"})
    a.track("task_completed", {"duration": 5.2})
    a.track("llm_call", {"provider": "groq", "tokens": 150})
    a.track("error", {"type": "timeout"})
    print("📊 تقرير Analytics:")
    print(json.dumps(a.report(7), ensure_ascii=False, indent=2))
