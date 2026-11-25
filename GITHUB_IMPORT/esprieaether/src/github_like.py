# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Agent OS
#
# ⚡ EsprieAether - GitHub Like Agent
# وكيل متابعة الإعجابات والاشارات على GitHub

import os
import json
import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "007aether/esprieaether")

logger = logging.getLogger("github_like")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

# Storage for likes
LIKES_FILE = BASE_DIR / "data" / "github_likes.json"

class GitHubLike:
    """محرك الإعجابات والاشارات على المستودعات"""

    def __init__(self):
        self.likes = self._load()
        self.checkpoint_file = BASE_DIR / "data" / "github_like_checkpoint.json"

    def _load(self) -> dict:
        """تحميل الإعجابات المحفوظة"""
        if LIKES_FILE.exists():
            try:
                return json.loads(LIKES_FILE.read_text())
            except Exception:
                pass
        return {"likes": {}, "count": 0, "last_updated": None}

    def _save(self):
        """حفظ الإعجابات"""
        self.likes["last_updated"] = datetime.now().isoformat()
        LIKES_FILE.parent.mkdir(parents=True, exist_ok=True)
        LIKES_FILE.write_text(json.dumps(self.likes, ensure_ascii=False, indent=2))

        # Checkpoint
        ck = {
            "updated": self.likes["last_updated"],
            "total_likes": self.likes.get("count", 0),
        }
        self.checkpoint_file.write_text(json.dumps(ck, ensure_ascii=False))

    def like_repo(self, repo_url: str, actor: str = "unknown", ip: str = "unknown") -> dict:
        """
        إعجاب بمستودع على GitHub
        Like a GitHub repository
        """
        if not repo_url.startswith("https://github.com/"):
            return {"status": "error", "message": "invalid repo URL"}

        # استخراج owner/repo
        parts = repo_url.rstrip("/").split("/")
        if len(parts) < 5:
            return {"status": "error", "message": "invalid repo URL format"}

        owner = parts[-2]
        repo = parts[-1]

        key = f"{owner}/{repo}"

        # لا تكرر الإعجاب نفسه
        if key in self.likes.get("likes", {}):
            like = self.likes["likes"][key]
            if actor in like.get("users_liked", []):
                return {"status": "already_liked", "message": "already liked"}

        # سجّل الإعجاب
        if key not in self.likes.get("likes", {}):
            self.likes["likes"][key] = {
                "repo": key,
                "title": repo,
                "repo_url": repo_url,
                "users_liked": [],
                "created_at": datetime.now().isoformat(),
            }
            self.likes["count"] = self.likes.get("count", 0) + 1

        like = self.likes["likes"][key]
        if actor not in like["users_liked"]:
            like["users_liked"].append(actor)
            logger.info(f"❤️ Liked {key} by {actor}")

        self._save()
        return {
            "status": "ok",
            "repo": key,
            "total_likes": like["users_liked"].__len__(),
            "message": f"❤️ {key} liked by {actor}" if actor != "unknown" else f"❤️ {key} liked"
        }

    def dislike_repo(self, repo_url: str, actor: str = "unknown") -> dict:
        """إلغاء الإعجاب بستارة/مستودع"""
        if not repo_url.startswith("https://github.com/"):
            return {"status": "error", "message": "invalid repo URL"}

        parts = repo_url.rstrip("/").split("/")
        if len(parts) < 5:
            return {"status": "error", "message": "invalid repo URL format"}

        key = f"{parts[-2]}/{parts[-1]}"

        if key in self.likes.get("likes", {}):
            like = self.likes["likes"][key]
            if actor in like.get("users_liked", []):
                like["users_liked"].remove(actor)
                self.likes["count"] = max(0, self.likes.get("count", 1) - 1)
                logger.info(f"❌ Unliked {key} by {actor}")
                self._save()
                return {"status": "ok", "repo": key, "message": f"Disliked {key}"}

        return {"status": "not_liked", "message": f"{key} not liked"}

    def get_likes(self, repo_url: str = None, limit: int = 50) -> dict:
        """جلب الإعجابات"""
        if repo_url:
            parts = repo_url.rstrip("/").split("/")
            key = f"{parts[-2]}/{parts[-1]}"
            if key in self.likes.get("likes", {}):
                return {"status": "ok", "likes": [self.likes["likes"][key]], "count": 1}
            return {"status": "not_found", "likes": [], "count": 0}

        # جلب جميع الإعجابات
        likes = self.likes.get("likes", {})
        items = list(likes.values())
        return {
            "status": "ok",
            "likes": items[-limit:] if limit else items,
            "count": len(items),
        }

    def get_stats(self) -> dict:
        """إحصائيات الإعجابات"""
        return {
            "total_likes": self.likes.get("count", 0),
            "total_users": len(set(u for l in self.likes.get("likes", {}).values()
                                    for u in l.get("users_liked", []))),
            "total_repos": len(self.likes.get("likes", {})),
            "last_updated": self.likes.get("last_updated"),
        }

    def reset_likes(self, reason: str = "admin") -> dict:
        """إعادة تعيين الإعجابات (للأدمن)"""
        self.likes = {"likes": {}, "count": 0, "last_updated": datetime.now().isoformat()}
        self._save()
        return {"status": "ok", "message": f"Likes reset by {reason}"}


if __name__ == "__main__":
    print("🔗 GitHub Like Agent")
    print("═" * 40)
    gl = GitHubLike()
    print(f"Stats: {gl.get_stats()}")
    print(f"Likes file: {LIKES_FILE}")
