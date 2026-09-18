#!/usr/bin/env python3
"""
ESPRIEAETHER SELF-EVOLUTION ENGINE
Learns from errors, improves continuously
Inspired by legacy aether_ai_brain.py
"""

import sqlite3
import os
import re
from datetime import datetime
from pathlib import Path

DB = os.path.expanduser("~/ESPRIEAETHER/data/esprieaether.db")


class SelfEvolution:
    def __init__(self):
        self.db = DB
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS evolution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                cycle INTEGER,
                issues_found INTEGER,
                improvements INTEGER,
                notes TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS improvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                file TEXT,
                line INTEGER,
                issue_type TEXT,
                description TEXT,
                applied INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()
    
    def analyze_code_quality(self, base_path=None):
        """Analyze ESPRIEAETHER code for issues"""
        if base_path is None:
            base_path = os.path.expanduser("~/ESPRIEAETHER")
        
        issues = []
        improvements = []
        
        for py_file in Path(base_path).rglob("*.py"):
            if "venv" in str(py_file) or "__pycache__" in str(py_file):
                continue
            
            try:
                src = py_file.read_text(errors="ignore")
                lines = src.split("\n")
                
                for i, line in enumerate(lines, 1):
                    if "TODO" in line.upper():
                        issues.append((py_file.name, i, "todo", line.strip()[:80]))
                    if "FIXME" in line.upper():
                        issues.append((py_file.name, i, "fixme", line.strip()[:80]))
                    if re.match(r'\s*except\s*:', line):
                        issues.append((py_file.name, i, "bare_except", "Security risk"))
                
                if len(lines) > 300:
                    improvements.append((py_file.name, 0, "long_file", f"{len(lines)} lines"))
            except Exception:
                pass
        
        # Save to DB
        conn = sqlite3.connect(self.db)
        for f, l, t, d in issues:
            conn.execute('''
                INSERT INTO improvements (file, line, issue_type, description)
                VALUES (?, ?, ?, ?)
            ''', (f, l, t, d))
        conn.commit()
        conn.close()
        
        return {"issues": len(issues), "improvements": len(improvements)}
    
    def run_cycle(self):
        """Run one evolution cycle"""
        conn = sqlite3.connect(self.db)
        cursor = conn.execute("SELECT COALESCE(MAX(cycle), 0) + 1 FROM evolution_log")
        cycle = cursor.fetchone()[0]
        conn.close()
        
        print(f"\n🧬 Evolution Cycle #{cycle}")
        print("=" * 50)
        
        result = self.analyze_code_quality()
        
        print(f"  Issues found: {result['issues']}")
        print(f"  Improvements: {result['improvements']}")
        
        conn = sqlite3.connect(self.db)
        conn.execute('''
            INSERT INTO evolution_log (cycle, issues_found, improvements, notes)
            VALUES (?, ?, ?, ?)
        ''', (cycle, result['issues'], result['improvements'], "Auto cycle"))
        conn.commit()
        conn.close()
        
        print(f"  ✅ Cycle #{cycle} complete\n")
        return result
    
    def get_history(self, limit=10):
        conn = sqlite3.connect(self.db)
        cursor = conn.execute('''
            SELECT cycle, issues_found, improvements, timestamp
            FROM evolution_log ORDER BY cycle DESC LIMIT ?
        ''', (limit,))
        history = cursor.fetchall()
        conn.close()
        return history


if __name__ == "__main__":
    evo = SelfEvolution()
    evo.run_cycle()
    
    print("📊 Recent cycles:")
    for c in evo.get_history(5):
        print(f"  #{c[0]} — Issues: {c[1]}, Improvements: {c[2]} ({c[3][:16]})")
