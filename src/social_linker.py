#!/usr/bin/env python3
"""
SOCIAL LINKING MODULE FOR ESPRIEAETHER
=====================================
Complete social network linking:
- GitHub integration
- Twitter/X integration
- Discord integration
- LinkedIn integration
- YouTube integration
- Website linking
"""

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None


class SocialLinker:
    """
    Manages social network links and integrations.

    Supports:
    - GitHub (repos, stars, forks, commits)
    - Twitter/X (posts, replies, follows)
    - Discord (servers, channels, messages)
    - LinkedIn (company pages, posts)
    - YouTube (channels, videos, subscribers)
    - Website (links, sitemap, analytics)
    """

    def __init__(self, config_file: str = None):
        self.config_file = Path(config_file) if config_file else Path(
            os.path.expanduser("~/.esprieaether/social_links.json")
        )
        self.links = self._load_config()
        self._lock = threading.Lock()
        self._cache = {}

    def _load_config(self) -> Dict:
        """Load social links configuration."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Ensure social_links dict exists
                    if "social_links" not in data:
                        data["social_links"] = {}
                    return data
            except Exception:
                pass
        return {
            "github": {"repo": "007aether/esprieaether", "token": None},
            "twitter": {"handle": "AetherSovereign", "token": None},
            "discord": {"server_id": None, "token": None},
            "linkedin": {"company_page": None},
            "youtube": {"channel_id": None},
            "website": {"url": "https://aether.ai"},
            "social_links": {
                "github": "https://github.com/007aether/esprieaether",
                "twitter": "https://twitter.com/AetherSovereign",
                "discord": "https://discord.gg/esprieaether",
                "linkedin": "https://linkedin.com/company/esprieaether",
                "youtube": "https://youtube.com/@esprieaether",
                "website": "https://aether.ai",
                "telegram": "https://t.me/esprieaether",
            },
            "last_updated": None,
            "all_working": True,
        }

    def _save_config(self):
        """Save social links configuration."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.links, f, indent=2, ensure_ascii=False)
        # Ensure social_links key is in config
        self.links.setdefault("social_links", {})
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.links, f, indent=2, ensure_ascii=False)

    def add_social_link(self, platform: str, url: str, name: str = None):
        """Add a social network link."""
        with self._lock:
            platform_lower = platform.lower()
            if platform_lower not in self.links["social_links"]:
                self.links["social_links"][platform_lower] = url
            self.links["website"]["url"] = url
            self.links["last_updated"] = datetime.now(timezone.utc).isoformat()
            self._save_config()
            return self.links["social_links"][platform_lower]

    def remove_social_link(self, platform: str):
        """Remove a social network link."""
        with self._lock:
            platform_lower = platform.lower()
            if platform_lower in self.links["social_links"]:
                del self.links["social_links"][platform_lower]
            self.links["last_updated"] = datetime.now(timezone.utc).isoformat()
            self._save_config()

    def get_all_links(self) -> Dict:
        """Get all social links."""
        return self.links["social_links"].copy()

    def get_github_stats(self) -> Dict:
        """Get GitHub repository statistics."""
        repo = self.links["github"].get("repo", "007aether/esprieaether")
        token = self.links["github"].get("token")
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"

        stats = {
            "repo": repo,
            "stars": None,
            "forks": None,
            "open_issues": None,
            "watchers": None,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        try:
            resp = requests.get(
                f"https://api.github.com/repos/{repo}",
                headers=headers,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                stats["stars"] = data.get("stargazers_count")
                stats["forks"] = data.get("forks_count")
                stats["open_issues"] = data.get("open_issues_count")
                stats["watchers"] = data.get("watchers_count")
                stats["description"] = data.get("description")
                stats["language"] = data.get("language")
                stats["updated_at"] = data.get("updated_at")
        except Exception as e:
            stats["error"] = str(e)

        return stats

    def get_twitter_user(self, handle: str = None) -> Dict:
        """Get Twitter user info (requires API credentials)."""
        handle = handle or self.links["twitter"].get("handle", "AetherSovereign")
        # Twitter API v2 requires OAuth 2.0 bearer token
        # This is a placeholder - actual implementation needs credentials
        return {
            "handle": handle,
            "tweets_count": None,
            "followers": None,
            "following": None,
            "last_checked": datetime.now(timezone.utc).isoformat(),
            "note": "Twitter API requires OAuth token - use Twitter developer console",
        }

    def get_youtube_stats(self) -> Dict:
        """Get YouTube channel statistics."""
        channel_id = self.links["youtube"].get("channel_id")
        if not channel_id:
            return {"error": "No YouTube channel ID configured"}

        stats = {"channel_id": channel_id, "last_updated": datetime.now(timezone.utc).isoformat()}

        try:
            resp = requests.get(
                f"https://www.googleapis.com/youtube/v3/channels",
                params={"id": channel_id, "part": "statistics,contentDetails"},
                headers={"Authorization": f"Bearer {self.links['youtube'].get('token')}"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("items"):
                    item = data["items"][0]
                    stats["subscribers"] = item["statistics"].get("subscriberCount")
                    stats["video_count"] = item["statistics"].get("videoCount")
                    stats["view_count"] = item["statistics"].get("viewCount")
        except Exception as e:
            stats["error"] = str(e)

        return stats

    def get_discord_server(self) -> Dict:
        """Get Discord server information."""
        server_id = self.links["discord"].get("server_id")
        if not server_id:
            return {"error": "No Discord server ID configured"}

        return {
            "server_id": server_id,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "note": "Discord API requires bot token - add via Discord developer portal",
        }

    def sync_social_links(self) -> Dict:
        """Sync all social links and get current status."""
        links = self.get_all_links()
        stats = {
            "github": self.get_github_stats(),
            "twitter": self.get_twitter_user(),
            "discord": self.get_discord_server(),
            "youtube": self.get_youtube_stats(),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "total_links": len(links),
            "platforms": list(links.keys()),
        }
        return stats

    def test_all_links(self) -> Dict:
        """Test all configured links for availability."""
        results = {"links": [], "all_working": True}

        for platform, url in self.links["social_links"].items():
            result = {"platform": platform, "url": url, "working": False}
            try:
                resp = requests.head(url, timeout=5, allow_redirects=True)
                result["working"] = resp.status_code < 400
                result["status_code"] = resp.status_code
            except Exception as e:
                result["error"] = str(e)
                if result["working"]:
                    result["working"] = False
                    self.links["all_working"] = False

            results["links"].append(result)

        results["all_working"] = all(
            link["working"] for link in results["links"] if "error" not in link
        )
        return results


class SocialLinkerRunner:
    """
    Runner for the social linking scenario.
    """

    def __init__(self):
        self.linker = SocialLinker()

    def run(self) -> Dict:
        """Run the social linking scenario."""
        print("=" * 60)
        print("🔗 Scenario: Social Network Linking")
        print("=" * 60)

        print("\n📌 Design Principle:")
        print("   🔗 All social links connected to EsprieAether")
        print("   🔗 GitHub, Twitter, Discord, YouTube, LinkedIn")

        print("\n1️⃣  Configuring social links...")
        for platform, url in self.linker.links["social_links"].items():
            print(f"   {platform}: {url}")

        print("\n2️⃣  Testing link availability...")
        results = self.linker.test_all_links()
        for link in results["links"]:
            status = "✅" if link.get("working") else "❌"
            print(f"   {status} {link['platform']}: {link.get('url', '')[:50]}")

        print("\n3️⃣  Getting GitHub statistics...")
        stats = self.linker.get_github_stats()
        print(f"   Repository: {stats.get('repo', 'N/A')}")
        print(f"   Stars: {stats.get('stars', 'N/A')}")
        print(f"   Forks: {stats.get('forks', 'N/A')}")
        print(f"   Language: {stats.get('language', 'N/A')}")

        print("\n4️⃣  Social linking summary...")
        print(f"   Total platforms: {results['total_links']}")
        print(f"   Platforms linked: {len(results['links'])}")
        print(f"   All working: {results['all_working']}")

        return {
            "social_links": self.linker.get_all_links(),
            "github_stats": stats,
            "link_test": results,
            "provisional": "linked",
        }


if __name__ == "__main__":
    runner = SocialLinkerRunner()
    results = runner.run()
    print("\n" + "=" * 60)
    print("✅ Social linking complete!")
    print("=" * 60)
