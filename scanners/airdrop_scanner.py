#!/usr/bin/env python3
"""
AIRDROP SCANNER - Scan for crypto airdrops
"""

import requests
import sqlite3
import os
from datetime import datetime

DB = os.path.expanduser("~/ESPRIEAETHER/data/esprieaether.db")


class AirdropScanner:
    def __init__(self):
        self.db = DB
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS airdrops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                name TEXT,
                description TEXT,
                url TEXT,
                status TEXT,
                potential_value TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def scan_airdrops_io(self):
        """Scan airdrops.io via simple HTML parsing"""
        print("🪂 Scanning airdrops.io...")
        
        try:
            response = requests.get(
                "https://airdrops.io/latest/",
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            
            if response.status_code != 200:
                print(f"  ❌ HTTP {response.status_code}")
                return []
            
            # Simple regex for airdrop names + links
            import re
            html = response.text
            
            # Find h3 titles
            titles = re.findall(r'<h3[^>]*>([^<]+)</h3>', html)[:20]
            
            airdrops = []
            for title in titles:
                title = title.strip()
                if len(title) > 3 and len(title) < 100:
                    airdrops.append({
                        "name": title,
                        "description": "",
                        "url": f"https://airdrops.io/?s={title.replace(' ', '+')}",
                        "status": "active",
                        "potential_value": "$10-500"
                    })
            
            # Save to DB
            conn = sqlite3.connect(self.db)
            for a in airdrops:
                conn.execute('''
                    INSERT INTO airdrops (name, description, url, status, potential_value)
                    VALUES (?, ?, ?, ?, ?)
                ''', (a["name"], a["description"], a["url"], a["status"], a["potential_value"]))
            conn.commit()
            conn.close()
            
            return airdrops
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return []
    
    def scan_all(self):
        print("\n" + "="*70)
        print("  🪂 AIRDROP SCANNER")
        print("="*70 + "\n")
        
        airdrops = self.scan_airdrops_io()
        print(f"  ✅ Found {len(airdrops)} airdrops\n")
        return airdrops
    
    def show_recent(self, limit=20):
        conn = sqlite3.connect(self.db)
        cursor = conn.execute('''
            SELECT name, status, potential_value FROM airdrops 
            ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        airdrops = cursor.fetchall()
        conn.close()
        
        print(f"\n📊 Recent airdrops ({len(airdrops)}):")
        for a in airdrops:
            print(f"  🪂 {a[0]:<40} | {a[1]} | {a[2]}")


if __name__ == "__main__":
    ac = AirdropScanner()
    ac.scan_all()
    ac.show_recent(10)
