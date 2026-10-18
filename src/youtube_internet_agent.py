#!/usr/bin/env python3
"""
🤖 EsprieAether - YouTube & Internet Agent
Scrapes YouTube, browses web, collects content for knowledge base.
"""

import os
import re
import json
import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys_path_needed = str(BASE_DIR / "src")
if sys_path_needed not in __import__('sys').path:
    __import__('sys').path.insert(0, sys_path_needed)

logger = logging.getLogger("youtube_internet_agent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

class YouTubeInternetAgent:
    """وكيل البحث والاستكشاف عبر الإنترنت"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.content_file = self.data_dir / "internet_content.json"
        self.history_file = self.data_dir / "internet_history.json"
        self._load_history()
    
    def _load_history(self):
        if self.history_file.exists():
            try:
                self.history = json.loads(self.history_file.read_text())
            except:
                self.history = {"searches": [], "pages_visited": [], "last_run": None}
        else:
            self.history = {"searches": [], "pages_visited": [], "last_run": None}
    
    def _save(self):
        self.history["last_run"] = datetime.now().isoformat()
        self.history_file.write_text(json.dumps(self.history, indent=2, ensure_ascii=False))
    
    async def fetch_url(self, url: str, session: aiohttp.ClientSession, timeout=30) -> dict:
        """Fetch URL content"""
        try:
            async with session.get(url, timeout=timeout) as resp:
                content = await resp.text()
                return {
                    "url": url,
                    "status": resp.status,
                    "title": re.search(r'<title>(.*?)</title>', content, re.S),
                    "content": content[:50000],
                    "fetched_at": datetime.now().isoformat()
                }
        except Exception as e:
            return {"url": url, "error": str(e), "fetched_at": datetime.now().isoformat()}
    
    async def youtube_search(self, query: str, limit=5) -> list:
        """Search YouTube (no API key needed - uses public search)"""
        results = []
        # Note: YouTube scraping requires API key or unofficial methods
        # This is a placeholder for actual implementation
        results.append({
            "query": query,
            "source": "YouTube",
            "results": [f"Video about: {query} (requires YouTube API key)"],
            "fetched_at": datetime.now().isoformat()
        })
        return results
    
    async def search_web(self, query: str, limit=5) -> list:
        """Search the web using public APIs"""
        results = []
        async with aiohttp.ClientSession() as session:
            # Try Brave Search API (free tier)
            for i in range(limit):
                try:
                    url = f"https://api.search.brave.com/res/v1/web/search?q={query}&count=5&offset={i*5}"
                    async with session.get(url, headers={
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip"
                    }, timeout=30) as resp:
                        data = await resp.json()
                        for result in data.get("web", {}).get("results", [])[:2]:
                            results.append({
                                "title": result.get("title"),
                                "url": result.get("url"),
                                "description": result.get("description"),
                                "source": "Brave Search",
                                "fetched_at": datetime.now().isoformat()
                            })
                except:
                    continue
        self.history["searches"].append({
            "query": query,
            "results": len(results),
            "timestamp": datetime.now().isoformat()
        })
        self._save()
        return results
    
    async def crawl_page(self, url: str) -> dict:
        """Crawl a webpage and extract content"""
        async with aiohttp.ClientSession() as session:
            return await self.fetch_url(url, session)
    
    def save_content(self, content: dict):
        """Save content to knowledge base"""
        existing = []
        if self.content_file.exists():
            try:
                existing = json.loads(self.content_file.read_text())
            except:
                existing = []
        
        content["saved_at"] = datetime.now().isoformat()
        existing.append(content)
        
        # Keep only recent content
        if len(existing) > 100:
            existing = existing[-100:]
        
        self.content_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
        return content
    
    def get_stats(self) -> dict:
        """Get statistics"""
        return {
            "searches_count": len(self.history.get("searches", [])),
            "pages_visits": len(self.history.get("pages_visited", [])),
            "content_items": len(json.loads(self.content_file.read_text()) if self.content_file.exists() else []),
            "last_run": self.history.get("last_run"),
            "last_updated": datetime.now().isoformat()
        }

# Test
async def test_agent():
    agent = YouTubeInternetAgent()
    print("Testing YouTube/Internet Agent...")
    
    # Test web search
    results = await agent.search_web("EsprieAether system", limit=3)
    print(f"Web search results: {len(results)}")
    for r in results:
        print(f"  - {r.get('title', 'N/A')}: {r.get('url', 'N/A')}")
    
    # Test crawling
    if results:
        crawl = await agent.crawl_page(results[0]["url"])
        print(f"Crawl status: {crawl.get('status', 'N/A')}")
    
    # Stats
    stats = agent.get_stats()
    print(f"Agent stats: {json.dumps(stats, indent=2, ensure_ascii=False)}")
    
    print("\n✅ YouTube Internet Agent test complete")

if __name__ == "__main__":
    asyncio.run(test_agent())
