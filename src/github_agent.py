# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether - GitHub Agent
وكيل المزامنة والraf التلقائي لـ GitHub
"""
import os
import base64
import time
import logging
from datetime import datetime
from pathlib import Path

from github import Github, GithubException, InputGitTreeElement, Auth
from dotenv import load_dotenv

# ─── الإعدادات ───
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "ather007/esprieaether")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

logger = logging.getLogger("github_agent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


class GitHubAgent:
    """وكيل GitHub للraf التلقائي والمزامنة"""

    def __init__(self, token: str = None, repo_name: str = None):
        self.token = token or GITHUB_TOKEN
        self.repo_name = repo_name or GITHUB_REPO
        self.branch = GITHUB_BRANCH
        self.gh = None
        self.repo = None

        if not self.token:
            logger.warning("⚠️ GITHUB_TOKEN غير موجود في .env")
            return

        try:
            self.gh = Github(auth=Auth.Token(self.token))
            self.repo = self.gh.get_repo(self.repo_name)
            logger.info(f"✅ متصل بـ GitHub: {self.repo.full_name}")
        except GithubException as e:
            logger.error(f"❌ فشل الاتصال بـ GitHub: {e}")

    # ─────────────────────────────────────
    #  فحص الحالة
    # ─────────────────────────────────────
    def ping(self) -> dict:
        """wright الاتصال بـ GitHub"""
        if not self.gh:
            return {"status": "error", "message": "لا يوجد token"}

        try:
            user = self.gh.get_user()
            repo = self.repo
            return {
                "status": "online",
                "user": user.login,
                "repo": repo.full_name,
                "branch": self.branch,
                "rate_limit": self.gh.get_rate_limit().core
            }
        except GithubException as e:
            if e.status == 429:
                retry_after = int(e.headers.get("Retry-After", 300))
                logger.warning(f"⚠️ تلقي رمز 429 - الانتظار {retry_after} ثانية...")
                time.sleep(retry_after)
                return self.ping()  # حاول مجدداً بعد الانتظار
            else:
                logger.error(f"❌ فشل الاتصال بـ GitHub: {e}")
                return {"status": "error", "message": str(e)}