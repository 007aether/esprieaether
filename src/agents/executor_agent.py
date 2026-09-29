"""وكيل التنفيذ"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent
from inference_router import ask


class ExecutorAgent(BaseAgent):
    def __init__(self):
        super().__init__("Executor", "execute")
    
    def run(self, task, context=None):
        self.log(f"أنفذ: {task[:50]}")
        plan = context.get("plan", "") if context else ""
        prompt = f"""أنت منفذ خبير. نفّذ المهمة بناءً على الخطة.

المهمة: {task}
الخطة: {plan}

قدّم النتيجة النهائية بشكل واضح."""
        result = ask(prompt)
        return {"agent": self.name, "task": task, "result": result}
