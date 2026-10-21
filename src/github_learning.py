"""
G0DM0D3 GitHub Integration Learning System
برنامج متقدم لربط الجهاز مع غيت هوب وتعلم المشاريع وحللها
"""

import requests
import json
import os
from datetime import datetime
from pathlib import Path


class GitHubIntegration:
    """وحدة الربط مع غيت هوب"""
    
    def __init__(self, token: str = None):
        self.token = token or os.getenv('GITHUB_TOKEN')
        self.base_url = 'https://api.github.com'
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'EsprieAether-Learning-System/1.0.0'
        }
        if self.token:
            self.headers['Authorization'] = f'token {self.token}'
    
    def search_repositories(self, query: str, limit: int = 10, sort: str = 'stars'):
        """يبحث في غيت هوب عن مشاريع متعلقة"""
        url = f"{self.base_url}/search/repositories"
        params = {
            'q': query,
            'sort': sort,
            'per_page': min(limit, 50),
            'page': 1
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            if response.status_code == 200:
                return response.json().get('items', [])
            else:
                print(f"❌ Error: {response.status_code}")
                return []
        except Exception as e:
            print(f"⚠️ Error searching: {e}")
            return []
    
    def get_repository(self, repo_name: str) -> dict:
        """يقرأ بيانات الريبوزيتوري"""
        url = f"{self.base_url}/repos/{repo_name}"
        headers = self.headers.copy()
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"⚠️ Error fetching repo: {e}")
            return None
    
    def get_repository_contents(self, repo_name: str, path: str = '') -> list:
        """يقرأ الملفات في الريبوزيتوري"""
        url = f"{self.base_url}/repos/{repo_name}/contents/{path}"
        headers = self.headers.copy()
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                items = response.json()
                if isinstance(items, list):
                    files = []
                    for item in items:
                        if item['type'] == 'file':
                            files.append(item['name'])
                        elif item['type'] == 'dir':
                            files.extend(self.get_repository_contents(repo_name, item['path']))
                    return files
            return []
        except Exception as e:
            print(f"⚠️ Error reading contents: {e}")
            return []
    
    def analyze_repository(self, repo: dict) -> dict:
        """يحلل الريبوزيتوري ويحدد الجودة والتعلم"""
        score = 0
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
            'score': 0,
            'categories': [],
            'learning_opportunities': []
        }
        
        # حساب الجودة
        score += repo.get('stargazers_count', 0) // 100
        score += repo.get('forks_count', 0) // 50
        if analysis['language'] in ['Python', 'JavaScript', 'TypeScript', 'Go', 'Rust']:
            score += 15  # Higher weight for major languages
        if analysis['language'] == 'Python':
            score += 10
        if 'automation' in analysis['topics']:
            score += 20
        if 'security' in analysis['topics'] or 'cybersecurity' in analysis['topics']:
            score += 25
        if 'ai' in analysis['topics'] or 'machine-learning' in analysis['topics']:
            score += 20
        if 'reverse-engineering' in analysis['topics']:
            score += 20
        if repo.get('description') and 'tutorial' in repo['description'].lower():
            score += 10
        if repo.get('description') and 'guide' in repo['description'].lower():
            score += 8
        if repo.get('description') and ('learn' in repo['description'].lower() or 'learning' in repo['description'].lower()):
            score += 10
        if repo.get('stargazers_count', 0) > 10000:
            score += 20
        if repo.get('forks_count', 0) > 1000:
            score += 15
        if repo.get('created_at'):
            # Recent repos get points
            try:
                from datetime import datetime
                created = datetime.fromisoformat(repo['created_at'].replace('Z', '+00:00'))
                age = (datetime.now() - created).days
                if age < 365:
                    score += 15  # Recent and active
            except:
                pass
        
        analysis['score'] = min(score, 100)
        
        # تحديد الفرص التعليمية
        desc = (analysis['description'] or '').lower()
        language = analysis['language'] or ''
        topics = [t.lower() for t in analysis['topics']]
        if 'python' in language.lower():
            analysis['learning_opportunities'].append('python-scripts')
        if language in ['JavaScript', 'TypeScript']:
            analysis['learning_opportunities'].append('js-typescript')
        if language in ['Go', 'Rust']:
            analysis['learning_opportunities'].append('system-language')
        if any(t in topics for t in ['automation', 'devops']):
            analysis['learning_opportunities'].append('automation-patterns')
        if any(t in topics for t in ['security', 'cybersecurity']):
            analysis['learning_opportunities'].append('security-patterns')
        if any(t in topics for t in ['ai', 'machine-learning']):
            analysis['learning_opportunities'].append('ai-patterns')
        if 'reverse-engineering' in topics:
            analysis['learning_opportunities'].append('reversing')
        if desc and ('tutorial' in desc or 'guide' in desc or 'learn' in desc or 'teaching' in desc):
            analysis['learning_opportunities'].append('education-materials')
        if desc and ('project' in desc or 'example' in desc or 'practice' in desc):
            analysis['learning_opportunities'].append('project-examples')
        
        return analysis
    
    def search_learning_paths(self, queries: list[str] = None) -> list:
        """يبحث في غيت هوب عن مسارات تعلم"""
        if queries is None:
            queries = [
                'automation+teaching+language',
                'programming+skills+language',
                'code+examples+language',
                'practice+exercises+language',
                'certificates+language',
                'tutorials+language',
                'guides+language'
            ]
        
        all_results = []
        for query in queries or []:
            results = self.search_repositories(query, limit=20)
            all_results.extend(results)
            import time
            time.sleep(1)  # Rate limiting
        
        return all_results


class LearningDatabase:
    """قاعدة بيانات التعلم المستمر"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Path.home() / 'Desktop/esprieaether/data/learning_database.json'
        self.data = self.load()
    
    def load(self) -> dict:
        import json
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading database: {e}")
                return {'repositories': [], 'learnings': [], 'statistics': {}}
        return {'repositories': [], 'learnings': [], 'statistics': {}}
    
    def save(self):
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving database: {e}")
    
    def add_repository(self, repo_data: dict):
        """يضيف مشروع جديد إلى قاعدة البيانات"""
        self.data['repositories'].append(repo_data)
        repo_key = repo_data.get('full_name', repo_data.get('name', 'unknown'))
        if repo_key not in [r.get('key', '') for r in self.data['repositories']]:
            self.data['repositories'] = [r for r in self.data['repositories'] 
                                         if r.get('key', '') != repo_key]
            self.data['repositories'].insert(0, repo_data)
        self.save()
    
    def add_learning(self, learning: dict):
        """يضيف نتيجة تعلم"""
        self.data['learnings'].append(learning)
        self.save()
    
    def get_statistics(self) -> dict:
        return {
            'total_repositories': len(self.data.get('repositories', [])),
            'total_learnings': len(self.data.get('learnings', [])),
            'categories': self.data.get('statistics', {}),
            'last_update': datetime.now().isoformat()
        }


class AutonomousLearningLoop:
    """الحلقة التعلم المستقلة"""
    
    def __init__(self):
        self.github = GitHubIntegration()
        self.db = LearningDatabase()
    
    def run_cycle(self, iterations: int = 3, delay: int = 300):
        """تشغيل دورة التعلم"""
        print(f"\n{'='*60}")
        print(f"🔄 بدء دورة التعلم التلقائية - {iterations} تكرار")
        print(f"{'='*60}\n")
        
        for i in range(iterations):
            print(f"\n🔄 دورة {i+1}/{iterations}")
            
            # البحث في غيت هوب
            print("📡 البحث في غيت هوب...")
            results = self.github.search_learning_paths()
            print(f"📦 تم العثور على {len(results)} مشروع")
            
            # تحليل ونقل إلى قاعدة البيانات
            for repo in results[:10]:  # أول 10 فقط
                analysis = self.github.analyze_repository(repo)
                if analysis['score'] >= 15:
                    self.db.add_repository(analysis)
                    print(f"  ✓ مضاف: {analysis['name']} (جودة: {analysis['score']})")
            
            # حساب الإحصائيات
            stats = self.db.get_statistics()
            print(f"📊 إحصائيات النظام:")
            print(f"   • مشاريع محفوظة: {stats['total_repositories']}")
            print(f"   • تعلمات محفوظة: {stats['total_learnings']}")
            
            # الانتظار قبل الدورة التالية
            if i < iterations - 1:
                print(f"⏳ الانتظار {delay} ثانية...")
                import time
                time.sleep(delay)
        
        print(f"\n✅ دورة التعلم مكتملة")
        self.print_summary()
    
    def print_summary(self):
        stats = self.db.get_statistics()
        print(f"\n📈 ملخص التطور:")
        print(f"   • مشاريع محفوظة: {stats['total_repositories']}")
        print(f"   • تعلمات محفوظة: {stats['total_learnings']}")
        if self.db.data.get('repositories'):
            top_repo = sorted(
                self.db.data['repositories'],
                key=lambda x: x.get('score', 0),
                reverse=True
            )[:3]
            print(f"   • أفضل المشاريع:")
            for repo in top_repo:
                print(f"     - {repo['name']} (جودة: {repo['score']})")


# Main execution
if __name__ == "__main__":
    print("🚀 بدء نظام التعلم الذاتي مع غيت هوب")
    loop = AutonomousLearningLoop()
    loop.run_cycle(iterations=3, delay=60)
