"""
⚡ EsprieAether - Log Analyzer
محلل ذكي للسجلات عبر Cloud
"""
import os
import re
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path.home() / "AETHER_V8"
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("log_analyzer")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

REPORTS_FILE = BASE_DIR / "log_analyzer_reports.json"


class LogAnalyzer:
    """محلل السجلات الذكي"""

    def __init__(self):
        self.reports = self._load_reports()

    def _load_reports(self) -> list:
        if REPORTS_FILE.exists():
            try:
                return json.loads(REPORTS_FILE.read_text())
            except Exception:
                pass
        return []

    def _save_reports(self):
        REPORTS_FILE.write_text(
            json.dumps(self.reports[-10:], indent=2, ensure_ascii=False)
        )

    # ─────────────────────────────────────
    #  قراءة السجلات
    # ─────────────────────────────────────
    def read_logs(self, hours: int = 24) -> dict:
        """قراءة السجلات"""
        log_files = [
            BASE_DIR / "autonomous.log",
            BASE_DIR / "bot.log",
        ]

        cutoff = datetime.now() - timedelta(hours=hours)
        all_lines = []

        for log in log_files:
            if not log.exists():
                continue
            try:
                content = log.read_text(encoding="utf-8", errors="ignore")
                lines = content.split(chr(10))
                all_lines.extend(lines[-2000:])  # آخر 2000 سطر
            except Exception:
                pass

        # احصائيات
        stats = {
            "total": len(all_lines),
            "errors": 0,
            "warnings": 0,
            "successes": 0,
            "info": 0,
        }

        error_patterns = {}
        warning_patterns = {}

        for line in all_lines:
            if "ERROR" in line:
                stats["errors"] += 1
                # استخرج نمط
                match = re.search(r'ERROR \| [^|]+ \| ([^:]+):', line)
                if match:
                    key = match.group(1).strip()[:60]
                    error_patterns[key] = error_patterns.get(key, 0) + 1
            elif "WARNING" in line:
                stats["warnings"] += 1
                match = re.search(r'WARNING \| [^|]+ \| ([^:]+):', line)
                if match:
                    key = match.group(1).strip()[:60]
                    warning_patterns[key] = warning_patterns.get(key, 0) + 1
            elif "✅" in line:
                stats["successes"] += 1
            elif "INFO" in line:
                stats["info"] += 1

        # رتب الأنماط
        sorted_errors = sorted(error_patterns.items(), key=lambda x: -x[1])[:10]
        sorted_warnings = sorted(warning_patterns.items(), key=lambda x: -x[1])[:5]

        return {
            "stats": stats,
            "error_patterns": sorted_errors,
            "warning_patterns": sorted_warnings,
            "sample_lines": all_lines[-30:],
        }

    # ─────────────────────────────────────
    #  تحليل عبر Cloud
    # ─────────────────────────────────────
    def analyze(self) -> dict:
        """تحليل شامل"""
        logs = self.read_logs()

        if logs["stats"]["total"] == 0:
            return {"status": "no_logs"}

        # حاول Cloud
        try:
            from cloud_fallback import CloudFallback
            cloud = CloudFallback()

            # ابنِ prompt
            error_summary = chr(10).join(
                f"- {e[0]}: {e[1]} مرة" for e in logs["error_patterns"][:5]
            ) or "لا أخطاء"

            warning_summary = chr(10).join(
                f"- {w[0]}: {w[1]} مرة" for w in logs["warning_patterns"][:3]
            ) or "لا تحذيرات"

            sample_text = chr(10).join(logs["sample_lines"][-10:])

            prompt_parts = [
                "أنت محلل سجلات لـ EsprieAether.",
                "",
                "احصائيات آخر 24 ساعة:",
                f"- إجمالي: {logs['stats']['total']}",
                f"- أخطاء: {logs['stats']['errors']}",
                f"- تحذيرات: {logs['stats']['warnings']}",
                f"- نجاحات: {logs['stats']['successes']}",
                "",
                "أكثر الأخطاء تكراراً:",
                error_summary,
                "",
                "أكثر التحذيرات تكراراً:",
                warning_summary,
                "",
                "آخر 10 أسطر:",
                sample_text,
                "",
                "قدم تحليلاً مختصراً في 3 نقاط:",
                "1. الحالة العامة",
                "2. المشكلة الأساسية (إن وجدت)",
                "3. توصية واحدة محددة",
            ]

            prompt = chr(10).join(prompt_parts)

            result = cloud.ask(prompt, prefer="auto")

            if result["status"] == "ok":
                analysis = result["answer"]

                # احفظ
                report = {
                    "timestamp": datetime.now().isoformat(),
                    "stats": logs["stats"],
                    "error_patterns": logs["error_patterns"][:5],
                    "analysis": analysis,
                    "source": result["source"],
                }
                self.reports.append(report)
                self._save_reports()

                return {
                    "status": "ok",
                    "report": report,
                }
        except Exception as e:
            logger.error(f"Cloud فشل: {e}")

        # fallback: تحليل محلي بسيط
        return {
            "status": "local_only",
            "stats": logs["stats"],
            "error_patterns": logs["error_patterns"][:5],
        }

    # ─────────────────────────────────────
    #  التنسيق
    # ─────────────────────────────────────
    def format_telegram(self) -> str:
        """تنسيق للـ Telegram"""
        if not self.reports:
            return "📊 لا توجد تقارير بعد. شغّل `/analyze`"

        last = self.reports[-1]
        s = last["stats"]

        text = "📊 *تحليل السجلات*" + chr(10)
        text += "_" + last["timestamp"][:19] + "_" + chr(10) + chr(10)

        text += "*الإحصائيات:*" + chr(10)
        text += f"• إجمالي: `{s['total']}`" + chr(10)
        text += f"• أخطاء: `{s['errors']}`" + chr(10)
        text += f"• تحذيرات: `{s['warnings']}`" + chr(10)
        text += f"• نجاحات: `{s['successes']}`" + chr(10) + chr(10)

        if last.get("analysis"):
            text += "*التحليل:*" + chr(10)
            text += last["analysis"][:800]

        return text


if __name__ == "__main__":
    print("═" * 60)
    print("📊 Log Analyzer Test")
    print("═" * 60)

    a = LogAnalyzer()

    # اختبار 1: قراءة
    print("\n▶ قراءة السجلات...")
    logs = a.read_logs()
    print(f"  إجمالي: {logs['stats']['total']}")
    print(f"  أخطاء: {logs['stats']['errors']}")
    print(f"  تحذيرات: {logs['stats']['warnings']}")

    print("\n▶ أكثر الأخطاء:")
    for err, count in logs["error_patterns"][:5]:
        print(f"  • {err}: {count}")

    # اختبار 2: تحليل
    print("\n▶ التحليل عبر Cloud...")
    result = a.analyze()
    print(f"  النتيجة: {result['status']}")

    if result.get("report", {}).get("analysis"):
        print("\n▶ التحليل:")
        print(result["report"]["analysis"][:500])
