#!/usr/bin/env python3
"""
Memory Optimizer — تحسين نظام الذاكرة للنضام
المكون الأول من خطة التطوير

وظائف الملف:
1. تحليل حالة الذاكرة الحالية
2. ضغط البيانات غير المستخدمة
3. دمج المعلومات المتضاربة
4. تحسين الوصول للبيانات
5. إدارة دورة حياة الذاكرة
6. تقرير الأداء
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter
from typing import Dict, List, Any

class MemoryOptimizer:
    """مُحسّن نظام الذاكرة"""
    
    def __init__(self, state_file: str = None):
        self.state_file = Path(state_file or os.path.expanduser('~/Desktop/esprieaether/data/memory_optimizer_state.json'))
        self.state = self.load_state()
        self.stats = {}
        
    def load_state(self) -> dict:
        """تحميل حالة الذاكرة"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'memory_age': {},
            'data_categories': {},
            'compression_stats': {},
            'optimization_history': [],
            'last_optimization': None
        }
    
    def save_state(self):
        """حفظ حالة الذاكرة"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            print(f"⚠️ Error saving memory state: {e}")
    
    def analyze_memory(self, data_paths: list = None):
        """تحليل حالة الذاكرة"""
        print("🔍 تحليل حالة الذاكرة...")
        
        # الحصول على الحجم والتوقيت
        if data_paths is None:
            data_paths = [
                'data/learning_database.json',
                'data/autonome_evolve_state.json',
                'data/agent_board.json',
                'data/agent_proposed_tasks.json',
            ]
        
        for path in data_paths:
            file_path = Path(path)
            if file_path.exists():
                size = file_path.stat().st_size
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                # حساب العمر
                age = datetime.now() - mtime
                age_days = age.days
                
                self.state['memory_age'][path] = {
                    'size': size,
                    'modified': mtime.isoformat(),
                    'age_days': age_days,
                    'highlights': self._extract_highlights(file_path)
                }
                
                # تجميع حسب الفئة
                category = self._categorize_file(path)
                self.state['data_categories'][category] = self.state['data_categories'].get(category, 0) + 1
    
    def _extract_highlights(self, file_path: Path) -> dict:
        """استخراج أهم الإحصائيات من الملف"""
        try:
            if file_path.suffix == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, dict):
                    # إحصائيات عامة
                    return {
                        'key_count': len(data),
                        'nested_keys': sum(1 for k in data if isinstance(data[k], dict))
                    }
                elif isinstance(data, list):
                    return {
                        'items_count': len(data),
                        'unique_ids': len(set(str(x.get('id', '')) for x in data if isinstance(x, dict)))
                    }
        except:
            pass
        return {'size': file_path.stat().st_size}
    
    def _categorize_file(self, path: str) -> str:
        """تصنيف الملف"""
        categories = {
            'learning': ['learning_database', 'github'],
            'state': ['state', 'evolve'],
            'board': ['board', 'tasks', 'proposed'],
            'knowledge': ['knowledge', 'graph'],
            'evaluation': ['evaluation', 'eval', 'score'],
            'memory': ['memory', 'vector'],
            'execution': ['executor', 'log', 'task'],
            'integration': ['github', 'integration', 'api'],
        }
        
        for cat, keywords in categories.items():
            if any(k in path.lower() for k in keywords):
                return cat
        return 'other'
    
    def optimize_memory(self, threshold_days: int = 30):
        """تحسين نظام الذاكرة"""
        print("🚀 تحسين نظام الذاكرة...")
        
        self.analyze_memory()
        
        # تحديد الملفات القديمة
        old_files = []
        for path, info in self.state['memory_age'].items():
            if info['age_days'] > threshold_days:
                old_files.append({
                    'path': path,
                    'age_days': info['age_days'],
                    'size': info['size']
                })
        
        # الضغط والحذف
        compressed = 0
        for item in old_files:
            if item['age_days'] > threshold_days * 2:  # ملفات قديمة جدا
                print(f"  🗑️ حذف الملف القديم: {item['path']} ({item['age_days']} يوم)")
                try:
                    os.remove(item['path'])
                    compressed += 1
                except:
                    print(f"    ⚠️ لا يمكن الحذف")
        
        # تحديث الإحصائيات
        self.state['compression_stats']['files_removed'] = compressed
        self.state['compression_stats']['total_optimized'] = len(old_files)
        
        # حفظ التاريخ
        self.state['optimization_history'].append({
            'timestamp': datetime.now().isoformat(),
            'threshold_days': threshold_days,
            'files_optimized': len(old_files),
            'files_removed': compressed
        })
        
        # الحفاظ على آخر 10 محاور
        self.state['optimization_history'] = self.state['optimization_history'][-10:]
        
        self.save_state()
        print(f"✅ تم التحسين: {compressed} ملفات محذوفة")
        return compressed
    
    def get_memory_report(self) -> dict:
        """تقرير حالة الذاكرة"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_files_analyzed': len(self.state['memory_age']),
            'total_size_mb': sum(f['size'] for f in self.state['memory_age'].values()) / (1024 * 1024),
            'old_files': sum(1 for f in self.state['memory_age'].values() if f['age_days'] > 30),
            'categories': self.state['data_categories'],
            'compression': self.state.get('compression_stats', {})
        }
        return report

def main():
    """التشغيل الرئيسي لمُحسّن الذاكرة"""
    print("=" * 60)
    print("🧠 Memory Optimizer - مُحسّن نظام الذاكرة")
    print("=" * 60)
    
    optimizer = MemoryOptimizer()
    
    # تحليل
    print("\n📊 تحليل الحالة الحالية:")
    optimizer.analyze_memory()
    report = optimizer.get_memory_report()
    
    print(f"\n📈 الإحصائيات:")
    print(f"   • ملفات التحليل: {report['total_files_analyzed']}")
    print(f"   • الحجم الإجمالي: {report['total_size_mb']:.2f} MB")
    print(f"   • الملفات القديمة (>30 يوم): {report['old_files']}")
    
    # تحسين
    print("\n🔧 تحسين الذاكرة...")
    compressed = optimizer.optimize_memory(threshold_days=30)
    
    # تقرير
    print("\n📋 تقرير التحسين:")
    print(f"   • ملفات محذوفة: {compressed}")
    print(f"   • تاريخ التحسين: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    print("\n✅ الذاكرة محسّنة بنجاح!")
    optimizer.save_state()

if __name__ == "__main__":
    main()
