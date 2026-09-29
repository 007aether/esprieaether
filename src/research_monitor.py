"""
⚡ EsprieAether — Research Monitor
يفحص arXiv + HackerNews + Reddit + GitHub Trending
"""
import os
import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path.home() / "AETHER_V8"
STATE_FILE = BASE_DIR / "research_monitor_state.json"
REPORT_FILE = BASE_DIR / "research_reports.json"

logger = logging.getLogger("research_monitor")


class ResearchMonitor:
    def __init__(self):
        self.state = self._load_state()
        self.reports = self._load_reports()
    
    def _load_state(self):
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except Exception:
                pass
        return {"last_run": None, "seen_items": []}
    
    def _load_reports(self):
        if REPORT_FILE.exists():
            try:
                return json.loads(REPORT_FILE.read_text())
            except Exception:
                pass
        return []
    
    def _save(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2, ensure_ascii=False))
        REPORT_FILE.write_text(json.dumps(self.reports[-100:], indent=2, ensure_ascii=False))
    
    # ─────────── المصادر ───────────
    
    def fetch_arxiv(self, query="cat:cs.AI", limit=5):
        """أحدث أبحاث arXiv في AI"""
        try:
            url = f"http://export.arxiv.org/api/query?search_query={query}&start=0&max_results={limit}&sortBy=submittedDate&sortOrder=descending"
            r = requests.get(url, timeout=15)
            if r.status_code != 200:
                return []
            import xml.etree.ElementTree as ET
            root = ET.fromstring(r.text)
            ns = {"a": "http://www.w3.org/2005/Atom"}
            items = []
            for entry in root.findall("a:entry", ns):
                title = entry.find("a:title", ns).text.strip()
                link = entry.find("a:id", ns).text.strip()
                summary = entry.find("a:summary", ns).text.strip()[:300]
                published = entry.find("a:published", ns).text.strip()
                items.append({
                    "title": title, "url": link, "summary": summary,
                    "published": published, "source": "arxiv",
                })
            return items
        except Exception as e:
            logger.error(f"arXiv error: {e}")
            return []
    
    def fetch_hackernews(self, limit=5):
        """أعلى HackerNews stories"""
        try:
            r = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10)
            if r.status_code != 200:
                return []
            ids = r.json()[:limit]
            items = []
            for i in ids:
                d = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{i}.json", timeout=5).json()
                if d:
                    items.append({
                        "title": d.get("title", ""),
                        "url": d.get("url", f"https://news.ycombinator.com/item?id={i}"),
                        "score": d.get("score", 0),
                        "source": "hackernews",
                    })
            return items
        except Exception as e:
            logger.error(f"HN error: {e}")
            return []
    
    def fetch_reddit(self, subreddit="MachineLearning", limit=5):
        """أعلى posts في subreddit"""
        try:
            url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
            headers = {"User-Agent": "AETHER/1.0"}
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                return []
            data = r.json()
            items = []
            for child in data.get("data", {}).get("children", []):
                d = child.get("data", {})
                items.append({
                    "title": d.get("title", ""),
                    "url": f"https://reddit.com{d.get('permalink', '')}",
                    "score": d.get("score", 0),
                    "subreddit": subreddit,
                    "source": "reddit",
                })
            return items
        except Exception as e:
            logger.error(f"Reddit error: {e}")
            return []
    
    def fetch_github_trending(self, language="python"):
        """مستودعات GitHub الأكثر رواجًا"""
        try:
            headers = {"Accept": "application/vnd.github+json"}
            url = f"https://api.github.com/search/repositories?q=created:>{(datetime.now()-timedelta(days=7)).strftime('%Y-%m-%d')}+language:{language}&sort=stars&order=desc&per_page=5"
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                return []
            items = []
            for repo in r.json().get("items", [])[:5]:
                items.append({
                    "title": repo["full_name"],
                    "url": repo["html_url"],
                    "description": repo.get("description", ""),
                    "stars": repo["stargazers_count"],
                    "source": "github",
                })
            return items
        except Exception as e:
            logger.error(f"GitHub error: {e}")
            return []
    
    # ─────────── الدورة ───────────
    
    def run(self):
        """دورة كاملة: فحص كل المصادر"""
        logger.info("🔍 بدء دورة Research Monitor...")
        all_items = []
        all_items.extend(self.fetch_arxiv())
        all_items.extend(self.fetch_hackernews())
        all_items.extend(self.fetch_reddit("MachineLearning"))
        all_items.extend(self.fetch_reddit("LocalLLaMA"))
        all_items.extend(self.fetch_github_trending())
        
        # فلترة المكرر
        seen = set(self.state.get("seen_items", []))
        new_items = [i for i in all_items if i.get("title") not in seen]
        
        # تحديث الحالة
        for i in new_items:
            seen.add(i.get("title", ""))
        self.state["seen_items"] = list(seen)[-500:]
        self.state["last_run"] = datetime.now().isoformat()
        
        # حفظ التقرير
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_new": len(new_items),
            "items": new_items[:30],
        }
        self.reports.append(report)
        self._save()
        
        logger.info(f"✅ {len(new_items)} عنصر جديد")
        return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    rm = ResearchMonitor()
    report = rm.run()
    print(f"\n📊 إجمالي الجديد: {report['total_new']}")
    for i in report["items"][:10]:
        print(f"  [{i['source']}] {i.get('title', '?')[:70]}")
