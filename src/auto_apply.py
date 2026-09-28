"""
⚡ EsprieAether - Auto Apply Engine
تطبيق آمن للاقتراحات مع اختبار و rollback
"""
import re
import json
import shutil
import logging
import subprocess
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path.home() / "AETHER_V8"
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("auto_apply")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

BACKUP_DIR = BASE_DIR / "_auto_apply_backups"
BACKUP_DIR.mkdir(exist_ok=True)

APPLY_LOG = BASE_DIR / "auto_apply_log.json"

# ─── حدود الأمان ───
MAX_APPLIES_PER_DAY = 10
SIMPLE_KEYWORDS = [
    "timeout", "delay", "retry", "interval", "sleep",
    "عدد", "كمية", "مدة", "تأخير", "فاصل",
    "من", "إلى", "من 120", "to 180",
]


class AutoApply:
    """محرك التطبيق الآمن"""

    def __init__(self):
        self.log = self._load_log()

    def _load_log(self) -> dict:
        if APPLY_LOG.exists():
            try:
                return json.loads(APPLY_LOG.read_text())
            except Exception:
                pass
        return {"applied": [], "rejected": [], "total": 0}

    def _save_log(self):
        APPLY_LOG.write_text(
            json.dumps(self.log, indent=2, ensure_ascii=False)
        )

    # ─────────────────────────────────────
    #  فحص: هل الاقتراح بسيط؟
    # ─────────────────────────────────────
    def is_simple(self, action: str) -> bool:
        """هل الاقتراح بسيط بما يكفي للتطبيق التلقائي؟"""
        action_lower = action.lower()

        # يجب أن يحتوي على كلمة بسيطة
        for kw in SIMPLE_KEYWORDS:
            if kw in action_lower:
                return True

        # شرط أساسي: يجب أن يحتوي على "من X إلى Y" أو أرقام صريحة
        if re.search(r'\d+\s*(to|إلى|من)\s*\d+', action_lower):
            return True

        # أو يحتوي على تغيير في قيمة رقمية صريحة
        numeric_changes = [
            r'\d+\s*(ثانية|second|s)',
            r'\d+\s*(مرة|time|times)',
            r'\d+\s*(gigabyte|gb|mb|kb)',
            r'\d+\s*(percent|%)',
        ]
        for p in numeric_changes:
            if re.search(p, action_lower):
                return True

        # الاقتراحات التي تحتوي على "إضافة" أو "تطبيق" أو "تحسين" → معقدة
        complex_keywords = [
            "إضافة", "أضف", "تطبيق", "دمج", "إنشاء",
            "add", "implement", "integrate", "create",
            "تحسين", "improve", "enhance",
        ]
        for kw in complex_keywords:
            if kw in action_lower:
                return False

        return False

    # ─────────────────────────────────────
    #  نسخة احتياطية
    # ─────────────────────────────────────
    def backup(self, file_path: Path) -> Path:
        """حفظ نسخة احتياطية"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}.{timestamp}.bak"
        backup_path = BACKUP_DIR / backup_name
        shutil.copy2(file_path, backup_path)
        return backup_path

    def restore(self, backup_path: Path, original: Path):
        """استرجاع من نسخة احتياطية"""
        shutil.copy2(backup_path, original)
        logger.info(f"↩️ Rollback: {original.name}")

    # ─────────────────────────────────────
    #  توليد التعديل عبر Cloud
    # ─────────────────────────────────────
    def generate_patch(self, file_path: Path, action: str) -> dict:
        """Cloud يولّد التعديل (السطر فقط — prompt مختصر)"""
        try:
            from cloud_fallback import CloudFallback
            cloud = CloudFallback()

            content = file_path.read_text()
            lines = content.split(chr(10))

            # ابحث عن السطر الذي يحتوي على الرقم المطلوب تغييره
            import re as _re

            # استخرج الرقمين من الـ action
            numbers = _re.findall(r'\d+', action)
            if len(numbers) < 2:
                return {"status": "skipped", "reason": "لا يوجد رقمان"}

            old_val = numbers[0]
            new_val = numbers[1]

            # ابحث عن السطر الذي يحتوي على old_val
            candidate_lines = []
            for i, line in enumerate(lines):
                if old_val in line and ("=" in line or "(" in line):
                    candidate_lines.append((i + 1, line.strip()))

            if not candidate_lines:
                return {"status": "skipped", "reason": "لم أجد السطر"}

            # ابنِ prompt مختصر
            prompt_parts = [
                "You are a Python code editor.",
                "",
                "TASK: Change value " + old_val + " to " + new_val,
                "",
                "Candidate lines from " + file_path.name + ":",
            ]
            for num, line in candidate_lines[:5]:
                prompt_parts.append("  " + str(num) + ": " + line)

            prompt_parts.extend([
                "",
                "Return ONLY the new version of the best candidate line.",
                "Format: LINE_NUMBER: new line",
                "Example: 86: timeout=180,",
                "No explanation, no markdown.",
                "If none match, return: SKIP",
            ])

            prompt = chr(10).join(prompt_parts)
            result = cloud.ask(prompt, prefer="cloud")

            if result["status"] != "ok":
                return {"status": "error", "message": "Cloud فشل"}

            answer = (result.get("answer") or "").strip()

            if not answer or answer == "SKIP":
                return {"status": "skipped", "reason": "Cloud رفض"}

            # استخرج LINE_NUMBER: new_line
            match = _re.match(r'(\d+):\s*(.+)', answer)
            if not match:
                return {"status": "skipped", "reason": "صيغة غير مفهومة: " + answer[:100]}

            line_num = int(match.group(1))
            new_line = match.group(2).strip()

            if line_num < 1 or line_num > len(lines):
                return {"status": "error", "message": "رقم السطر خارج النطاق"}

            # استبدل
            old_line = lines[line_num - 1]
            indent = old_line[:len(old_line) - len(old_line.lstrip())]
            lines[line_num - 1] = indent + new_line
            new_code = chr(10).join(lines)

            if new_code == content:
                return {"status": "no_change"}

            return {
                "status": "ok",
                "old_code": content,
                "new_code": new_code,
                "old_size": len(content),
                "new_size": len(new_code),
                "line_changed": line_num,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ─────────────────────────────────────
    #  إعادة صياغة
    # ─────────────────────────────────────
    def reformulate(self, action: str) -> str:
        """إعادة صياغة اقتراح مرفوض"""
        try:
            from cloud_fallback import CloudFallback
            cloud = CloudFallback()

            prompt_parts = [
                "أعد صياغة الاقتراح التالي ليكون أكثر تحديداً:",
                "",
                "الاقتراح: " + action,
                "",
                "اجعلها محددة مع:",
                "- اسم الملف بالضبط",
                "- السطر أو الدالة",
                "- التغيير بالأرقام",
                "",
                "أجب بجملة واحدة فقط.",
            ]
            result = cloud.ask(chr(10).join(prompt_parts), prefer="cloud")

            if result["status"] == "ok":
                ans = result.get("answer") or ""
                if ans:
                    return ans.strip()[:200]
        except Exception:
            pass
        return action

    # ─────────────────────────────────────
    #  اختبار
    # ─────────────────────────────────────
    def test_file(self, file_path: Path) -> bool:
        """اختبار py_compile"""
        try:
            r = subprocess.run(
                ["python3", "-m", "py_compile", str(file_path)],
                capture_output=True, text=True, timeout=15
            )
            return r.returncode == 0
        except Exception:
            return False

    def test_services(self) -> bool:
        """اختبار الخدمات"""
        try:
            for svc in ["aether-web", "aether-bot", "aether-core"]:
                r = subprocess.run(
                    ["/usr/bin/systemctl", "is-active", svc],
                    capture_output=True, text=True, timeout=5
                )
                if r.stdout.strip() != "active":
                    return False
            return True
        except Exception:
            return False

    # ─────────────────────────────────────
    #  تطبيق
    # ─────────────────────────────────────
    def apply(self, suggestion_id: str) -> dict:
        """تطبيق اقتراح"""
        # 1. فحص الحد اليومي
        today = datetime.now().date().isoformat()
        today_applies = [
            a for a in self.log["applied"]
            if a["timestamp"][:10] == today
        ]
        if len(today_applies) >= MAX_APPLIES_PER_DAY:
            return {"status": "limit_reached", "message": "الحد اليومي"}

        # 2. ابحث عن الاقتراح
        from self_evolve import SelfEvolve
        evo = SelfEvolve()
        sug = None
        for s in evo.suggestions:
            if s["id"].endswith(suggestion_id):
                sug = s
                break

        if not sug:
            return {"status": "error", "message": "لم أجد الاقتراح"}

        if sug["status"] != "pending":
            return {"status": "error", "message": "الحالة: " + sug["status"]}

        # 3. فحص البساطة
        if not self.is_simple(sug["action"]):
            self.log["rejected"].append({
                "timestamp": datetime.now().isoformat(),
                "id": sug["id"],
                "reason": "غير بسيط",
            })
            self._save_log()
            return {
                "status": "rejected",
                "message": "غير بسيط — يحتاج مراجعة يدوية",
            }

        # 4. ابحث عن الملف
        file_path = BASE_DIR / "src" / sug["file"]
        if not file_path.exists():
            return {"status": "error", "message": "الملف غير موجود"}

        # 5. نسخة احتياطية
        backup = self.backup(file_path)

        # 6. ولّد التعديل
        patch = self.generate_patch(file_path, sug["action"])

        if patch["status"] != "ok":
            return {
                "status": patch["status"],
                "message": patch.get("reason", patch.get("message", "")),
            }

        # 7. اكتب الكود الجديد
        file_path.write_text(patch["new_code"])

        # 8. اختبار
        if not self.test_file(file_path):
            self.restore(backup, file_path)
            return {"status": "error", "message": "فشل py_compile — rollback"}

        if not self.test_services():
            self.restore(backup, file_path)
            return {"status": "error", "message": "فشل الخدمات — rollback"}

        # 9. نجح!
        sug["status"] = "auto_applied"
        sug["applied_at"] = datetime.now().isoformat()
        sug["old_size"] = patch["old_size"]
        sug["new_size"] = patch["new_size"]
        evo._save_suggestions()

        self.log["applied"].append({
            "timestamp": datetime.now().isoformat(),
            "id": sug["id"],
            "file": sug["file"],
            "action": sug["action"][:100],
        })
        self.log["total"] += 1
        self._save_log()

        return {
            "status": "ok",
            "message": "✅ تم التطبيق بنجاح",
            "file": sug["file"],
            "old_size": patch["old_size"],
            "new_size": patch["new_size"],
        }

    # ─────────────────────────────────────
    #  إحصائيات
    # ─────────────────────────────────────
    def stats(self) -> dict:
        today = datetime.now().date().isoformat()
        today_count = len([
            a for a in self.log["applied"]
            if a["timestamp"][:10] == today
        ])
        return {
            "total": self.log["total"],
            "today": today_count,
            "limit": MAX_APPLIES_PER_DAY,
            "rejected": len(self.log["rejected"]),
        }

    def format_telegram(self) -> str:
        s = self.stats()
        text = "🤖 *Auto-Apply Engine*" + chr(10) + chr(10)
        text += f"📊 إجمالي: `{s['total']}`" + chr(10)
        text += f"📅 اليوم: `{s['today']}/{s['limit']}`" + chr(10)
        text += f"❌ مرفوض: `{s['rejected']}`" + chr(10) + chr(10)

        if self.log["applied"]:
            text += "*آخر 5 تطبيقات:*" + chr(10)
            for a in self.log["applied"][-5:]:
                text += f"✅ `{a['file']}` ({a['timestamp'][11:19]})" + chr(10)

        return text


if __name__ == "__main__":
    print("═" * 60)
    print("🤖 Auto Apply Engine Test")
    print("═" * 60)

    a = AutoApply()

    # اختبار is_simple
    tests = [
        "زيادة timeout من 120 إلى 180",
        "إضافة retry mechanism 3 مرات",
        "تطبيق آليات Self-Learning",
        "تحسين تصفية الأكواد",
    ]

    print("\n▶ اختبار is_simple:")
    for t in tests:
        r = a.is_simple(t)
        emoji = "✅" if r else "❌"
        print(f"  {emoji} {t[:50]}")

    print("\n▶ الإحصائيات:")
    print(a.format_telegram())
