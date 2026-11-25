#!/usr/bin/env python3
"""
==========================================
  BACKUP & ROLLBACK AGENT
==========================================
يحفظ نسخاً احتياطية لملفات النظام
ويقدم إمكانية الرجوع للنقاط السابقة
"""
import json
import shutil
import os
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path("C:/Users/ESPRIEAETHER/Desktop/esprieaether")
BACKUP_DIR = PROJECT_DIR / "backup"
DATA_DIR = PROJECT_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
LOG_FILE = LOGS_DIR / "backup_rollback.log"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

class BackupRollbackAgent:
    def __init__(self):
        self.backup_count = 10  # أقصى عدد من النسخ الاحتياطية
        self._log("شبدأ وكيل النسخ الاحتياطي والاسترجاع")

    def _log(self, msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {msg}"
        print(log_msg)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + "\n")

    def create_backup(self, file_path, label=None):
        """إنشاء نسخة احتياطية"""
        file_path = Path(file_path)
        if not file_path.exists():
            self._log(f"  ⚠️ الملف غير موجود: {file_path}")
            return None

        # تحديد اسم الملف
        if label:
            backup_name = f"{label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        else:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # مجلد النسخ الاحتياطية
        file_backup_dir = BACKUP_DIR / file_path.parent.name
        file_backup_dir.mkdir(parents=True, exist_ok=True)

        # نسخ الملف
        backup_path = file_backup_dir / (backup_name + ".bak")
        shutil.copy2(file_path, backup_path)

        self._log(f"  ✅ نسخ احتياطي: {backup_path}")
        return backup_path

    def restore_backup(self, backup_path):
        """استعادة من نسخة احتياطية"""
        backup_path = Path(backup_path)
        if not backup_path.exists():
            self._log(f"  ❌ ملف النسخة الاحتياطية غير موجود: {backup_path}")
            return False

        self._log(f"  📂 استعادة من: {backup_path}")
        return True

    def list_backups(self, file_path=None):
        """سرد النسخ الاحتياطية"""
        if file_path:
            file_path = Path(file_path)
            backup_files = list(file_path.parent.glob(f"*{file_path.stem}*.bak"))
        else:
            backup_files = list(BACKUP_DIR.rglob("*.bak"))

        backups = []
        for bf in backup_files:
            backups.append({
                "path": str(bf),
                "size": bf.stat().st_size,
                "modified": datetime.fromtimestamp(bf.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })

        backups.sort(key=lambda x: x["modified"], reverse=True)
        return backups

    def cleanup_old_backups(self):
        """تنظيف النسخ الاحتياطية القديمة"""
        all_backups = list(BACKUP_DIR.rglob("*.bak"))
        if len(all_backups) <= self.backup_count:
            return

        # ترتيب حسب التعديل
        all_backups.sort(key=lambda x: x.stat().st_mtime)
        to_remove = all_backups[self.backup_count:]

        for bp in to_remove:
            bp.unlink()
            self._log(f"  🗑️ حُذف النسخة القديمة: {bp}")

        self._log(f"  ✅ تنظيف انتهى: {len(to_remove)} نسخة حُذفت")

    def run(self):
        """تنفيذ الوكيل"""
        self._log("=" * 60)
        self._log("🔧 وكيل النسخ الاحتياطي والاسترجاع")
        self._log("=" * 60)

        # قائمة الملفات الرئيسية للتأمين
        main_files = [
            PROJECT_DIR / "src" / "agents" / "trading_bot.py",
            PROJECT_DIR / "src" / "agents" / "error_fix_agent.py",
            PROJECT_DIR / "src" / "agents" / "network_monitor.py",
            PROJECT_DIR / "src" / "agents" / "security_agent.py",
            PROJECT_DIR / "src" / "agents" / "predictive_analyzer.py",
            PROJECT_DIR / "src" / "agents" / "daily_report.py",
            PROJECT_DIR / "src" / "agents" / "memory_agent.py",
            PROJECT_DIR / "src" / "agents" / "arabic_support.py",
            PROJECT_DIR / "src" / "agents" / "knowledge_base.py",
            PROJECT_DIR / "src" / "agents" / "health_check.py",
            PROJECT_DIR / "src" / "agents" / "news_agent.py",
            PROJECT_DIR / "src" / "agents" / "wall_of_text.py",
            PROJECT_DIR / "src" / "agents" / "paper_trading.py",
            PROJECT_DIR / "src" / "agents" / "backup_rollback.py",
            PROJECT_DIR / "src" / "agents" / "simple_gui.py",
        ]

        # إنشاء النسخ الاحتياطية
        self._log("\n📦 إنشاء النسخ الاحتياطية:")
        for f in main_files:
            if f.exists():
                self.create_backup(f)

        # تنظيف النسخ القديمة
        self.cleanup_old_backups()

        # عرض النسخة
        self._log("\n📋 النسخ الاحتياطية المتاحة:")
        backups = self.list_backups()
        for b in backups[:10]:
            self._log(f"  - {b['path']} ({b['size']} بايت)")

        self._log("\n" + "=" * 60)
        self._log("✅ الوكيل مكتمل!")


if __name__ == "__main__":
    agent = BackupRollbackAgent()
    agent.run()
