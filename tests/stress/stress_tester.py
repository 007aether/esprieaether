#!/usr/bin/env python3
"""
Stress Testing Suite — وحدة الإجهاد الإنتاجي
المكون: اختبار الأداء والحمل لجميع الخدمات

الوظائف:
1. اختبار تحميل الخدمات
2. قياس سرعة الاستجابة
3. تحديد نقاط الضعف
4. مقارنة الأداء
5. توليد التقارير
"""

import json
import time
import requests
import statistics
import os
from datetime import datetime
from pathlib import Path

class StressTester:
    """مُختبر الأداء والحمول"""
    
    def __init__(self, results_file: str = None):
        self.results_file = Path(results_file or os.path.expanduser('~/Desktop/esprieaether/data/stress_test_results.json'))
        self.results = self.load_results()
        
    def load_results(self) -> dict:
        """تحميل النتائج السابقة"""
        if self.results_file.exists():
            try:
                with open(self.results_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'tests': [],
            'comparison': {},
            'recommendations': []
        }
    
    def save_results(self):
        """حفظ النتائج"""
        try:
            with open(self.results_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, default=str)
        except Exception as e:
            print(f"⚠️ Error saving results: {e}")
    
    def test_service(self, name: str, port: int, path: str = "/health", requests: int = 50) -> dict:
        """اختبار خدمة معينة"""
        print(f"🔍 اختبار {name} (Port {port})...")
        
        latencies = []
        errors = 0
        
        start_time = time.perf_counter()
        
        for i in range(requests):
            try:
                url = f"http://127.0.0.1:{port}{path}"
                start = time.perf_counter()
                resp = requests.get(url, timeout=5)
                elapsed = time.perf_counter() - start
                latencies.append(elapsed * 1000)  # ms
                
                if resp.status_code >= 500:
                    errors += 1
            except Exception as e:
                errors += 1
                latencies.append(0)
        
        total_time = time.perf_counter() - start_time
        
        stats = {
            'name': name,
            'port': port,
            'requests': requests,
            'errors': errors,
            'success_rate': round((requests - errors) / requests * 100, 2),
            'total_time': round(total_time, 3),
            'avg_latency': round(statistics.mean(latencies), 2) if latencies else 0,
            'min_latency': round(min(latencies), 2) if latencies else 0,
            'max_latency': round(max(latencies), 2) if latencies else 0,
            'p50_latency': round(statistics.median(latencies), 2) if latencies else 0,
            'p95_latency': round(statistics.quantiles(latencies, n=20)[18], 2) if latencies else 0,
        }
        
        return stats
    
    def test_all_services(self) -> list:
        """اختبار جميع الخدمات"""
        print("\n🚀 بدء اختبار الأداء لجميع الخدمات")
        print("=" * 60)
        
        services = [
            ("Web Interface", 5000, "/health"),
            ("Cloud Desktop", 5001, "/health"),
            ("Sunna API", 5100, "/health"),
            ("Integrations", 5102, "/health"),
            ("Kanban", 5103, "/health"),
            ("Ollama", 11434, "/api/tags"),
            ("Router", 11435, "/health"),
            ("Orchestrator", 11436, "/health"),
            ("Agent Mesh", 11437, "/health"),
            ("JARVIS", 8000, "/api/health"),
            ("DSH Relay", 5105, "/health"),
            ("G0DM0D3", 3860, "/"),
        ]
        
        results = []
        for name, port, path in services:
            result = self.test_service(name, port, path)
            results.append(result)
            time.sleep(0.5)  # انتظار بسيط بين الاختبارات
        
        self.results['tests'].extend(results)
        self.results['last_test'] = datetime.now().isoformat()
        self.save_results()
        
        return results
    
    def get_recommendations(self) -> list:
        """توليد التوصيات"""
        recs = []
        
        for test in self.results['tests']:
            if test['success_rate'] < 90:
                recs.append(f"⚠️ {test['name']} معدل نجاح منخفض: {test['success_rate']}%")
            elif test['success_rate'] < 98:
                recs.append(f"📊 {test['name']} يعمل جيداً ({test['success_rate']}%)")
            else:
                recs.append(f"✅ {test['name']} يعمل بشكل مثالي")
            
            if test['p95_latency'] > 500:
                recs.append(f"⏱️ {test['name']} وقت استجابة بطيء (p95: {test['p95_latency']}ms)")
        
        self.results['recommendations'] = recs
        self.save_results()
        
        return recs
    
    def print_summary(self):
        """طباعة ملخص النتائج"""
        print("\n" + "=" * 60)
        print("📊 ملخص اختبار الأداء")
        print("=" * 60)
        
        for test in self.results['tests']:
            print(f"\n🌐 {test['name']} (Port {test['port']})")
            print(f"   ✅ Rate: {test['success_rate']}%")
            print(f"   ⏱️ Avg: {test['avg_latency']}ms")
            print(f"   📊 P95: {test['p95_latency']}ms")
        
        print("\n💡 التوصيات:")
        for rec in self.results['recommendations']:
            print(f"   • {rec}")

def main():
    print("🔥 Stress Testing Suite")
    print("=" * 60)
    
    tester = StressTester()
    results = tester.test_all_services()
    tester.get_recommendations()
    tester.print_summary()

if __name__ == "__main__":
    main()
