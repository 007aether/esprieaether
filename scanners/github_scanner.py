#!/usr/bin/env python3
"""
GITHUB SCANNER - Scan GitHub repos for tools, exploits, airdrops
"""

import requests
import sqlite3
import os
from datetime import datetime

DB = os.path.expanduser("~/ESPRIEAETHER/data/esprieaether.db")


class GitHubScanner:
    def __init__(self):
        self.db = DB
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS github_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                query TEXT,
                repo_name TEXT,
                description TEXT,
                stars INTEGER,
                url TEXT,
                language TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def search(self, query, language=None, min_stars=100, limit=10):
        """Search GitHub repos"""
        print(f"🔍 Searching GitHub: '{query}' (min ⭐{min_stars})")
        
        url = "https://api.github.com/search/repositories"
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": limit
        }
        if language:
            params["q"] += f" language:{language}"
        if min_stars:
            params["q"] += f" stars:>{min_stars}"
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                repos = data.get("items", [])
                
                conn = sqlite3.connect(self.db)
                for repo in repos:
                    conn.execute('''
                        INSERT INTO github_scans (query, repo_name, description, stars, url, language)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        query,
                        repo["full_name"],
                        repo["description"] or "",
                        repo["stargazers_count"],
                        repo["html_url"],
                        repo["language"] or "unknown"
                    ))
                conn.commit()
                conn.close()
                
                return repos
            else:
                print(f"❌ GitHub API error: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    def scan_ai_tools(self):
        """Scan for AI tools"""
        queries = [
            "ollama local llm",
            "llm agent framework",
            "autonomous ai agent",
            "local ai assistant",
        ]
        
        all_repos = []
        for q in queries:
            repos = self.search(q, min_stars=500, limit=5)
            all_repos.extend(repos)
            print(f"  ✅ Found {len(repos)} for '{q}'")
        
        return all_repos
    
    def show_recent(self, limit=20):
        conn = sqlite3.connect(self.db)
        cursor = conn.execute('''
            SELECT repo_name, stars, language, url, description
            FROM github_scans ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        repos = cursor.fetchall()
        conn.close()
        
        print(f"\n📊 Recent scans ({len(repos)}):")
        for r in repos:
            print(f"  ⭐ {r[1]:>6} | {r[2]:<12} | {r[0]}")
            print(f"    {r[4][:80] if r[4] else 'No description'}")
            print(f"    {r[3]}\n")


if __name__ == "__main__":
    gs = GitHubScanner()
    gs.scan_ai_tools()
    gs.show_recent(10)
