# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether - GitHub Evolve
البحث في GitHub عن تحسينات وتطبيقها
"""
import os
import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path.home() / "AETHER_V8"
load_dotenv(BASE_DIR / ".env")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SUGGESTIONS_FILE = BASE_DIR / "self_evolve_suggestions.json"
SEARCH_HISTORY = BASE_DIR / "github_evolve_history.json"

logger = logging.getLogger("github_evolve")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

# ─── GitHub API ───
GITHUB_API = "https://api.github.com"


class GitHubEvolve:
    """محرك البحث والتطوير من GitHub"""

    def __init__(self):
        self.token = GITHUB_TOKEN
        self.history = self._load_history()

    def _load_history(self) -> dict:
        if SEARCH_HISTORY.exists():
            try:
                return json.loads(SEARCH_HISTORY.read_text())
            except Exception:
                pass
        return {"searches": [], "last_run": None, "total_found": 0}

    def _save_history(self):
        SEARCH_HISTORY.write_text(
            json.dumps(self.history, indent=2, ensure_ascii=False)
        )

    def _headers(self) -> dict:
        h = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            h["Authorization"] = f"token {self.token}"
        return h

    # ─────────────────────────────────────
    #  بحث GitHub
    # ─────────────────────────────────────
    def search_repos(self, query: str, limit: int = 5) -> list:
        """البحث عن مستودعات"""
        try:
            r = requests.get(
                f"{GITHUB_API}/search/repositories",
                headers=self._headers(),
                params={
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": limit,
                },
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()

            results = []
            for repo in data.get("items", []):
                results.append({
                    "name": repo["full_name"],
                    "url": repo["html_url"],
                    "description": repo.get("description", "")[:200],
                    "stars": repo["stargazers_count"],
                    "language": repo.get("language", ""),
                    "updated": repo.get("updated_at", ""),
                    "topics": repo.get("topics", []),
                })

            logger.info(f"✅ بحث '{query}': {len(results)} نتيجة")
            return results
        except Exception as e:
            logger.error(f"❌ بحث فشل: {e}")
            return []

    def search_code(self, query: str, limit: int = 5) -> list:
        """البحث في الكود"""
        try:
            r = requests.get(
                f"{GITHUB_API}/search/code",
                headers=self._headers(),
                params={
                    "q": query,
                    "per_page": limit,
                },
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()

            results = []
            for item in data.get("items", []):
                results.append({
                    "repo": item["repository"]["full_name"],
                    "path": item["path"],
                    "url": item["html_url"],
                })
            return results
        except Exception as e:
            logger.error(f"❌ بحث كود فشل: {e}")
            return []

    # ─────────────────────────────────────
    #  بحثات محددة لـ EsprieAether
    # ─────────────────────────────────────
    def find_improvements(self) -> dict:
        """البحث عن تحسينات لـ EsprieAether"""
        searches = {
            "ai_agent": "ai agent python telegram bot automation",
            "crypto_farming": "crypto airdrop farming automation python",
            "local_llm": "ollama local llm agent framework",
            "self_evolve": "self-improving agent github python",
            "task_scheduler": "python autonomous task scheduler systemd",
        }

        all_results = {}
        for name, query in searches.items():
            results = self.search_repos(query, limit=3)
            if results:
                all_results[name] = results

        # سجل البحث
        self.history["searches"].append({
            "timestamp": datetime.now().isoformat(),
            "queries": list(searches.keys()),
            "results_count": sum(len(v) for v in all_results.values()),
        })
        self.history["last_run"] = datetime.now().isoformat()
        self.history["total_found"] = self.history.get("total_found", 0) + \
            sum(len(v) for v in all_results.values())
        self.history["searches"] = self.history["searches"][-20:]  # احتفظ بآخر 20
        self._save_history()

        return all_results

    # ─────────────────────────────────────
    #  تحليل عبر Cloud/JARVIS
    # ─────────────────────────────────────
    def analyze_with_ai(self, results: dict) -> list:
        """تحليل النتائج عبر Cloud"""
        from cloud_fallback import CloudFallback

        cloud = CloudFallback()

        # ابنِ الـ prompt
        prompt_lines = [
            "أنت مساعد تطوير لـ EsprieAether (نظام Python محلي).",
            "",
            "إليك نتائج بحث GitHub عن مشاريع مشابهة:",
        ]

        for category, repos in results.items():
            prompt_lines.append(f"\n## {category}")
            for repo in repos:
                prompt_lines.append(
                    f"- **{repo['name']}** ({repo['stars']}⭐): "
                    f"{repo['description'][:100]}"
                )

        prompt_lines.extend([
            "",
            "اقترح 3 تحسينات محددة لـ EsprieAether مبنية على هذه المشاريع.",
            "استخدم هذا التنسيق الصارم:",
            "[FILE: اسم_ملف] [ACTION: وصف_التعديل]",
            "",
            "الملفات المتاحة: bot.py, autonomous_loop.py, command_router.py, self_evolve.py, cloud_fallback.py",
        ])

        prompt = "\n".join(prompt_lines)

        # استشر Cloud
        result = cloud.ask(prompt, prefer="cloud")

        if result["status"] != "ok":
            logger.warning("⚠️ Cloud فشل — لا اقتراحات")
            return []

        # استخرج الاقتراحات
        suggestions = []
        response = result["answer"]

        for line in response.split("\n"):
            if "[FILE:" in line and "[ACTION:" in line:
                import re
                file_match = re.search(r'\[FILE:\s*([^\]]+)\]', line)
                action_match = re.search(r'\[ACTION:\s*([^\]]+)\]', line)

                if file_match and action_match:
                    suggestions.append({
                        "id": f"github_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(suggestions)}",
                        "timestamp": datetime.now().isoformat(),
                        "source": "github_evolve",
                        "file": file_match.group(1).strip(),
                        "action": action_match.group(1).strip(),
                        "raw": line.strip(),
                        "status": "pending",
                        "github_results": results,
                    })

        return suggestions

    def save_suggestions(self, suggestions: list) -> int:
        """حفظ الاقتراحات في الملف الرئيسي"""
        if not suggestions:
            return 0

        # اقرأ الملف الحالي
        existing = []
        if SUGGESTIONS_FILE.exists():
            try:
                existing = json.loads(SUGGESTIONS_FILE.read_text())
            except Exception:
                pass

        # أضف الجديد
        all_suggestions = existing + suggestions
        SUGGESTIONS_FILE.write_text(
            json.dumps(all_suggestions, indent=2, ensure_ascii=False)
        )

        return len(suggestions)

    # ─────────────────────────────────────
    #  الوظيفة الكاملة
    # ─────────────────────────────────────
    def run(self) -> dict:
        """دورة كاملة: بحث + تحليل + حفظ"""
        logger.info("🔍 بدء بحث GitHub...")

        # 1. ابحث
        results = self.find_improvements()
        if not results:
            return {"status": "no_results"}

        total = sum(len(v) for v in results.values())
        logger.info(f"📊 وجدت {total} مستودع")

        # 2. حلل
        logger.info("🧠 تحليل عبر Cloud...")
        suggestions = self.analyze_with_ai(results)

        if not suggestions:
            return {"status": "no_suggestions", "results_count": total}

        # 3. احفظ
        saved = self.save_suggestions(suggestions)
        logger.info(f"✅ {saved} اقتراح جديد")

        return {
            "status": "ok",
            "results_count": total,
            "suggestions_count": saved,
        }


if __name__ == "__main__":
    print("═" * 60)
    print("🔍 GitHub Evolve Test")
    print("═" * 60)

    evolve = GitHubEvolve()

    # اختبر البحث فقط
    print("\n▶ اختبار البحث...")
    results = evolve.find_improvements()

    for category, repos in results.items():
        print(f"\n## {category}")
        for repo in repos:
            print(f"  ⭐ {repo['name']} ({repo['stars']}⭐)")
            print(f"     {repo['description'][:80]}")
