#!/usr/bin/env python3
"""
Stress Testing & Performance Benchmark — اختبار الحمل وال أداء
المكون الثاني من خطة التطوير

وظائف الملف:
1. توليد حمل اختباري على الخدمات
2. قياس الأداء والسرعة
3. تسجيل النتائج والتحليل
4. مقارنة الأداء قبل وبعد التحسين
"""

import json
import time
import requests
import statistics
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

class StressTester:
    """مُختبر الأداء والحمل"""
    
    def __init__(self, results_file: str = None):
        self.results_file = Path(results_file or os.path.expanduser('~/Desktop/esprieaether/data/stress_test_results.json'))
        self.results = self.load_results()
        
    def load_results(self) -> dict:
        """تحميل نتائج الاختبار السابقة"""
        if self.results_file.exists():
            try:
                with open(self.results_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'tests': [],
            'comparison': {},
            'last_test': None,
            'recommendations': []
        }
    
    def save_results(self):
        """حفظ النتائج"""
        try:
            with open(self.results_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, default=str)
        except Exception as e:
            print(f"⚠️ Error saving stress test results: {e}")
    
    def test_service(self, name: str, port: int, path: str = "/health", 
                     request_count: int = 100, delay: float = 0.1) -> dict:
        """اختبار خدمة معينة"""
        print(f"🔍 اختبار الخدمة: {name} (Port {port})")
        
        start_time = time.perf_counter()
        responses = []
        errors = 0
        latencies = []
        
        for i in range(request_count):
            try:
                url = f"http://127.0.0.1:{port}{path}"
                start = time.perf_counter()
                resp = requests.get(url, timeout=5)
                elapsed = time.perf_counter() - start
                latencies.append(elapsed * 1000)  # ms
                
                if resp.status_code >= 500:
                    errors += 1
                responses.append({
                    'request': i + 1,
                    'status': resp.status_code,
                    'latency': round(elapsed * 1000, 2)
                })
            except Exception as e:
                errors += 1
                latencies.append(0)
            
            # الانتظار بين الطلبات
            time.sleep(delay)
        
        total_time = time.perf_counter() - start_time
        total_requests = len(responses)
        
        # حساب الإحصائيات
        stats = {
            'name': name,
            'port': port,
            'requests': total_requests,
            'errors': errors,
            'success_rate': round((total_requests - errors) / total_requests * 100, 2),
            'total_time': round(total_time, 3),
            'requests_per_second': round(total_requests / total_time, 2),
            'latency': {
                'avg': round(statistics.mean(latencies), 2) if latencies else 0,
                'min': round(min(latencies), 2) if latencies else 0,
                'max': round(max(latencies), 2) if latencies else 0,
                'p50': round(statistics.median(latencies), 2) if latencies else 0,
                'p95': round(statistics.quantiles(latencies, n=20)[18], 2) if latencies else 0,
                'p99': round(statistics.quantiles(latencies, n=100)[98], 2) if latencies else 0,
            }
        }
        
        return stats
    
    def test_all_services(self) -> dict:
        """اختبار جميع الخدمات المعروفة"""
        print("=" * 60)
        print("🚀 بدء اختبار الأداء لجميع الخدمات")
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
        ]
        
        results = []
        for name, port, path in services:
            result = self.test_service(name, port, path)
            results.append(result)
        
        self.results['tests'].extend(results)
        self.results['last_test'] = datetime.now().isoformat()
        self.save_results()
        
        return results
    
    def compare_performance(self, new_results: list) -> dict:
        """مقارنة الأداء قبل وبعد التحسين"""
        print("📊 مقارنة الأداء...")
        
        if not self.results['tests']:
            return {"message": "لا توجد نتائج سابقة للمقارنة"}
        
        # إيجاد الخدمات المشتركة
        old_services = {t['name']: t for t in self.results['tests']}
        new_services = {t['name']: t for t in new_results}
        
        comparison = []
        for name in old_services:
            if name in new_services:
                old = old_services[name]
                new = new_services[name]
                
                latency_improvement = new['latency']['avg'] - old['latency']['avg']
                rsps_improvement = new['requests_per_second'] - old['requests_per_second']
                
                comparison.append({
                    'service': name,
                    'old_requests_per_sec': old['requests_per_second'],
                    'new_requests_per_sec': new['requests_per_sec'],
                    'rsps_change': round(rsps_improvement, 2),
                    'old_latency_avg': old['latency']['avg'],
                    'new_latency_avg': new['latency']['avg'],
                    'latency_change': round(latency_improvement, 2),
                    'success_rate_change': round(new['success_rate'] - old['success_rate'], 2)
                })
        
        self.results['comparison'] = comparison
        self.save_results()
        
        return comparison
    
    def get_recommendations(self) -> list:
        """توليد التوصيات"""
        if not self.results['tests']:
            return ["لا توجد نتائج لاستخلاص التوصيات"]
        
        recs = []
        for test in self.results['tests']:
            if test['success_rate'] < 80:
                recs.append(f"⚠️ خادم {test['name']} لديه معدل نجاح < 80%: {test['success_rate']}%")
            elif test['success_rate'] < 95:
                recs.append(f"📊 خادم {test['name']} يعمل بشكل جيد (95-99%)")
            
            if test['latency']['p99'] > 500:
                recs.append(f"⚠️ {test['name']} تناظر زمن استجابة عالي (p99: {test['latency']['p99']}ms)")
        
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
            print(f"   📈 Requests/Sec: {test['requests_per_second']}")
            print(f"   ⏱️ Latency Avg: {test['latency']['avg']}ms")
            print(f"   📊 Latency p99: {test['latency']['p99']}ms")
        
        if self.results['comparison']:
            print("\n🔄 مقارنة الأداء:")
            for comp in self.results['comparison']:
                change = comp['rsps_change']
                sign = "+" if change > 0 else ""
                print(f"   • {comp['service']}: {sign}{change} req/s")

def main():
    """التشغيل الرئيسي للمُختبر"""
    print("🔥 Stress Testing & Performance Benchmark")
    print("=" * 60)
    
    tester = StressTester()
    
    #اختبار جميع الخدمات
    results = tester.test_all_services()
    
    #مقارنة
    comparison = tester.compare_performance(results)
    
    #توصيات
    recommendations = tester.get_recommendations()
    
    #طباعة
    tester.print_summary()
    
    print("\n✅ اختبار الأداء مكتمل!")

if __name__ == "__main__":
    main()
