#!/usr/bin/env python3
"""
ESPRIEAETHER SECURITY SCANNER
Scans code for vulnerabilities
Inspired by legacy aether_security_scanner.py
"""

import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

DB = os.path.expanduser("~/ESPRIEAETHER/data/esprieaether.db")

# Vulnerability patterns
PATTERNS = {
    "hardcoded_password": r'password\s*=\s*["\'][^"\']+["\']',
    "hardcoded_api_key": r'api_key\s*=\s*["\'][^"\']+["\']',
    "hardcoded_token": r'token\s*=\s*["\'][^"\']+["\']',
    "sql_injection": r'execute\s*\(\s*["\'].*%s.*["\']',
    "eval_usage": r'\beval\s*\(',
    "exec_usage": r'\bexec\s*\(',
    "subprocess_shell": r'subprocess\.(run|call|Popen)\s*\([^)]*shell\s*=\s*True',
    "insecure_random": r'random\.(random|randint|choice)\s*\(',
    "pickle_load": r'pickle\.load',
    "os_system": r'os\.system\s*\(',
}


class SecurityScanner:
    def __init__(self):
        self.db = DB
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS security_findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                file TEXT,
                line INTEGER,
                issue_type TEXT,
                severity TEXT,
                snippet TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def scan_file(self, filepath):
        findings = []
        try:
            content = Path(filepath).read_text(errors="ignore")
            lines = content.split("\n")
            
            for i, line in enumerate(lines, 1):
                for issue_type, pattern in PATTERNS.items():
                    if re.search(pattern, line, re.IGNORECASE):
                        # Determine severity
                        severity = "HIGH" if issue_type in [
                            "hardcoded_password", "hardcoded_api_key", 
                            "hardcoded_token", "sql_injection"
                        ] else "MEDIUM"
                        
                        findings.append({
                            "file": os.path.basename(filepath),
                            "line": i,
                            "issue_type": issue_type,
                            "severity": severity,
                            "snippet": line.strip()[:100]
                        })
        except Exception:
            pass
        return findings
    
    def scan_directory(self, base_path=None):
        if base_path is None:
            base_path = os.path.expanduser("~/ESPRIEAETHER")
        
        print(f"\n🔒 Scanning: {base_path}")
        print("=" * 60)
        
        all_findings = []
        py_files = list(Path(base_path).rglob("*.py"))
        
        for py_file in py_files:
            if "venv" in str(py_file) or "__pycache__" in str(py_file):
                continue
            findings = self.scan_file(py_file)
            all_findings.extend(findings)
        
        # Save to DB
        if all_findings:
            conn = sqlite3.connect(self.db)
            for f in all_findings:
                conn.execute('''
                    INSERT INTO security_findings (file, line, issue_type, severity, snippet)
                    VALUES (?, ?, ?, ?, ?)
                ''', (f['file'], f['line'], f['issue_type'], f['severity'], f['snippet']))
            conn.commit()
            conn.close()
        
        # Print summary
        by_severity = {}
        by_type = {}
        for f in all_findings:
            by_severity[f['severity']] = by_severity.get(f['severity'], 0) + 1
            by_type[f['issue_type']] = by_type.get(f['issue_type'], 0) + 1
        
        print(f"\n📊 Found {len(all_findings)} findings:")
        for sev, count in by_severity.items():
            icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(sev, "⚪")
            print(f"  {icon} {sev}: {count}")
        
        print(f"\n📋 By type:")
        for t, count in sorted(by_type.items(), key=lambda x: -x[1]):
            print(f"  • {t}: {count}")
        
        return all_findings


if __name__ == "__main__":
    scanner = SecurityScanner()
    scanner.scan_directory()
