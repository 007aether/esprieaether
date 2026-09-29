"""منسق الوكلاء — Multi-Agent Orchestration"""
import sys
import json
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.planner_agent import PlannerAgent
from agents.executor_agent import ExecutorAgent
from agents.reviewer_agent import ReviewerAgent

logger = logging.getLogger("orchestrator")


class Orchestrator:
    def __init__(self):
        self.planner = PlannerAgent()
        self.executor = ExecutorAgent()
        self.reviewer = ReviewerAgent()
    
    def process(self, task: str) -> dict:
        logger.info(f"🎯 بدء معالجة: {task[:60]}")
        
        # 1) تخطيط
        plan = self.planner.run(task)
        logger.info("✅ اكتمل التخطيط")
        
        # 2) تنفيذ
        exec_result = self.executor.run(task, {"plan": plan["plan"]})
        logger.info("✅ اكتمل التنفيذ")
        
        # 3) مراجعة
        review = self.reviewer.run(task, {"result": exec_result["result"]})
        logger.info("✅ اكتملت المراجعة")
        
        return {
            "task": task,
            "plan": plan,
            "execution": exec_result,
            "review": review,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    o = Orchestrator()
    result = o.process("اكتب دالة Python تحسب الأعداد الأولية حتى 100")
    print("\n" + "="*60)
    print("📋 النتيجة النهائية:")
    print("="*60)
    print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])
