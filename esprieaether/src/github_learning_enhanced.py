#!/usr/bin/env python3
"""
GitHub Learning Enhanced — تعلم متقدم من غيت هوب
المكون الرابع من خطة التطوير

تحسين الوحدة لربطها بشكل أفضل مع نضام ESPRIEAETHER
ومنحها قدرة تعلم ذكية وتحليل أعمق
"""

import requests
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter

class GitHubLearningEnhanced:
    """تعلم متقدم من غيت هوب"""
    
    def __init__(self, token: str = None):
        self.token = token or os.getenv('GITHUB_TOKEN')
        self.base_url = 'https://api.github.com'
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'EsprieAether-Learning-Enhanced/2.0.0'
        }
        if self.token:
            self.headers['Authorization'] = f'token {self.token}'
        
    def search_repositories(self, query: str, limit: int = 20, sort: str = 'stars') -> List[Dict]:
        """البحث المتقدم في غيت هوب"""
        url = f"{self.base_url}/search/repositories"
        params = {
            'q': query,
            'sort': sort,
            'per_page': min(limit, 100),
            'page': 1
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            if response.status_code == 200:
                return response.json().get('items', [])
            return []
        except Exception as e:
            print(f"⚠️ Error: {e}")
            return []
    
    def analyze_repository(self, repo: Dict) -> Dict:
        """تحليل عميق للمشروع"""
        analysis = {
            'name': repo.get('full_name'),
            'owner': repo.get('owner', {}).get('login', ''),
            'description': repo.get('description'),
            'stars': repo.get('stargazers_count', 0),
            'forks': repo.get('forks_count', 0),
            'language': repo.get('language'),
            'topics': repo.get('topics', []),
            'created': repo.get('created_at'),
            'updated': repo.get('pushed_at'),
            'size': repo.get('size', 0),
            'score': 0,
            'learning_opportunities': [],
            'categories': [],
            'recommendations': []
        }
        
        # حساب الجودة الشاملة
        score = 0
        score += repo.get('stargazers_count', 0) // 100
        score += repo.get('forks_count', 0) // 50
        
        # تقييم اللغة
        lang = repo.get('language', '')
        if lang == 'Python':
            score += 20
            analysis['learning_opportunities'].append('python-scripts')
        elif lang in ['JavaScript', 'TypeScript']:
            score += 15
            analysis['learning_opportunities'].append('js-typescript')
        elif lang in ['Go', 'Rust']:
            score += 15
            analysis['learning_opportunities'].append('system-language')
        
        # تقييم المواضيع
        topics = [t.lower() for t in analysis['topics']]
        if any('automation' in t for t in topics):
            score += 15
            analysis['categories'].append('automation')
        if any('security' in t or 'cybersecurity' in t for t in topics):
            score += 20
            analysis['categories'].append('security')
        if any('ai' in t or 'machine-learning' in t for t in topics):
            score += 15
            analysis['categories'].append('ai-ml')
        if any('reverse' in t for t in topics):
            score += 15
            analysis['categories'].append('reverse-engineering')
        
        # تقييم الوصف
        desc = (analysis['description'] or '').lower()
        if any(w in desc for w in ['tutorial', 'guide', 'learn', 'teaching', 'educational']):
            score += 10
            analysis['learning_opportunities'].append('education-materials')
        if any(w in desc for w in ['automation', 'automate', 'ci-cd', 'deployment']):
            analysis['learning_opportunities'].append('automation-patterns')
        if any(w in desc for w in ['security', 'cybersecurity', 'hacking', 'pentest']):
            analysis['learning_opportunities'].append('security-patterns')
        
        # تقييم الحجم (مشاريع مثالية)
        if analysis['size'] < 5000:
            score += 5  # مشاريع صغيرة وواضحة
        if analysis['size'] > 50000:
            score += 5  # مشاريع أكبر ومكثفة
        
        analysis['score'] = min(score, 100)
        
        # تقييم التحديث الأخير
        if analysis['updated']:
            try:
                from datetime import datetime
                updated = datetime.fromisoformat(analysis['updated'].replace('Z', '+00:00'))
                age = (datetime.now() - updated).days
                if age < 90:
                    score += 10  # محدث حديثاً
                elif age < 365:
                    score += 5
            except:
                pass
        
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """توليد توصيات للاستفادة القصوى"""
        recs = []
        desc = (analysis['description'] or '').lower()
        topics = [t.lower() for t in analysis['topics']]
        
        # التوصيات الخاصة بالمشروع
        if 'python' in analysis['language'].lower():
            recs.append('Python learning path')
        if analysis['score'] > 70:
            recs.append('High-quality project, use for reference')
        
        # التوصيات الخاصة بالفئة
        if 'security' in analysis['categories']:
            recs.append('Study security patterns and implementations')
        if 'automation' in analysis['categories']:
            recs.append('Focus on automation and DevOps workflows')
        if 'ai' in analysis['categories']:
            recs.append('Review AI/ML implementation patterns')
        
        return recs
    
    def search_learning_paths(self, categories: List[str] = None) -> List[Dict]:
        """البحث عن مسارات تعلم محددة"""
        if categories is None:
            categories = ['automation', 'security', 'ai-ml', 'reverse-engineering', 'education']
        
        queries = {
            'automation': 'automation devops ci-cd deployment tutorial',
            'security': 'security cybersecurity hacking tutorial',
            'ai-ml': 'machine-learning ai deep-learning tutorial',
            'reverse-engineering': 'reverse-engineering dissassembly malware',
            'education': 'tutorial tutorial programming tutorial'
        }
        
        all_results = []
        for cat in categories:
            query = queries.get(cat, cat)
            results = self.search_repositories(query, limit=20, sort='stars')
            all_results.extend(results)
        
        return all_results
    
    def get_learning_summary(self, results: List[Dict]) -> Dict:
        """ملخص نتائج التعلم"""
        if not results:
            return {'total': 0, 'high_quality': 0, 'categories': {}}
        
        summary = {
            'total': len(results),
            'high_quality': 0,
            'categories': Counter(),
            'top_projects': []
        }
        
        high_score = 0
        for repo in results:
            analysis = self.analyze_repository(repo)
            if analysis['score'] >= 70:
                summary['high_quality'] += 1
            summary['categories'][analysis['categories'][0] if analysis['categories'] else 'general'] += 1
        
            if len(summary['top_projects']) < 10:
                summary['top_projects'].append({
                    'name': analysis['name'],
                    'score': analysis['score'],
                    'categories': analysis['categories'],
                    'learning': analysis['learning_opportunities']
                })
        
        summary['top_projects'] = sorted(
            summary['top_projects'],
            key=lambda x: x['score'],
            reverse=True
        )
        
        return summary

def main():
    """التشغيل الرئيسي"""
    print("🔍 GitHub Learning Enhanced")
    print("=" * 60)
    
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print("⚠️ قم بوضع GITHUB_TOKEN في الملف .env")
        return
    
    gh = GitHubLearningEnhanced(token)
    
    # البحث عن مسارات التعلم
    print("\n📡 البحث في غيت هوب...")
    results = gh.search_learning_paths([
        'automation', 'security', 'ai-ml', 'education'
    ])
    
    print(f"📦 تم العثور على {len(results)} مشروع")
    
    # التحليل
    print("\n📊 التحليل والتجميع:")
    summary = gh.get_learning_summary(results)
    
    print(f"   • إجمالي المشاريع: {summary['total']}")
    print(f"   • عالية الجودة: {summary['high_quality']}")
    print(f"   • الفئات: {dict(summary['categories'])}")
    
    # أهم 10 مشاريع
    print("\n🏆 أهم 10 مشاريع:")
    for i, project in enumerate(summary['top_projects'], 1):
        print(f"   {i}. {project['name']} (جودة: {project['score']})")
        print(f"      🎯 {project['categories']} | 🎓 {project['learning']}")

if __name__ == "__main__":
    main()
