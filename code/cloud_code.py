#!/usr/bin/env python3
"""CLOUD CODE"""

import os, sys, sqlite3, subprocess, time
import ollama

BASE = os.path.expanduser("~/ESPRIEAETHER")
DB = f"{BASE}/data/esprieaether.db"
WORKSPACE = f"{BASE}/workspace"
MODEL = "hermes3:latest"
os.makedirs(WORKSPACE, exist_ok=True)


class CloudCode:
    def __init__(self):
        self.workspace = WORKSPACE
        self.model = MODEL
    
    def generate_code(self, prompt, language="python", file_path=None):
        print(f"🧠 Generating {language}...")
        start = time.time()
        try:
            r = ollama.chat(model=self.model, messages=[
                {"role": "system", "content": f"Expert {language} dev. Return ONLY code."},
                {"role": "user", "content": f"Generate {language} code for:\n{prompt}\n\nReturn ONLY code."}
            ])
            elapsed = time.time() - start
            code = r['message']['content'].strip()
            if code.startswith("```"):
                lines = code.split("\n")[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                code = "\n".join(lines)
            if file_path:
                fp = os.path.join(self.workspace, file_path)
                os.makedirs(os.path.dirname(fp), exist_ok=True)
                with open(fp, 'w') as f:
                    f.write(code)
                print(f"💾 Saved: {fp}")
            print(f"✅ Done in {elapsed:.2f}s")
            return code
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def execute(self, file_path, timeout=30):
        fp = os.path.join(self.workspace, file_path)
        if not os.path.exists(fp):
            return {"error": f"Not found: {fp}"}
        ext = os.path.splitext(file_path)[1]
        cmd_map = {".py": ["python3", fp], ".sh": ["bash", fp], ".js": ["node", fp]}
        cmd = cmd_map.get(ext)
        if not cmd:
            return {"error": f"Unsupported: {ext}"}
        print(f"▶️  Running: {' '.join(cmd)}")
        start = time.time()
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=self.workspace)
            return {"stdout": r.stdout, "stderr": r.stderr, "exit_code": r.returncode, "duration": time.time() - start}
        except subprocess.TimeoutExpired:
            return {"error": f"Timeout {timeout}s"}
        except Exception as e:
            return {"error": str(e)}
    
    def list_files(self):
        files = []
        for root, dirs, fnames in os.walk(self.workspace):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in fnames:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, self.workspace)
                files.append((rel, os.path.getsize(full)))
        return files
    
    def read_file(self, file_path):
        fp = os.path.join(self.workspace, file_path)
        if not os.path.exists(fp):
            return None
        with open(fp, 'r') as f:
            return f.read()
    
    def explain_code(self, file_path):
        fp = os.path.join(self.workspace, file_path)
        if not os.path.exists(fp):
            return f"❌ Not found: {fp}"
        with open(fp, 'r') as f:
            code = f.read()
        print(f"🧠 Analyzing...")
        try:
            r = ollama.chat(model=self.model, messages=[{"role": "user", "content": f"Explain:\n```\n{code}\n```"}])
            return r['message']['content']
        except Exception as e:
            return f"Error: {e}"
