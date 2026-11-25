#!/usr/bin/env python3
"""NEWS SCANNER - Fixed for RSS + Atom"""

import requests
import sqlite3
import os
import re
from datetime import datetime
from xml.etree import ElementTree as ET

DB = os.path.expanduser("~/ESPRIEAETHER/data/esprieaether.db")

FEEDS = {
    "Hacker News": "https://hnrss.org/frontpage",
    "TechCrunch": "https://techcrunch.com/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
}

NS = {"atom": "http://www.w3.org/2005/Atom"}


class NewsScanner:
    def __init__(self):
        self.db = DB
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                source TEXT, title TEXT, link TEXT,
                summary TEXT, published TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def _get_text(self, item, tag):
        """Get text from RSS or Atom tag"""
        el = item.find(tag)
        if el is None:
            el = item.find(f"atom:{tag}", NS)
        return el.text if el is not None and el.text else ""
    
    def _get_link(self, item):
        """Get link from RSS or Atom"""
        el = item.find("link")
        if el is not None and el.text:
            return el.text.strip()
        el = item.find("atom:link", NS)
        if el is not None:
            return el.get("href", "")
        return ""
    
    def fetch_feed(self, name, url, limit=5):
        print(f"📰 Fetching: {name}")
        try:
            response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code != 200:
                print(f"  ❌ HTTP {response.status_code}")
                return []
            
            root = ET.fromstring(response.content)
            items = root.findall(".//item")
            if not items:
                items = root.findall(".//atom:entry", NS)
            
            news = []
            for item in items[:limit]:
                title = self._get_text(item, "title")
                link = self._get_link(item)
                desc = self._get_text(item, "description") or self._get_text(item, "summary")
                if desc:
                    desc = re.sub(r'<[^>]+>', '', desc)[:200]
                
                if not title:
                    continue
                
                news.append({
                    "source": name, "title": title, "link": link,
                    "summary": desc, "published": datetime.now().isoformat()
                })
            
            conn = sqlite3.connect(self.db)
            for n in news:
                conn.execute('''
                    INSERT INTO news (source, title, link, summary, published)
                    VALUES (?, ?, ?, ?, ?)
                ''', (n["source"], n["title"], n["link"], n["summary"], n["published"]))
            conn.commit()
            conn.close()
            return news
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return []
    
    def scan_all(self):
        print("\n" + "="*70)
        print("  📰 NEWS SCANNER")
        print("="*70 + "\n")
        total = 0
        for name, url in FEEDS.items():
            news = self.fetch_feed(name, url, limit=3)
            total += len(news)
            print(f"  ✅ {len(news)} items from {name}\n")
        return total
    
    def show_recent(self, limit=15):
        conn = sqlite3.connect(self.db)
        cursor = conn.execute('''
            SELECT source, title, link FROM news ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        news = cursor.fetchall()
        conn.close()
        print(f"\n📊 Recent news ({len(news)}):")
        for n in news:
            print(f"  📰 [{n[0]}] {n[1][:80]}")
            if n[2]:
                print(f"     {n[2]}")
            print()


if __name__ == "__main__":
    ns = NewsScanner()
    ns.scan_all()
    ns.show_recent(10)
