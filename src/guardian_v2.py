"""⚡ EsprieAether — Guardian v2"""
import os
import json
import logging
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path.home() / "AETHER_V8"
GUARDIAN_FILE = BASE_DIR / "guardian_v2.json"
logger = logging.getLogger("guardian_v2")


class Guardian:
    """يحمي النظام من العمليات الخطيرة"""
    
    DANGEROUS = [
        r"rm\s+-rf\s+/", r"rm\s+-r\s+/", r"dd\s+if=", r"mkfs",
        r"shutdown", r"reboot", r"systemctl\s+stop",
        r">\s*/dev/", r"chmod\s+777\s+/", r"chown\s+-R",
        r"drop\s+database", r"truncate",
        r":\(\)\{.*\};:",  # fork bomb
    ]
    
    def __init__(self):
        self.data = self._load()
    
    def _load(self):
        if GUARDIAN_FILE.exists():
            try:
                return json.loads(GUARDIAN_FILE.read_text())
            except Exception:
                pass
        return {"blocked": [], "approved": [], "checks": 0}
    
    def _save(self):
        GUARDIAN_FILE.write_text(json.dumps(self.data, indent=2, ensure_ascii=False))
    
    def is_dangerous(self, command: str) -> tuple:
        """يعيد (is_dangerous, matched_pattern)"""
        for pattern in self.DANGEROUS:
            if re.search(pattern, command, re.IGNORECASE):
                return True, pattern
        return False, None
    
    def check(self, command: str, auto_approve: bool = False) -> dict:
        """يفحص أمرًا قبل التنفيذ"""
        self.data["checks"] += 1
        dangerous, pattern = self.is_dangerous(command)
        
        result = {
            "command": command[:200],
            "timestamp": datetime.now().isoformat(),
            "dangerous": dangerous,
            "pattern": pattern,
            "approved": False,
            "blocked": False,
        }
        
        if dangerous:
            if auto_approve:
                result["approved"] = True
                self.data["approved"].append(result)
                logger.warning(f"⚠️ تمت الموافقة على أمر خطير: {command[:50]}")
            else:
                result["blocked"] = True
                self.data["blocked"].append(result)
                logger.error(f"🚫 تم حظر أمر خطير: {command[:50]}")
        else:
            result["approved"] = True
        
        self._save()
        return result
    
    def stats(self):
        return {
            "total_checks": self.data["checks"],
            "blocked": len(self.data["blocked"]),
            "approved_dangerous": len(self.data["approved"]),
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    g = Guardian()
    
    tests = [
        "ls -la",
        "python script.py",
        "rm -rf /tmp/test",
        "rm -rf /",
        "systemctl stop nginx",
        "echo hello",
    ]
    
    print("🛡️ اختبار Guardian v2\n")
    for cmd in tests:
        r = g.check(cmd)
        icon = "🚫" if r["blocked"] else ("⚠️" if r["dangerous"] else "✅")
        print(f"{icon} {cmd:<30} → {'BLOCKED' if r['blocked'] else 'ALLOWED'}")
    
    print(f"\n📊 إحصاءات: {g.stats()}")
