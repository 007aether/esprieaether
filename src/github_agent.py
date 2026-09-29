"""
⚡ EsprieAether - GitHub Agent
وكيل المزامنة والرفع التلقائي لـ GitHub
"""
import os
import base64
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
    """وكيل GitHub للرفع التلقائي والمزامنة"""

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
        """فحص الاتصال بـ GitHub"""
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
                "stars": repo.stargazers_count,
                "private": repo.private,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ─────────────────────────────────────
    #  رفع ملف واحد
    # ─────────────────────────────────────
    def push_file(self, local_path: str, repo_path: str = None,
                  commit_message: str = None) -> dict:
        """رفع ملف واحد إلى GitHub"""
        if not self.repo:
            return {"status": "error", "message": "لا يوجد اتصال"}

        local = Path(local_path)
        if not local.exists():
            return {"status": "error", "message": f"الملف غير موجود: {local_path}"}

        repo_file = repo_path or str(local.relative_to(BASE_DIR))
        msg = commit_message or f"⚡ Auto-push: {repo_file} ({datetime.now().strftime('%Y-%m-%d %H:%M')})"

        try:
            # قراءة المحتوى
            with open(local, "rb") as f:
                content = f.read()

            # ترميز Base64 (مطلوب لـ GitHub API)
            encoded = base64.b64encode(content).decode("utf-8")

            # هل الملف موجود؟
            try:
                existing = self.repo.get_contents(repo_file, ref=self.branch)
                result = self.repo.update_file(
                    existing.path, msg, encoded, existing.sha, branch=self.branch
                )
                action = "updated"
            except GithubException:
                result = self.repo.create_file(
                    repo_file, msg, encoded, branch=self.branch
                )
                action = "created"

            return {
                "status": "ok",
                "action": action,
                "file": repo_file,
                "sha": result["commit"].sha[:8],
                "url": result["commit"].html_url,
            }
        except Exception as e:
            logger.error(f"فشل رفع {repo_file}: {e}")
            return {"status": "error", "message": str(e)}

    # ─────────────────────────────────────
    #  رفع عدة ملفات (commit واحد)
    # ─────────────────────────────────────
    def push_files(self, file_list: list, commit_message: str = None) -> dict:
        """رفع عدة ملفات في commit واحد — أسرع وأكثر كفاءة"""
        if not self.repo:
            return {"status": "error", "message": "لا يوجد اتصال"}

        try:
            # الحصول على آخر commit
            ref = self.repo.get_git_ref(f"heads/{self.branch}")
            base_tree = self.repo.get_git_tree(ref.object.sha)

            elements = []
            for file_path in file_list:
                local = Path(file_path) if isinstance(file_path, str) else file_path
                if not local.exists():
                    continue

                repo_path = str(local.relative_to(BASE_DIR))

                # قراءة المحتوى (نصي أو ثنائي)
                if local.suffix in (".png", ".jpg", ".jpeg", ".gif", ".ico"):
                    with open(local, "rb") as f:
                        data = base64.b64encode(f.read()).decode()
                    element = InputGitTreeElement(repo_path, "100644", "blob", data)
                else:
                    with open(local, "r", encoding="utf-8") as f:
                        content = f.read()
                    element = InputGitTreeElement(repo_path, "100644", "blob", content)

                elements.append(element)

            if not elements:
                return {"status": "error", "message": "لا ملفات صالحة"}

            msg = commit_message or f"⚡ Auto-push: {len(elements)} files ({datetime.now().strftime('%Y-%m-%d %H:%M')})"

            # إنشاء tree جديد
            new_tree = self.repo.create_git_tree(elements, base_tree)
            parent = self.repo.get_git_commit(ref.object.sha)
            commit = self.repo.create_git_commit(msg, new_tree, [parent])
            ref.edit(commit.sha)

            return {
                "status": "ok",
                "action": "committed",
                "files_count": len(elements),
                "sha": commit.sha[:8],
                "url": commit.html_url,
            }
        except Exception as e:
            logger.error(f"فشل رفع الملفات: {e}")
            return {"status": "error", "message": str(e)}

    # ─────────────────────────────────────
    #  مزامنة المشروع كاملاً
    # ─────────────────────────────────────
    def sync_project(self, include_patterns: list = None) -> dict:
        """مزامنة ملفات المشروع إلى GitHub"""
        if not self.repo:
            return {"status": "error", "message": "لا يوجد اتصال"}

        # الملفات الافتراضية
        default_files = [
            BASE_DIR / "src" / "jarvis_bridge.py",
            BASE_DIR / "src" / "web_interface.py",
            BASE_DIR / "src" / "bot.py",
            BASE_DIR / "src" / "github_agent.py",
            BASE_DIR / "run.sh",
            BASE_DIR / "STATUS.md",
        ]

        files = include_patterns or default_files
        valid_files = [f for f in files if Path(f).exists()]

        if not valid_files:
            return {"status": "error", "message": "لا ملفات للمزامنة"}

        return self.push_files(valid_files)


# ─────────────────────────────────────
#  اختبار سريع
# ─────────────────────────────────────
if __name__ == "__main__":
    print("═" * 60)
    print("⚡ ESPRIEAETHER - GitHub Agent Test")
    print("═" * 60)

    agent = GitHubAgent()

    if not agent.gh:
        print("❌ GITHUB_TOKEN غير موجود في .env")
        print("   أضف GITHUB_TOKEN=... في .env")
        exit(1)

    # فحص الاتصال
    status = agent.ping()
    print(f"\n▶ الحالة: {status}\n")

    if status["status"] == "online":
        print(f"👤 المستخدم: {status['user']}")
        print(f"📦 المستودع: {status['repo']}")
        print(f"🌿 الفرع: {status['branch']}")
        print(f"⭐ النجوم: {status['stars']}")
        print(f"🔒 خاص: {status['private']}")

        # اختبار رفع ملف صغير
        test_file = BASE_DIR / "STATUS.md"
        if test_file.exists():
            print(f"\n▶ اختبار رفع STATUS.md...")
            result = agent.push_file(str(test_file))
            print(f"   النتيجة: {result}")
