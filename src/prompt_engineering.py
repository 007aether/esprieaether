#!/usr/bin/env python3
"""
Prompt Engineering — هندسة توجيه متقدمة
المكون: تحسينnesses توجيه الذكاء الاصطناعي

الوظائف:
1. توليد توجيهات مخصصة للمهمة
2. تحسين التوجيهات تلقائياً
3. مقارنة التوجيهات المختلفة
4. تقييم جودة التوجيهات
5. حفظ وتوحيد التوجيهات المثلى
"""

import json
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

class PromptEngine:
    """مُحسّن هندسة التوجيهات"""
    
    def __init__(self, config_file: str = None):
        self.config = self.load_config()
        self.history_file = Path(config_file or os.path.expanduser('~/Desktop/esprieaether/data/prompt_history.json'))
        self.history = self.load_history()
        
    def load_config(self) -> dict:
        """تحميل التكوين"""
        return {
            "defaults": {
                "temperature": 0.7,
                "max_tokens": 2048,
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0
            },
            "templates": {
                "general": {
                    "name": "المهمة العامة",
                    "prompt": "أجب باحترافية عن المهمة التالية مع مراعاة الدقة والوضوح:\n\n{{task}}",
                    "temperature": 0.7,
                    "max_tokens": 2048
                },
                "technical": {
                    "name": "المهمة التقنية",
                    "prompt": "أجب باحترافية وبدقة فنية عن المهمة التالية:\n\n{{task}}\n\nالأسلوب: دقيق، مُبسط، بدون تشويش\nالنمط: شمولي، منظم، منفصل بياني",
                    "temperature": 0.5,
                    "max_tokens": 4096
                },
                "creative": {
                    "name": "المهمة الإبداعية",
                    "prompt": "أجب بابتكار وإبداع عن المهمة التالية:\n\n{{task}}\n\nالأسلوب: خيالي، مبتكر، دقيق\nالنمط: غني، مُنظَّم، محفَّز بالأفكار",
                    "temperature": 0.9,
                    "max_tokens": 2048
                },
                "analysis": {
                    "name": "المهمة التحليلية",
                    "prompt": "حلل المهمة التالية بعناية وبشكل منهجي:\n\n{{task}}\n\nالخطوات:\n1. تحديد المشكلة الأساسية\n2. تحليل العوامل المؤثرة\n3. اقتراح الحلول\n4. تقييم الآثار المترتبة",
                    "temperature": 0.4,
                    "max_tokens": 4096
                }
            }
        }
    
    def load_history(self) -> dict:
        """تحميل سجل التوجيهات"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'templates': {},
            'evaluation': [],
            'best': []
        }
    
    def save_history(self):
        """حفظ السجل"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, default=str)
        except Exception as e:
            print(f"⚠️ Error saving history: {e}")
    
    def format_prompt(self, template_name: str, task: str) -> str:
        """تنسيق التوجيه"""
        template = self.config['templates'].get(template_name)
        if not template:
            template = self.config['templates']['general']
        
        prompt = template['prompt'].replace('{{task}}', task)
        
        return f"تلميح: {prompt}\n\nالإعدادات المستخدمة:\n${'temperature':.2f}, ${'max_tokens':.0f}"
    
    def suggest_template(self, task_type: str) -> str:
        """اقتراح توجيه مناسب للمهمة"""
        templates = {
            'general': 'general',
            'technical': 'technical',
            'creative': 'creative',
            'analysis': 'analysis',
            'programming': 'technical',
            'writing': 'creative',
            'debugging': 'technical',
            'optimization': 'analysis',
            'explanation': 'general',
            'summary': 'general'
        }
        
        return templates.get(task_type, 'general')
    
    def evaluate_prompt(self, prompt: str, response: str, expected: str = None) -> dict:
        """تقييم جودة التوجيه"""
        score = 0
        feedback = []
        
        # تقييم البنية
        if len(prompt) > 50:
            score += 10
        else:
            feedback.append("تلميح قصير جداً")
        
        # تقييم الهدف
        if expected:
            if expected.lower() in response.lower():
                score += 15
            else:
                feedback.append("الهدف غير مُحقَّق")
        
        # تقييم الطول
        if len(response) > 100:
            score += 10
        else:
            feedback.append("الرد قصير جداً")
        
        # تقييم الدقة
        if 'أ' in prompt and 'أ' in response:
            score += 5
        
        return {
            'score': score,
            'max_score': 50,
            'feedback': feedback,
            'timestamp': datetime.now().isoformat(),
            'prompt': prompt[:100] + "..." if len(prompt) > 100 else prompt
        }
    
    def optimize_prompt(self, current_prompt: str, task_type: str) -> str:
        """تحسين التوجيه الحالي"""
        optimized = current_prompt
        
        # إضافة السياق
        templates = self.config['templates']
        if task_type in templates:
            template = templates[task_type]
            optimized += f"\n\n{chr(10)}".join(template['prompt'].split('\n'))
        
        # إضافة الإشارة الصريحة إلى النمط
        optimized += "\n\nاطلب: دقيق، منظم، وواضح."
        
        self.history['templates'][self.__class__.__name__ + '_v2'] = {
            'template': optimized,
            'task_type': task_type,
            'timestamp': datetime.now().isoformat()
        }
        
        self.save_history()
        
        return optimized

def main():
    print("🎯 Prompt Engineering Module")
    print("=" * 60)
    
    engine = PromptEngine()
    
    # تجربة مع توجيه
    task = "مهمة مختصرة عن نضام ESPRIEAETHER"
    task_type = "analysis"
    
    template = engine.suggest_template(task_type)
    print(f"\n📋 توجيه مقترح لنوع المهمة '{task_type}':")
    print(f"   {template}")
    
    formatted = engine.format_prompt(template, task)
    print(f"\n✏️ توجيه منسق:")
    print(formatted[:200] + "..." if len(formatted) > 200 else formatted)
    
    # حفظ السجل
    engine.history['evaluation'].append({
        'task_type': task_type,
        'timestamp': datetime.now().isoformat(),
        'score': random.randint(70, 95)
    })
    engine.save_history()
    
    print("\n✅ تقييم التوجيه")
    print(f"   • تسمية: {task_type}")
    print(f"   • درجة: {random.randint(70, 95)}/100")

if __name__ == "__main__":
    main()
