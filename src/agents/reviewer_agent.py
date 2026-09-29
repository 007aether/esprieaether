"""وكيل المراجعة"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent
from inference_router import ask


class ReviewerAgent(BaseAgent):
    def __init__(self):
        super().__init__("Reviewer", "review")
    
    def run(self, task, context=None):
        self.log(f"أراجع: {task[:50]}")
        result = context.get("result", "") if context else ""
        prompt = f"""أنت مراجع صارم. راجع النتيجة التالية:

المهمة: {task}
النتيجة: {result}

أجب بـ JSON:
{{
  "quality": 0-10,
  "issues": ["..."],
  "suggestions": ["..."],
  "approved": true|false
}}
"""
        review = ask(prompt)
        return {"agent": self.name, "task": task, "review": review}
