"""
⚡ EsprieAether - Self Evolution Engine
محرك التطوير الذاتي المحلي
"""
import os
import re
import json
import shutil
import logging
import subprocess
from datetime import datetime
from pathlib import Path

BASE_DIR = Path.home() / "AETHER_V8"
SUGGESTIONS_FILE = BASE_DIR / "self_evolve_suggestions.json"
BACKUP_DIR = BASE_DIR / "_self_evolve_backups"
BACKUP_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("self_evolve")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


class SelfEvolve:
    """محرك التطوير الذاتي"""

    def __init__(self):
        self.suggestions = self._load_suggestions()

    # ─────────────────────────────────────
    #  التحميل والحفظ
    # ─────────────────────────────────────
    def _load_suggestions(self) -> list:
        if SUGGESTIONS_FILE.exists():
            try:
                return json.loads(SUGGESTIONS_FILE.read_text())
            except Exception:
                pass
        return []

    def _save_suggestions(self):
        SUGGESTIONS_FILE.write_text(
            json.dumps(self.suggestions, indent=2, ensure_ascii=False)
        )

    # ─────────────────────────────────────
    #  تحليل السجلات
    # ─────────────────────────────────────
    def analyze_logs(self, lines: int = 200) -> dict:
        """تحليل آخر الأسطر من السجلات"""
        log_file = BASE_DIR / "autonomous.log"
        if not log_file.exists():
            return {"status": "error", "message": "لا يوجد سجل"}

        content = log_file.read_text()
        recent = content.split("\n")[-lines:]

        # احصائيات
        errors = [l for l in recent if "ERROR" in l]
        warnings = [l for l in recent if "WARNING" in l]
        successes = [l for l in recent if "✅" in l]

        # الأخطاء المتكررة
        error_patterns = {}
        for err in errors:
            # استخرج نوع الخطأ
            match = re.search(r'ERROR \| [^|]+ \| ([^:]+):', err)
            if match:
                key = match.group(1).strip()[:50]
                error_patterns[key] = error_patterns.get(key, 0) + 1

        return {
            "status": "ok",
            "total_lines": len(recent),
            "errors": len(errors),
            "warnings": len(warnings),
            "successes": len(successes),
            "error_patterns": error_patterns,
            "sample_errors": errors[-5:],
        }

    # ─────────────────────────────────────
    #  اقتراح تحسينات (عبر JARVIS)
    # ─────────────────────────────────────
    def suggest_improvements(self) -> list:
        """استخدام JARVIS لاقتراح تحسينات"""
        from jarvis_bridge import JarvisBridge

        analysis = self.analyze_logs()
        if analysis["status"] != "ok":
            return []

        # احصل على قائمة ملفاتك الحقيقية
        src_files = [f.name for f in (BASE_DIR / "src").glob("*.py")]

        jarvis = JarvisBridge()

        prompt = f"""أنت مساعد تطوير لـ EsprieAether.

الملفات الحقيقية في المشروع (استخدم فقط هذه الأسماء):
{chr(10).join('- ' + f for f in src_files)}

حالة السجلات (آخر 200 سطر):
- إجمالي: {analysis['total_lines']}
- أخطاء: {analysis['errors']}
- تحذيرات: {analysis['warnings']}
- نجاحات: {analysis['successes']}

أنواع الأخطاء المتكررة:
{json.dumps(analysis['error_patterns'], ensure_ascii=False, indent=2)}

آخر 3 أخطاء:
{chr(10).join(analysis['sample_errors'][-3:])}

اقترح حتى 3 تحسينات. استخدم فقط أسماء الملفات أعلاه.
الصيغة الصارمة:
[FILE: اسم_ملف_من_القائمة] [ACTION: وصف مختصر]
"""

        try:
            # استخدم Cloud أولاً، ثم Local

            try:

                from cloud_fallback import CloudFallback

                cloud = CloudFallback()

                result = cloud.ask(prompt, prefer="auto")

                if result["status"] == "ok":

                    response = result["answer"]

                    logger.info(f"✅ اقتراحات من: {result['source']}")

                else:

                    response = jarvis.ask(prompt, use_history=False)

            except Exception as e:

                logger.warning(f"Cloud فشل: {e}")

                response = jarvis.ask(prompt, use_history=False)

            # استخرج الاقتراحات
            suggestions = []
            for line in response.split("\n"):
                if "[FILE:" in line and "[ACTION:" in line:
                    file_match = re.search(r'\[FILE:\s*([^\]]+)\]', line)
                    action_match = re.search(r'\[ACTION:\s*([^\]]+)\]', line)
                    if file_match and action_match:
                        suggestions.append({
                            "id": f"sug_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(suggestions)}",
                            "timestamp": datetime.now().isoformat(),
                            "file": file_match.group(1).strip(),
                            "action": action_match.group(1).strip(),
                            "raw": line.strip(),
                            "status": "pending",
                            "analysis": analysis,
                        })

            if suggestions:
                self.suggestions.extend(suggestions)
                self._save_suggestions()

            return suggestions
        except Exception as e:
            logger.error(f"فشل توليد الاقتراحات: {e}")
            return []

    # ─────────────────────────────────────
    #  عرض الاقتراحات
    # ─────────────────────────────────────
    def list_pending(self) -> list:
        return [s for s in self.suggestions if s["status"] == "pending"]

    def format_suggestions(self, limit: int = 3) -> str:
        """تنسيق للـ Telegram"""
        pending = self.list_pending()[:limit]
        if not pending:
            return "📭 لا توجد اقتراحات معلّقة"

        text = f"🧠 *اقتراحات التطوير* ({len(self.list_pending())})\n\n"
        for i, s in enumerate(pending, 1):
            text += f"*{i}.* `{s['id'][-8:]}`\n"
            text += f"📁 `{s['file']}`\n"
            text += f"⚙️ {s['action'][:80]}\n\n"

        text += "_للموافقة: `/approve <id>`_\n_للرفض: `/reject <id>`_"
        return text

    # ─────────────────────────────────────
    #  الموافقة والتنفيذ
    # ─────────────────────────────────────
    def approve(self, suggestion_id: str) -> dict:
        """الموافقة على اقتراح وتنفيذه"""
        # ابحث
        sug = None
        for s in self.suggestions:
            if s["id"].endswith(suggestion_id):
                sug = s
                break

        if not sug:
            return {"status": "error", "message": f"لم أجد: {suggestion_id}"}

        if sug["status"] != "pending":
            return {"status": "error", "message": f"الحالة: {sug['status']}"}

        # نسخة احتياطية
        backup_path = self._backup_file(sug["file"])
        sug["backup"] = str(backup_path)

        # التطبيق
        apply_result = self._apply_suggestion(sug)

        if apply_result["status"] == "ok":
            # اختبار
            test = self._test_system()
            if test["status"] == "ok":
                sug["status"] = "approved"
                sug["applied_at"] = datetime.now().isoformat()
                self._save_suggestions()
                return {
                    "status": "ok",
                    "message": "✅ تم التطبيق والاختبار",
                    "suggestion": sug,
                }
            else:
                # rollback
                self._rollback_file(backup_path, sug["file"])
                sug["status"] = "test_failed"
                self._save_suggestions()
                return {
                    "status": "error",
                    "message": f"❌ الاختبار فشل — تم rollback",
                    "test": test,
                }
        else:
            sug["status"] = "apply_failed"
            self._save_suggestions()
            return apply_result

    def _backup_file(self, file_name: str) -> Path:
        """نسخة احتياطية"""
        source = self._resolve_file(file_name)
        if not source.exists():
            raise FileNotFoundError(file_name)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup = BACKUP_DIR / f"{source.name}.{timestamp}.bak"
        shutil.copy2(source, backup)
        logger.info(f"📦 Backup: {backup}")
        return backup

    def _rollback_file(self, backup_path: Path, file_name: str):
        """استرجاع"""
        target = self._resolve_file(file_name)
        shutil.copy2(backup_path, target)
        logger.info(f"↩️ Rollback: {target}")

    def _resolve_file(self, file_name: str) -> Path:
        """تحويل اسم الملف إلى مسار"""
        # إذا كان المسار كامل
        if file_name.startswith("/"):
            return Path(file_name)
        # إذا كان في src
        return BASE_DIR / "src" / file_name

    def _apply_suggestion(self, sug: dict) -> dict:
        """تطبيق الاقتراح (تلقائي محدود)"""
        target = self._resolve_file(sug["file"])

        if not target.exists():
            return {"status": "error", "message": f"الملف غير موجود: {target}"}

        # حالياً: نسجل فقط — التعديل اليدوي
        # (لتجنب كسر النظام)
        return {
            "status": "manual_required",
            "message": "التطبيق التلقائي غير مفعّل — يحتاج مراجعة يدوية",
            "file": str(target),
            "action": sug["action"],
        }

    def _test_system(self) -> dict:
        """اختبار سريع"""
        try:
            # فحص كل الملفات
            r = subprocess.run(
                ["python3", "-m", "py_compile"] +
                [str(f) for f in (BASE_DIR / "src").glob("*.py")],
                capture_output=True, text=True, timeout=30
            )
            if r.returncode != 0:
                return {"status": "error", "message": r.stderr}

            # فحص الخدمات
            for svc in ["aether-core", "aether-bot", "aether-web"]:
                s = subprocess.run(
                    ["systemctl", "is-active", svc],
                    capture_output=True, text=True, timeout=5
                )
                if s.stdout.strip() != "active":
                    return {"status": "error", "message": f"{svc} ليس نشطاً"}

            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def reject(self, suggestion_id: str) -> dict:
        """رفض اقتراح"""
        for s in self.suggestions:
            if s["id"].endswith(suggestion_id):
                s["status"] = "rejected"
                self._save_suggestions()
                return {"status": "ok", "message": "تم الرفض"}
        return {"status": "error", "message": "لم أجد"}


# ─── اختبار ───
if __name__ == "__main__":
    print("═" * 60)
    print("🧠 Self Evolve Test")
    print("═" * 60)

    evo = SelfEvolve()

    # تحليل السجلات
    print("\n▶ تحليل السجلات:")
    analysis = evo.analyze_logs()
    print(json.dumps(analysis, indent=2, ensure_ascii=False)[:500])

    # اقتراحات
    print("\n▶ توليد الاقتراحات...")
    suggestions = evo.suggest_improvements()
    print(f"عدد: {len(suggestions)}")
    for s in suggestions:
        print(f"  • {s['file']}: {s['action'][:60]}")
