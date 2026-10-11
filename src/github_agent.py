# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System


"""
⚡ EsprieAether - GitHub Agent
وكيل المزامنة والـ push التلقائي لـ GitHub.

طريقتان (بالتوالى):
  1. git CLI — يستعمل نفس الـ credentials لي شغالة محلياً (الأسهل، بلا token)
  2. PyGithub REST API — إذا وُجد GITHUB_TOKEN فـ .env
"""

import os
import subprocess
import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# ─── الإعدادات ───
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "007aether/esprieaether")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

logger = logging.getLogger("github_agent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


class GitHubAgent:
    """وكيل GitHub للـ push التلقائي والمزامنة"""

    def __init__(self, token: str = None, repo_name: str = None):
        self.token = token or GITHUB_TOKEN
        self.repo_name = repo_name or GITHUB_REPO
        self.branch = GITHUB_BRANCH
        self.gh = None
        self.repo = None

        # PyGithub (REST) — فقط إذا وُجد token
        if self.token:
            try:
                from github import Github, Auth
                self.gh = Github(auth=Auth.Token(self.token))
                self.repo = self.gh.get_repo(self.repo_name)
                logger.info(f"✅ PyGithub متصل: {self.repo.full_name}")
            except Exception as e:
                logger.warning(f"⚠️ PyGithub فشل ({e}) — نستعمل git CLI")

        self._ensure_remote()

    def _run_git(self, *args, timeout=120):
        """ينفّذ أمر git ف جذر المشروع"""
        return subprocess.run(
            ["git", *args],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def _ensure_remote(self):
        """يتأكد أن remote origin كيشير للريبو الصحيح"""
        try:
            r = self._run_git("remote", "get-url", "origin")
            current = (r.stdout or "").strip()
            want_https = f"https://github.com/{self.repo_name}.git"
            if current and self.repo_name not in current:
                self._run_git("remote", "set-url", "origin", want_https)
                logger.info(f"🔄 remote origin → {want_https}")
        except Exception as e:
            logger.warning(f"remote check failed: {e}")

    def git_status(self) -> dict:
        """حالة git: تغييرات، فرع، remote"""
        status_r = self._run_git("status", "--porcelain")
        branch_r = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        remote_r = self._run_git("remote", "get-url", "origin")
        changes = [l for l in (status_r.stdout or "").splitlines() if l.strip()]
        return {
            "status": "ok",
            "branch": (branch_r.stdout or "").strip(),
            "remote": (remote_r.stdout or "").strip(),
            "changes_count": len(changes),
            "changes": changes[:50],
            "clean": len(changes) == 0,
        }

    def push_files(self, files=None, message: str = "⚡ Auto-sync from EsprieAether"):
        """
        ي push المشروع كامل عبر git CLI (add -A + commit + push).
        """
        if not (BASE_DIR / ".git").exists():
            return {"status": "error", "message": "ماشي git repository"}

        self._run_git("add", "-A")

        st = self._run_git("status", "--porcelain")
        if not (st.stdout or "").strip():
            return {"status": "ok", "message": "لا توجد تغييرات", "files_count": 0}

        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        full_msg = f"{message} ({stamp})"
        cm = self._run_git(
            "-c", "user.name=007aether",
            "-c", "user.email=007aether@users.noreply.github.com",
            "commit", "-m", full_msg,
        )
        if cm.returncode != 0:
            return {"status": "error", "message": (cm.stderr or cm.stdout or "commit failed").strip()}

        sha_r = self._run_git("rev-parse", "--short", "HEAD")
        sha = (sha_r.stdout or "").strip()
        url = f"https://github.com/{self.repo_name}/commit/{sha}"

        env_push = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        try:
            ps = subprocess.run(
                ["git", "push", "origin", self.branch],
                cwd=str(BASE_DIR),
                capture_output=True, text=True,
                timeout=180, env=env_push,
            )
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "push timeout (180s)"}

        if ps.returncode == 0:
            return {"status": "ok", "sha": sha, "url": url, "message": full_msg}

        return {
            "status": "error",
            "sha": sha,
            "message": (ps.stderr or ps.stdout or "push failed").strip()[:300],
        }

    def ping(self) -> dict:
        """فحص الاتصال — git CLI هو المرجع"""
        try:
            gr = self._run_git("remote", "get-url", "origin")
            remote = (gr.stdout or "").strip()
            git_ok = gr.returncode == 0 and remote
        except Exception:
            git_ok = False
            remote = ""

        rest = None
        if self.gh:
            try:
                user = self.gh.get_user()
                rest = {"status": "online", "user": user.login}
            except Exception as e:
                rest = {"status": "error", "message": str(e)[:100]}

        return {
            "status": "ok" if git_ok else "error",
            "git_cli": "online" if git_ok else "error",
            "remote": remote,
            "repo": self.repo_name,
            "branch": self.branch,
            "rest_api": rest,
        }

    def push(self, files=None, message: str = "⚡ Auto-sync"):
        return self.push_files(files, message)


if __name__ == "__main__":
    ga = GitHubAgent()
    print(ga.git_status())
    print(ga.ping())
