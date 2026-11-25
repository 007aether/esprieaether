#!/usr/bin/env python3
"""
subagent_builder.py - Executable Subagent Builder (AgentFactory-style)
================================================================================

Preserve successful task solutions as EXECUTABLE subagent CODE (not just
text).  Each subagent = a self-contained Python module with documented
CLI + tools + state.

Build from:
  - knowledge_base.md / observations
  - error logs / failed tasks
  - previously evolved skills

Usage:
  python subagent_builder.py --build              # build all
  python subagent_builder.py --build --skill NAME
"""

import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path("C:/Users/ESPRIEAETHER/Desktop/esprieaether")
DATA_DIR = PROJECT_DIR / "data"
SKILLS_DIR = DATA_DIR / "skills"

for d in (DATA_DIR, SKILLS_DIR):
    d.mkdir(parents=True, exist_ok=True)

STATE_FILE = DATA_DIR / "subagent_state.json"


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = "[%s] [%s] %s" % (ts, level, msg)
    print(line)
    with open(DATA_DIR / "subagent_build.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"built": [], "errors": []}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, default=str)


def base_agent(name, project):
    uid = uuid.uuid4().hex[:6]
    ts = datetime.now().isoformat()
    lines = []
    lines.append("#!/usr/bin/env python3")
    lines.append("'''")
    lines.append("_auto.gen_subagent_%s -- %s" % (uid, name))
    lines.append("AgentFactory-style executable subagent. Built: %s." % ts)
    lines.append("Run:  python %s.py        (default task)" % name)
    lines.append("      python %s.py --task TEXT" % name)
    lines.append("'''")
    lines.append("")
    lines.append("import json, os, sys")
    lines.append("from datetime import datetime")
    lines.append("from pathlib import Path")
    lines.append("")
    lines.append("PROJECT_DIR = Path(\"%s\")" % project)
    lines.append("DATA_DIR = PROJECT_DIR / 'data'")
    lines.append("SKILLS_DIR = DATA_DIR / 'skills'")
    lines.append("")
    lines.append("STATE = {'built': [], 'errors': []}")
    lines.append("")
    lines.append("def log(msg, level='INFO'):")
    lines.append("    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')")
    lines.append("    print('[%s] [%s] %s' % (ts, level, msg))")
    lines.append("    with open(SKILLS_DIR + '/subagent_build.log', 'a', encoding='utf-8') as f:")
    lines.append("        f.write('[%s] [%s] %s' % (ts, level, msg) + chr(10))")
    lines.append("")
    lines.append("def run(task):")
    lines.append("    # execute your logic here")
    lines.append("    log('Subagent %s started task: %s...' % (name, task[:40]))")
    lines.append("    return {'ok': True, 'task': task, 'ts': datetime.now().isoformat()}")
    lines.append("")
    lines.append("if __name__ == '__main__':")
    lines.append("    task = sys.argv[1] if len(sys.argv) > 1 else 'run'")
    lines.append("    res = run(task)")
    lines.append("    print(json.dumps(res, ensure_ascii=False, indent=2))")
    return "\n".join(lines) + "\n"


def build_skill(name, content_lines, tag="unknown"):
    path = SKILLS_DIR / ("%s.py" % name)
    agent = base_agent(name, "C:/Users/ESPRIEAETHER/Desktop/esprieaether")
    path.parent.mkdir(parents=True, exist_ok=True)
    content = ["# Knowledge source (%s):" % tag]
    for ln in content_lines[:120]:
        content.append("# " + ln)
    content.append("")
    path.write_text(agent + "\n" + "\n".join(content) + "\n", encoding="utf-8")
    os.chmod(path, 0o755)
    return path


def build_all():
    log("--- BUILD ALL SUBAGENTS ---")
    kb = Path("C:/Users/ESPRIEAETHER/ObsidianVault/EsprieAether")
    if not kb.exists():
        kb = Path("C:/Users/ESPRIEAETHER/Desktop/esprieaether/ObsidianVault/EsprieAether")
    if not kb.exists():
        kb = Path("C:/Users/ESPRIEAETHER/ObsidianVault/EsprieAether")
    names = []
    if kb.exists():
        for md in sorted(kb.glob("*.md")):
            if "_Index" in md.name or "graph" in md.name:
                continue
            stem = md.stem
            name = "skill_%s" % stem
            try:
                lines = md.read_text(encoding="utf-8", errors="ignore").splitlines()
                p = build_skill(name, lines, tag="knowledge")
                os.chmod(p, 0o755)
                names.append(name)
                log("built subagent: %s (%d lines)" % (name, len(lines)))
            except Exception as e:
                log("failed %s: %s" % (name, e), "ERROR")
    return {"built": names, "path": str(SKILLS_DIR)}


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--build":
        res = build_all()
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print("Usage: python subagent_builder.py --build")
