#!/usr/bin/env python3
"""
TESTS FOR SOCIAL LINKING MODULE
================================
Unit tests for social networking integration.
"""

import sys
import os
import json
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

try:
    from src.social_linker import SocialLinker
    SOCIAL_LINKER_AVAILABLE = True
except ImportError as e:
    SOCIAL_LINKER_AVAILABLE = False
    print(f"Import error: {e}")


class TestSocialLinkerConfig(unittest.TestCase):
    """Test SocialLinker configuration management."""

    def setUp(self):
        if not SOCIAL_LINKER_AVAILABLE:
            self.skipTest("SocialLinker not available")
        self.linker = SocialLinker()
        # Clear cache
        self.linker._cache = {}

    def test_initial_config(self):
        """Test initial social links configuration."""
        links = self.linker.links
        self.assertIn("social_links", links)
        self.assertIn("github", links["social_links"])
        self.assertIn("twitter", links["social_links"])
        self.assertIn("discord", links["social_links"])
        self.assertIn("website", links["social_links"])

    def test_add_social_link(self):
        """Test adding a new social link."""
        original_count = len(self.linker.links["social_links"])
        self.linker.add_social_link("telegram", "https://t.me/esprieaether")
        new_count = len(self.linker.links["social_links"])
        self.assertEqual(new_count, original_count + 1)
        self.assertIn("telegram", self.linker.links["social_links"])

    def test_remove_social_link(self):
        """Test removing a social link."""
        original_count = len(self.linker.links["social_links"])
        self.linker.remove_social_link("twitter")
        new_count = len(self.linker.links["social_links"])
        self.assertEqual(new_count, original_count - 1)
        self.assertNotIn("twitter", self.linker.links["social_links"])

    def test_get_all_links(self):
        """Test getting all social links."""
        links = self.linker.get_all_links()
        self.assertIsInstance(links, dict)
        self.assertGreater(len(links), 0)
        self.assertEqual(
            links.get("github"), "https://github.com/007aether/esprieaether"
        )

    def test_get_github_stats(self):
        """Test getting GitHub repository statistics."""
        stats = self.linker.get_github_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn("repo", stats)
        self.assertIn("stars", stats)
        self.assertIn("forks", stats)
        self.assertIn("language", stats)
        self.assertIn("last_updated", stats)

    def test_get_twitter_user(self):
        """Test getting Twitter user info."""
        info = self.linker.get_twitter_user("AetherSovereign")
        self.assertIsInstance(info, dict)
        self.assertIn("handle", info)
        self.assertIn("tweets_count", info)
        self.assertIn("followers", info)
        self.assertIn("last_checked", info)

    def test_get_youtube_stats(self):
        """Test getting YouTube channel stats."""
        stats = self.linker.get_youtube_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn("channel_id", stats)

    def test_get_discord_server(self):
        """Test getting Discord server info."""
        info = self.linker.get_discord_server()
        self.assertIsInstance(info, dict)
        self.assertIn("server_id", info)

    def test_sync_social_links(self):
        """Test syncing social links."""
        sync = self.linker.sync_social_links()
        self.assertIsInstance(sync, dict)
        self.assertIn("github", sync)
        self.assertIn("twitter", sync)
        self.assertIn("last_updated", sync)

    def test_test_all_links(self):
        """Test testing all links."""
        test_results = self.linker.test_all_links()
        self.assertIsInstance(test_results, dict)
        self.assertIn("links", test_results)
        self.assertIn("all_working", test_results)
        self.assertGreater(len(test_results["links"]), 0)


class TestSocialLinkerRunner(unittest.TestCase):
    """Test SocialLinkerRunner (Scenario 6 end-to-end)."""

    def setUp(self):
        if not SOCIAL_LINKER_AVAILABLE:
            self.skipTest("SocialLinker not available")
        from src.social_linker import SocialLinkerRunner
        self.runner = SocialLinkerRunner()

    def test_run_social_scenario(self):
        """Test running social linking scenario."""
        results = self.runner.run()
        self.assertIsInstance(results, dict)
        self.assertIn("social_links", results)
        self.assertIn("github_stats", results)


if __name__ == "__main__":
    unittest.main(verbosity=2)
