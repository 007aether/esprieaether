# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether - Hierarchical Planner
طبقة التخطيط الهرمي
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

BASE_DIR = Path.home() / "AETHER_V8"
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("planner")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

PLANS_FILE = BASE_DIR / "plans.json"


class GoalStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Step:
    """خطوة واحدة في الخطة"""
    action: str
    tool: str = ""
    params: dict = field(default_factory=dict)
    status: str = "pending"
    result: str = ""


@dataclass
class Plan:
    """خطة كاملة"""
    goal: str
    complexity: int = 5
    steps: List[Step] = field(default_factory=list)
    status: str = "pending"
    created_at: str = ""
    completed_at: str = ""


class HierarchicalPlanner:
    """المخطط الهرمي"""

    def __init__(self):
        self.plans = self._load_plans()

    def _load_plans(self) -> list:
        if PLANS_FILE.exists():
            try:
                return json.loads(PLANS_FILE.read_text())
            except Exception:
                pass
        return []

    def _save_plans(self):
        PLANS_FILE.write_text(
            json.dumps(self.plans[-50:], indent=2, ensure_ascii=False)
        )

    # ─────────────────────────────────────
    #  تقييم التعقيد
    # ─────────────────────────────────────
    def assess_complexity(self, goal: str) -> int:
        """تقييم تعقيد الهدف (1-10)"""
        try:
            from cloud_fallback import CloudFallback
            cloud = CloudFallback()

            prompt_parts = [
                "قيّم تعقيد هذا الهدف من 1 إلى 10:",
                "1 = مهمة بسيطة من خطوة واحدة",
                "5 = مهمة متعددة الخطوات بتسلسل واضح",
                "10 = تتطلب استكشافاً وإبداعاً",
                "",
                "الهدف: " + goal,
                "",
                "أجب برقم فقط من 1 إلى 10:",
            ]
            prompt = chr(10).join(prompt_parts)

            result = cloud.ask(prompt, prefer="cloud")
            if result["status"] == "ok":
                answer = (result.get("answer") or "").strip()
                # استخرج أول رقم
                import re
                match = re.search(r'\d+', answer)
                if match:
                    num = int(match.group(0))
                    return max(1, min(10, num))
        except Exception as e:
            logger.error("assess_complexity: " + str(e))

        return 5  # افتراضي

    # ─────────────────────────────────────
    #  التخطيط
    # ─────────────────────────────────────
    def plan(self, goal: str) -> Plan:
        """إنشاء خطة لهدف"""
        logger.info("🎯 تخطيط: " + goal[:60])

        complexity = self.assess_complexity(goal)
        logger.info("📊 التعقيد: " + str(complexity) + "/10")

        if complexity < 4:
            # بسيط → خطوة واحدة
            plan = Plan(
                goal=goal,
                complexity=complexity,
                steps=[Step(action=goal, status="pending")],
                created_at=datetime.now().isoformat(),
            )
        else:
            # معقد → قسّمه لخطوات
            plan = self._decompose(goal, complexity)

        self.plans.append({
            "goal": plan.goal,
            "complexity": plan.complexity,
            "steps": [{"action": s.action, "tool": s.tool, "status": s.status} for s in plan.steps],
            "status": plan.status,
            "created_at": plan.created_at,
        })
        self._save_plans()

        return plan

    def _decompose(self, goal: str, complexity: int) -> Plan:
        """تقسيم الهدف لخطوات"""
        try:
            from cloud_fallback import CloudFallback
            cloud = CloudFallback()

            # احصل على الأدوات المتاحة
            tools_list = [
                "get_airdrops", "get_vpn_status", "get_stats", "get_services",
                "get_somnia_balance", "get_market", "get_daily_digest",
                "get_evolve_suggestions", "get_cost_report", "get_pharos_balance",
                "run_command", "ask_jarvis", "apply_suggestion", "restart_service",
            ]

            prompt_parts = [
                "قسّم هذا الهدف إلى خطوات قابلة للتنفيذ:",
                "",
                "الهدف: " + goal,
                "",
                "الأدوات المتاحة: " + ", ".join(tools_list),
                "",
                "أجب بصيغة JSON فقط:",
                '[{"step": "وصف الخطوة", "tool": "اسم_الأداة", "params": {}}]',
                "",
                "اقترح " + str(min(complexity, 7)) + " خطوات على الأكثر.",
            ]
            prompt = chr(10).join(prompt_parts)

            result = cloud.ask(prompt, prefer="cloud")
            if result["status"] == "ok":
                answer = (result.get("answer") or "").strip()

                # استخرج JSON
                import re
                match = re.search(r'\[.*\]', answer, re.DOTALL)
                if match:
                    steps_data = json.loads(match.group(0))
                    steps = []
                    for s in steps_data[:7]:
                        steps.append(Step(
                            action=s.get("step", ""),
                            tool=s.get("tool", ""),
                            params=s.get("params", {}),
                        ))
                    return Plan(
                        goal=goal,
                        complexity=complexity,
                        steps=steps,
                        created_at=datetime.now().isoformat(),
                    )
        except Exception as e:
            logger.error("decompose: " + str(e))

        # fallback
        return Plan(
            goal=goal,
            complexity=complexity,
            steps=[Step(action=goal, status="pending")],
            created_at=datetime.now().isoformat(),
        )

    # ─────────────────────────────────────
    #  تنفيذ الخطة
    # ─────────────────────────────────────
    def execute(self, plan: Plan) -> dict:
        """تنفيذ خطة"""
        logger.info("▶️ تنفيذ خطة: " + plan.goal[:60])
        plan.status = "in_progress"

        results = []
        for i, step in enumerate(plan.steps, 1):
            logger.info("  خطوة " + str(i) + ": " + step.action[:60])

            try:
                step.status = "in_progress"

                # نفّذ الأداة إن وُجدت
                if step.tool:
                    step.result = self._execute_tool(step.tool, step.params)
                else:
                    # استخدم JARVIS
                    step.result = self._ask_jarvis(step.action)

                step.status = "completed"
                results.append({"step": step.action, "result": step.result[:200]})

            except Exception as e:
                step.status = "failed"
                step.result = str(e)[:200]
                results.append({"step": step.action, "error": str(e)[:200]})
                plan.status = "failed"
                break

        if plan.status != "failed":
            plan.status = "completed"
        plan.completed_at = datetime.now().isoformat()

        return {
            "status": plan.status,
            "goal": plan.goal,
            "steps_count": len(plan.steps),
            "results": results,
        }

    def _execute_tool(self, tool: str, params: dict) -> str:
        """تنفيذ أداة MCP"""
        try:
            from mcp_client import MCPClient
            client = MCPClient()
            import asyncio
            result = asyncio.run(client.call_tool(tool, params))
            return result
        except Exception as e:
            return "⚠️ فشل الأداة: " + str(e)[:100]

    def _ask_jarvis(self, question: str) -> str:
        """اسأل JARVIS — لكن استخدم الأدوات السريعة أولاً"""
        # 1. جرّب الأدوات السريعة أولاً
        quick_tools = {
            "vpn": "get_vpn_status",
            "إيردروب": "get_airdrops",
            "ايردروب": "get_airdrops",
            "إحصائ": "get_stats",
            "احصائ": "get_stats",
            "خدمات": "get_services",
            "خدمة": "get_services",
            "somnia": "get_somnia_balance",
            "سوق": "get_market",
            "تقرير": "get_daily_digest",
            "اقتراح": "get_evolve_suggestions",
            "pharos": "get_pharos_balance",
        }

        q_lower = question.lower()
        for keyword, tool in quick_tools.items():
            if keyword in q_lower:
                logger.info("  ⚡ أداة سريعة: " + tool)
                return self._execute_tool(tool, {})

        # 2. إذا لم توجد أداة، استخدم JARVIS (بطيء)
        try:
            from jarvis_bridge import JarvisBridge
            j = JarvisBridge()
            return j.ask(question)
        except Exception as e:
            return "⚠️ فشل JARVIS: " + str(e)[:100]

    # ─────────────────────────────────────
    #  التقرير
    # ─────────────────────────────────────
    def format_plan(self, plan: Plan) -> str:
        """تنسيق خطة للتلغرام"""
        text = "🎯 *الخطة*" + chr(10)
        text += "📊 التعقيد: `" + str(plan.complexity) + "/10`" + chr(10)
        text += "🎯 الهدف: " + plan.goal[:100] + chr(10) + chr(10)
        text += "*الخطوات:*" + chr(10)

        for i, s in enumerate(plan.steps, 1):
            emoji = {"pending": "⏳", "in_progress": "▶️", "completed": "✅", "failed": "❌"}.get(s.status, "❓")
            text += emoji + " " + str(i) + ". " + s.action[:60] + chr(10)
            if s.tool:
                text += "   🔧 " + s.tool + chr(10)

        return text


if __name__ == "__main__":
    print("═" * 60)
    print("🎯 Hierarchical Planner Test")
    print("═" * 60)

    p = HierarchicalPlanner()

    # اختبار 1: بسيط
    print()
    print("▶ اختبار 1: هدف بسيط")
    plan1 = p.plan("ما حالة VPN؟")
    print(p.format_plan(plan1))

    # اختبار 2: معقد
    print()
    print("▶ اختبار 2: هدف معقد")
    plan2 = p.plan("حلل النظام وأصلح المشاكل واعمل نسخة احتياطية")
    print(p.format_plan(plan2))
