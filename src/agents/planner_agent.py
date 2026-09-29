"""وكيل التخطيط"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent
from inference_router import ask


class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__("Planner", "plan")
    
    def run(self, task, context=None):
        self.log(f"أخطط لـ: {task[:50]}")
        prompt = f"""أنت مخطط خبير. قسّم المهمة التالية إلى خطوات واضحة:

المهمة: {task}

أجب بـ JSON فقط:
{{
  "steps": [
    {{"n": 1, "action": "...", "expected": "..."}},
    ...
  ],
  "complexity": "simple|medium|complex",
  "tools_needed": ["tool1", "tool2"]
}}
"""
        response = ask(prompt)
        return {"agent": self.name, "task": task, "plan": response}
