#!/usr/bin/env python3
"""
Sync EsprieAether project files to Obsidian vault.
Keeps local Obsidian vault up to date with project docs, reports, and state.
"""
import shutil
import os
import json
from pathlib import Path
from datetime import datetime

REPO = Path(r"C:\Users\ESPRIEAETHER\Desktop\esprieaether")
VAULT = Path(r"C:\Users\ESPRIEAETHER\ObsidianVault\EsprieAether")

# Map: relative source path -> relative destination path in vault
SYNC_MAP = {
    # Root docs
    "README.md": "README.md",
    "CLAUDE.md": "CLAUDE.md",
    "AGENTS.md": "AGENTS.md",
    "STATUS.md": "STATUS.md",
    "STATUS_WINDOWS.md": "STATUS_WINDOWS.md",
    "development_plan.md": "development_plan.md",
    "COMPLETE_SYSTEM_REPORT.md": "COMPLETE_SYSTEM_REPORT.md",
    "comprehensive_report.md": "comprehensive_report.md",
    "phase_report.md": "phase_report.md",
    "observing_system.md": "observing_system.md",
    "layout_system.md": "layout_system.md",
    "gods-eye-view.md": "gods-eye-view.md",
    "GITHUB_RESEARCH_COMPARE.md": "GITHUB_RESEARCH_COMPARE.md",
    # State files
    "autonomous_state.json": "autonomous_state.json",
    "self_evolve_suggestions.json": "self_evolve_suggestions.json",
    # Reports dir
    "data/logs": "Reports/logs",
    # Data files
    "data/autonome_evolve_state.json": "autonome_evolve_state.json",
    "data/skill_candidates.json": "skill_candidates.json",
    "data/skill_tracker.json": "skill_tracker.json",
    # Src agents docs
    "src/agents": "Agents/src",
    # Bots docs
    "bots": "Bots",
    # Docs folder
    "docs": "Docs",
    # Brains
    "brain": "Brains",
    # Services
    "src/ai_router.py": "Services/ai_router.md",
    "src/web_interface.py": "Services/web_interface.md",
    "src/sunna_api.py": "Services/sunna_api.md",
    "src/sunna_executor.py": "Services/sunna_executor.md",
    "src/cloud_desktop_agent.py": "Services/cloud_desktop.md",
    "src/autonome_evolve.py": "Services/autonome_evolve.md",
    "src/agent_mesh.py": "Services/agent_mesh.md",
    "src/orchestrator.py": "Services/orchestrator.md",
    "src/veritas_kanban.py": "Services/veritas_kanban.md",
    "src/integrations_adapter.py": "Services/integrations_adapter.md",
    "src/bot.py": "Services/bot.md",
    "src/watchdog.py": "Services/watchdog.md",
    # Sunna workspace
    "Sunna-Equipe-Industrial": "Sunna",
    # Work folder
    "work": "Work",
    # Research
    "research": "Research",
    # Strategies
    "strategies": "Strategies",
}

EXTS = {".md", ".json", ".txt", ".log", ".py", ".html", ".css", ".js"}


def should_sync(path: Path) -> bool:
    if path.is_dir():
        return True
    return path.suffix.lower() in EXTS


def sync_file(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copy2(src, dst)
        return True
    return False


def sync_all():
    results = []
    VAULT.mkdir(parents=True, exist_ok=True)

    for rel_src, rel_dst in SYNC_MAP.items():
        src = REPO / rel_src
        dst = VAULT / rel_dst

        if not src.exists():
            results.append(f"[skip] {rel_src} not found")
            continue

        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", ".git", "node_modules", ".venv"))
            results.append(f"[dir ] {rel_src} -> {rel_dst}")
        else:
            if sync_file(src, dst):
                results.append(f"[file] {rel_src} -> {rel_dst}")
            else:
                results.append(f"[fail] {rel_src}")

    # Write sync report
    report = VAULT / "_SyncReport.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report.write_text(f"# Sync Report\n\n**Last sync:** {ts}\n\n## Results\n\n" + "\n".join(f"- {r}" for r in results) + "\n")
    results.append(f"[report] _SyncReport.md")
    return results


if __name__ == "__main__":
    print("=== EsprieAether -> Obsidian Sync ===")
    res = sync_all()
    for r in res:
        print(r)
    print(f"=== Done: {len(res)} items synced to {VAULT} ===")
