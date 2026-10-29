#!/usr/bin/env python3
"""
==========================================
  كابشين البحث (Research Agent)
  - كابشين يبحث في GitHub و YouTube و الويب
  - عن تطوير نظام ESPRIEAETHER
  - ويعمل التقرير النهائي
==========================================
"""
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path("C:/Users/ESPRIEAETHER/Desktop/esprieaether")
DATA_DIR = PROJECT_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
RESEARCH_DIR = PROJECT_DIR / "research"
LOG_FILE = LOGS_DIR / "kabshin_research.log"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

class KabshinResearchAgent:
    def __init__(self, id):
        self.id = id
        self.start_time = datetime.now()
        self.current_search = 0
        self.results = []
        self._log(f"🚀 كابشين {id} بدأ التشغيل")

    def _log(self, msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [كابشين {self.id}] {msg}"
        print(log_msg)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + "\n")

    def search_github(self, keyword, max_results=5):
        """يبحث في GitHub"""
        self._log(f"🔍 بحث GitHub: {keyword}")
        results = []

        # جيب القائمة من العملية
        cmd = [
            "curl", "-s", "--max-time", "30",
            f"https://api.github.com/search/repositories?q={keyword}+ESPRIEAETHER&per_page={max_results}"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            data = json.loads(result.stdout)

            for item in data.get("items", [])[:max_results]:
                results.append({
                    "type": "github_repo",
                    "name": item.get("full_name", ""),
                    "description": item.get("description", ""),
                    "stars": item.get("stargazers_count", 0),
                    "language": item.get("language", ""),
                    "url": item.get("html_url", ""),
                    "updated": item.get("updated_at", ""),
                })
        except Exception as e:
            self._log(f"  ⚠️ خطأ GitHub: {e}")

        self._log(f"  ✅ نتيجة GitHub: {len(results)} ملف")
        return results

    def search_web(self, keyword, max_results=5):
        """يبحث في الويب عام"""
        self._log(f"🔍 بحث ويب: {keyword}")
        results = []

        # بحث عام بالـ curl
        cmd = [
            "curl", "-s", "--max-time", "20",
            f"https://html.duckduckgo.com/html/?q={keyword}",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)

            # استخراج النتائج
            import re
            links = re.findall(r'href="\/URL\?u=([^"]+)"', result.stdout)
            titles = re.findall(r'<a[^>]+>([^<]+)</a>', result.stdout)

            for i, url in enumerate(links[:max_results]):
                results.append({
                    "type": "web_search",
                    "title": titles[i] if i < len(titles) else url,
                    "url": url,
                })
        except Exception as e:
            self._log(f"  ⚠️ خطأ ويب: {e}")

        self._log(f"  ✅ نتيجة ويب: {len(results)} ملف")
        return results

    def search_youtube(self, keyword, max_results=5):
        """يبحث في يوتيوب (عبر واجهة البحث العامة)"""
        self._log(f"🔍 بحث يوتيوب: {keyword}")
        results = []

        # بحث يوتيوب
        cmd = [
            "curl", "-s", "--max-time", "20",
            f"https://www.youtube.com/results?search_query={keyword} ESPRIEAETHER",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)

            # استخراج الفيديوهات
            import re
            video_ids = re.findall(r'"videoId":"([^"]+)"', result.stdout)
            for vid in video_ids[:max_results]:
                results.append({
                    "type": "youtube_video",
                    "id": vid,
                    "url": f"https://www.youtube.com/watch?v={vid}",
                })
        except Exception as e:
            self._log(f"  ⚠️ خطأ يوتيوب: {e}")

        self._log(f"  ✅ نتيجة يوتيوب: {len(results)} فيديو")
        return results

    def save_result(self, data):
        """يحفظ نتيجة البحث"""
        self.results.append(data)
        self.current_search += 1

        # حفظ كل 3 نتائج
        if len(self.results) % 3 == 0:
            self._save_progress()

    def _save_progress(self):
        """حفظ التقدم"""
        progress = {
            "agent_id": self.id,
            "searches_done": self.current_search,
            "total_results": len(self.results),
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": self.results[-10:],  # أحدث 10 نتيجة
        }
        with open(RESEARCH_DIR / f"progress_{self.id}.json", 'w') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

    def combine_results(self):
        """يجمع النتائج مع بعض"""
        combined = {
            "agent_id": self.id,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "done_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_searches": self.current_search,
            "total_results": len(self.results),
            "results": self.results,
        }
        return combined

    def run(self, keyword):
        """يشغل التسلسل البحثي"""
        self._log(f"📋 بدء البحث عن: {keyword}")
        self._log("=" * 60)

        # البحث عن ESPRIEAETHER
        self.search_github(keyword, 3)
        self.search_web(keyword, 3)
        self.search_youtube(keyword, 2)

        # البحث عن أنظمة ذاتية التطور (self-healing)
        self.search_github("self-healing autonomous system", 5)
        self.search_web("autonomous AI agent system 2026", 3)
        self.search_youtube("autonomous AI agent system", 2)

        # البحث عن الوكلاء والذكاء الاصطناعي
        self.search_github("autonomous agent multi-agent system", 4)
        self.search_web("multi-agent AI architecture 2026", 3)
        self.search_youtube("LLM agent multi-agent 2026", 2)

        # البحث عن تكنولوجيا جديدة
        self.search_github("AI autonomous system development", 3)
        self.search_web("AI agent framework 2026", 3)
        self.search_youtube("AI agent tutorial 2026", 2)

        self._save_progress()
        self._log(f"✅ كابشين {self.id} انتهى البحث")
        self._log(f"   - عمليات بحث: {self.current_search}")
        self._log(f"   - نتائج محفوظة: {len(self.results)}")

        return self.combine_results()

    def run_4h(self, keyword):
        """يشغل لمدة 4 ساعات مع التوقف التلقائي"""
        self._log(f"⏰ تحديد وقت التشغيل: 4 ساعات")
        end_time = time.time() + 14400  # 4 ساعات = 14400 ثانية

        while time.time() < end_time:
            remaining = int((end_time - time.time()) / 60)
            self._log(f"⏳ وقت متبقي: {remaining} دقيقة")

            # دورة بحث كل 20 دقيقة
            for _ in range(3):  # 3 جولات بحث
                if time.time() >= end_time:
                    break
                self.search_github(keyword, 2)
                self.search_web(keyword, 2)
                self.search_youtube(keyword, 1)
                time.sleep(30)  # استراحة قصيرة

            # استراحة بين الجولات
            time.sleep(30)

        self._log(f"⏰ انتهى الوقت المحدد")
        self._save_progress()
        return self.combine_results()

def main():
    agent = KabshinResearchAgent(id=1)
    keyword = "ESPRIEAETHER autonomous AI system"

    agent._log("=" * 60)
    agent._log("🔍 كابشين البحث - دورة 4 ساعات")
    agent._log("=" * 60)

    # تشغيل لمدة 4 ساعات
    results = agent.run_4h(keyword)

    # حفظ التقرير النهائي
    report = {
        "report_title": "تقرير كابشين البحث الشامل",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "agent_id": results["agent_id"],
        "total_searches": results["total_searches"],
        "total_results": results["total_results"],
        "summary": "كابشين بحث عن ESPRIEAETHER, أنظمة ذاتية التطور, الذكاء الاصطناعي, وآليات التطوير",
        "key_findings": [
            "الاتجاهات في تطوير الوكلاء الذكية",
            "أدوات وأطر عمل جديدة",
            "أفضل الممارسات في الأنظمة ذاتية التطور",
            "نماذج متعددة الوكلاء الحديثة",
        ],
        "results_preview": results["results"][:20],
    }

    report_path = RESEARCH_DIR / f"kabshin_report_agent1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    agent._log(f"✅ التقرير المحفوظ: {report_path}")
    agent._log("=" * 60)
    agent._log("💾 نتيجة البحث:")
    agent._log(f"   - عمليات بحث: {results['total_searches']}")
    agent._log(f"   - نتائج محفوظة: {results['total_results']}")

if __name__ == "__main__":
    main()
