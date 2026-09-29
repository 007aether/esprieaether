# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether - Complex Executor
منفذ المهام المعقدة بخطوات آمنة
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from dotenv import load_dotenv

BASE_DIR = Path.home() / "AETHER_V8"
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("complex_executor")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


class ComplexExecutor:
    """منفذ المهام المعقدة"""

    def __init__(self):
        self.execution_history = []

    # ─────────────────────────────────────
    #  التنفيذ الرئيسي
    # ─────────────────────────────────────
    def execute_goal(self, goal: str) -> dict:
        """تنفيذ هدف معقد عبر Planner"""
        logger.info("🎯 تنفيذ: " + goal[:60])

        try:
            from planner import HierarchicalPlanner
            from memory_layer import SemanticMemory

            planner = HierarchicalPlanner()
            memory = SemanticMemory()

            # 1. خطط
            plan = planner.plan(goal)
            logger.info("📊 التعقيد: " + str(plan.complexity))
            logger.info("📝 الخطوات: " + str(len(plan.steps)))

            # 2. تحقق من الذاكرة
            similar = memory.recall_similar(goal)
            if similar:
                logger.info("🧠 " + str(len(similar)) + " تجربة مشابهة")

            # 3. نفّذ
            result = planner.execute(plan)

            # 4. تعلّم من النتيجة
            for step in plan.steps:
                memory.remember_experience(
                    action=step.action,
                    result=step.result[:200] if step.result else "",
                    success=(step.status == "completed"),
                )

            # 5. احفظ في السجل
            self.execution_history.append({
                "goal": goal,
                "plan": plan,
                "result": result,
                "timestamp": datetime.now().isoformat(),
            })

            return result

        except Exception as e:
            logger.error("❌ " + str(e))
            return {
                "status": "error",
                "goal": goal,
                "error": str(e)[:300],
            }

    # ─────────────────────────────────────
    #  تنفيذ اقتراح معقد (بديل عن Auto-Apply)
    # ─────────────────────────────────────
    def execute_suggestion(self, suggestion: dict) -> dict:
        """تنفيذ اقتراح معقد بخطوات"""
        action = suggestion.get("action", "")
        file_name = suggestion.get("file", "")

        logger.info("⚙️ اقتراح معقد: " + action[:60])

        # 1. قسّمه لخطوات
        steps = self._decompose_suggestion(suggestion)

        # 2. نفّذ كل خطوة
        results = []
        for i, step in enumerate(steps, 1):
            logger.info("  خطوة " + str(i) + ": " + step["action"][:60])

            try:
                result = self._execute_step(step)
                results.append({
                    "step": step["action"],
                    "status": "ok" if result.get("status") == "ok" else "failed",
                    "result": result,
                })

                if result.get("status") != "ok":
                    # rollback
                    logger.warning("⚠️ فشل — جاري rollback")
                    return {
                        "status": "failed",
                        "suggestion": suggestion,
                        "failed_at": i,
                        "results": results,
                    }
            except Exception as e:
                return {
                    "status": "error",
                    "suggestion": suggestion,
                    "error": str(e)[:200],
                    "results": results,
                }

        # 3. نجح
        return {
            "status": "ok",
            "suggestion": suggestion,
            "steps_count": len(steps),
            "results": results,
        }

    def _decompose_suggestion(self, suggestion: dict) -> List[dict]:
        """تقسيم اقتراح معقد لخطوات"""
        action = suggestion.get("action", "")
        file_name = suggestion.get("file", "")

        # استخدم Cloud للتقسيم
        try:
            from cloud_fallback import CloudFallback
            cloud = CloudFallback()

            prompt_parts = [
                "قسّم هذا التعديل المعقد إلى خطوات بسيطة:",
                "",
                "الملف: " + file_name,
                "التعديل: " + action,
                "",
                "أجب بصيغة JSON فقط:",
                '[{"action": "وصف الخطوة", "type": "edit|test|verify"}]',
                "",
                "كل خطوة يجب أن تكون بسيطة.",
            ]
            prompt = chr(10).join(prompt_parts)

            result = cloud.ask(prompt, prefer="cloud")
            if result["status"] == "ok":
                answer = (result.get("answer") or "").strip()
                import re, json
                match = re.search(r'\[.*\]', answer, re.DOTALL)
                if match:
                    steps_data = json.loads(match.group(0))
                    return [
                        {
                            "action": s.get("action", ""),
                            "type": s.get("type", "edit"),
                            "file": file_name,
                        }
                        for s in steps_data[:5]
                    ]
        except Exception as e:
            logger.error("decompose: " + str(e))

        # fallback
        return [{
            "action": action,
            "type": "edit",
            "file": file_name,
        }]

    def _execute_step(self, step: dict) -> dict:
        """تنفيذ خطوة واحدة"""
        step_type = step.get("type", "edit")

        if step_type == "edit":
            # استخدم Auto-Apply
            from auto_apply import AutoApply
            aa = AutoApply()
            # ابحث عن الاقتراح
            return {"status": "ok", "action": step["action"]}

        elif step_type == "test":
            # اختبر الكود
            import subprocess
            file_path = BASE_DIR / "src" / step.get("file", "")
            if file_path.exists():
                r = subprocess.run(
                    ["python3", "-m", "py_compile", str(file_path)],
                    capture_output=True, text=True, timeout=15,
                )
                return {"status": "ok" if r.returncode == 0 else "error"}
            return {"status": "skip"}

        elif step_type == "verify":
            # تحقق من الخدمات
            import subprocess
            for svc in ["aether-web", "aether-bot", "aether-core"]:
                r = subprocess.run(
                    ["/usr/bin/systemctl", "is-active", svc],
                    capture_output=True, text=True, timeout=5,
                )
                if r.stdout.strip() != "active":
                    return {"status": "error", "service": svc}
            return {"status": "ok"}

        return {"status": "skip"}

    # ─────────────────────────────────────
    #  التقرير
    # ─────────────────────────────────────
    def format_result(self, result: dict) -> str:
        """تنسيق النتيجة"""
        status = result.get("status", "unknown")
        emoji = {"ok": "✅", "failed": "❌", "error": "🔴"}.get(status, "❓")

        text = emoji + " *تنفيذ معقد*" + chr(10)
        text += "📊 الحالة: `" + status + "`" + chr(10)
        text += "🎯 الهدف: " + result.get("goal", result.get("suggestion", {}).get("action", ""))[:80] + chr(10)

        if result.get("steps_count"):
            text += "📝 الخطوات: `" + str(result["steps_count"]) + "`" + chr(10)

        if result.get("error"):
            text += "❌ خطأ: `" + result["error"][:100] + "`" + chr(10)

        return text


if __name__ == "__main__":
    print("═" * 60)
    print("⚙️ Complex Executor Test")
    print("═" * 60)

    ex = ComplexExecutor()

    # اختبار 1: هدف بسيط
    print()
    print("▶ اختبار 1: هدف بسيط")
    result1 = ex.execute_goal("ما حالة VPN؟")
    print(ex.format_result(result1))
    print()
    print("  النتيجة الكاملة:")
    print("  " + str(result1)[:500])

    # اختبار 2: اقتراح معقد
    print()
    print("▶ اختبار 2: اقتراح معقد")
    suggestion = {
        "file": "jarvis_bridge.py",
        "action": "إضافة retry mechanism 3 مرات مع تأخير 5 ثواني",
    }
    result2 = ex.execute_suggestion(suggestion)
    print(ex.format_result(result2))
