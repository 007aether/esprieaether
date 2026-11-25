#!/usr/bin/env python3
"""NEWS SCANNER - Fixed for RSS + Atom"""

import requests
import sqlite3
import os
import re
import sys
from datetime import datetime
from xml.etree import ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from policy_gate import check_url

DB = os.path.expanduser("~/ESPRIEAETHER/data/esprieaether.db")

FEEDS = {
    "Hacker News": "https://hnrss.org/frontpage",
    "TechCrunch": "https://techcrunch.com/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
}

NS = {"atom": "http://www.w3.org/2005/Atom"}


def _say(message: str) -> None:
    """Console sûre sous Windows/cp1252 (le daemon n'impose pas PYTHONIOENCODING)."""
    encoding = getattr(sys.stdout, "encoding", None) or "cp1252"
    try:
        print(message.encode(encoding, errors="replace").decode(encoding))
    except (LookupError, UnicodeError):
        print(message.encode("ascii", errors="replace").decode("ascii"))


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
        _say(f"NEWS Fetching: {name}")
        gate = check_url(url)
        if not gate.allowed:
            _say(f"  BLOCKED {gate.reason}")
            return []
        try:
            response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code != 200:
                _say(f"  ERROR HTTP {response.status_code}")
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
            _say(f"  ERROR: {e}")
            return []
    
    def scan_all(self):
        _say("\n" + "="*70)
        _say("  NEWS SCANNER")
        _say("="*70 + "\n")
        total = 0
        for name, url in FEEDS.items():
            news = self.fetch_feed(name, url, limit=3)
            total += len(news)
            _say(f"  OK {len(news)} items from {name}\n")
        return total
    
    def show_recent(self, limit=15):
        conn = sqlite3.connect(self.db)
        cursor = conn.execute('''
            SELECT source, title, link FROM news ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        news = cursor.fetchall()
        conn.close()
        _say(f"\nRecent news ({len(news)}):")
        for n in news:
            _say(f"  NEWS [{n[0]}] {n[1][:80]}")
            if n[2]:
                _say(f"     {n[2]}")
            _say()


if __name__ == "__main__":
    ns = NewsScanner()
    ns.scan_all()
    ns.show_recent(10)
