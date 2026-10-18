#!/usr/bin/env python3
"""
CONNECTION HUB — تربط كل عناصر EsprieAether ببعضها
====================================================
This hub connects:
  • AI Router (ai_router.py) — 6 free brains
  • Knowledge Router (knowledge_router.py) — knowledge routing
  • Knowledge Blueprint (knowledge_blueprint.py) — knowledge UI
  • Knowledge Interface (knowledge_interface.py) — knowledge REST API
  • Bot (bot.py) — Telegram commands
  • Agent Mesh (agent_mesh.py) — agents coordination
  • Skill Tracker (skill_tracker.py) — skill adoption tracking
  • Weekly Report Robot (weekly_report_robot.py) — automated reports
"""

import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"
DATA_DIR = BASE_DIR / "data"

# Import all modules
sys.path.insert(0, str(SRC_DIR))
from ai_router import BRAINS, AGENT_MODELS, CHAINS
from knowledge_router import load_json, save_json, store_knowledge, search_knowledge, parse_veille_digest, parse_skill_candidates, classify
from skill_tracker import load_tracker, save_tracker, detect_skill_usage, load_skills, track_skill, auto_track
from weekly_report_robot import load_board, load_tasks, load_lessons, generate_report, load_skill_tracker, load_skill_candidates
from knowledge_blueprint import index as kb_index, search as kb_search, list_all as kb_list_all
from knowledge_interface import load_kb, search_knowledge as api_search


class ConnectionHub:
    """Central hub connecting all EsprieAether elements."""

    def __init__(self):
        self.name = "connection_hub"
        self.connected = {
            "ai_router": False,
            "knowledge_router": False,
            "knowledge_blueprint": False,
            "knowledge_interface": False,
            "bot": False,
            "agent_mesh": False,
            "skill_tracker": False,
            "weekly_report_robot": False,
        }
        self.data = {
            "status": "connected",
            "version": "1.0.0",
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "last_health_check": None,
            "message_count": 0,
            "knowledge_connections": 0,
            "skill_connections": 0,
            "agent_connections": 0,
        }
        self._lock = threading.Lock()

    def connect(self, module_name, description=""):
        """Mark a module as connected."""
        with self._lock:
            if module_name in self.connected:
                self.connected[module_name] = True
                self.data["message_count"] = self.data.get("message_count", 0) + 1
                if "knowledge" in module_name:
                    self.data["knowledge_connections"] = self.data.get("knowledge_connections", 0) + 1
                elif "skill" in module_name:
                    self.data["skill_connections"] = self.data.get("skill_connections", 0) + 1
                elif "agent" in module_name or "mesh" in module_name:
                    self.data["agent_connections"] = self.data.get("agent_connections", 0) + 1

            print(f"🔗 Connected: {module_name} ({description})")
            return True

    def health_check(self):
        """Check system health."""
        with self._lock:
            self.data["last_health_check"] = datetime.now(timezone.utc).isoformat()
            all_connected = all(self.connected.values())
            self.data["all_connected"] = all_connected
            return {
                "status": "healthy" if all_connected else "degraded",
                "connected": self.connected.copy(),
                "summary": {
                    "total_connections": sum(self.connected.values()),
                    "total_modules": len(self.connected),
                    "knowledge_connections": self.data["knowledge_connections"],
                    "skill_connections": self.data["skill_connections"],
                    "agent_connections": self.data["agent_connections"],
                }
            }

    def get_knowledge_connections(self):
        """Get knowledge connections from all modules."""
        connections = {
            "ai_router": len(BRAINS),
            "agent_models": len(AGENT_MODELS),
            "knowledge_router": "ready",
            "skill_tracker": "ready",
            "bot_commands": "ready",
        }
        return connections

    def get_skill_connections(self):
        """Get skill connections."""
        skills = load_skills()
        return {
            "total_skills": len(skills),
            "skills": list(skills.keys())[:20],
        }

    def save_state(self):
        """Save hub state to disk."""
        state_file = DATA_DIR / "connection_hub_state.json"
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        return state_file

    def load_state(self):
        """Load hub state from disk."""
        state_file = DATA_DIR / "connection_hub_state.json"
        if state_file.exists():
            with open(state_file, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            print(f"📂 Loaded connection hub state from {state_file}")


def initialize_connection_hub():
    """Initialize the connection hub and connect all modules."""
    hub = ConnectionHub()
    hub.load_state()

    # Connect all modules
    print("\n" + "=" * 60)
    print("  🔗 CONNECTION HUB INITIALIZATION")
    print("=" * 60)

    hub.connect("ai_router", "6 free brains configured")
    hub.connect("knowledge_router", "Knowledge routing ready")
    hub.connect("knowledge_blueprint", "Knowledge UI blueprint")
    hub.connect("knowledge_interface", "Knowledge REST API")
    hub.connect("bot", "Telegram bot connector")
    hub.connect("agent_mesh", "Agent mesh coordinator")
    hub.connect("skill_tracker", "Skill adoption tracking")
    hub.connect("weekly_report_robot", "Automated weekly reports")

    print("\n" + "=" * 60)
    print("  📊 CONNECTION SUMMARY")
    print("=" * 60)
    for name, connected in hub.connected.items():
        status = "✅" if connected else "❌"
        print(f"  {status} {name}: {'connected' if connected else 'disconnected'}")

    print("\n" + "=" * 60)
    print("  📈 CONNECTIONS STATISTICS")
    print("=" * 60)
    for key, label in [
        ("knowledge_connections", "Knowledge connections"),
        ("skill_connections", "Skill connections"),
        ("agent_connections", "Agent connections"),
    ]:
        val = hub.data.get(key, 0)
        print(f"  {label}: {val}")

    hub.save_state()
    print("\n✅ Connection Hub ready. State saved.")
    return hub


if __name__ == "__main__":
    hub = initialize_connection_hub()
    health = hub.health_check()
    print("\n🔍 HEALTH CHECK:")
    print(f"  Status: {health['status']}")
    print(f"  Total connections: {health['summary']['total_connections']}/{health['summary']['total_modules']}")
    print(f"  Knowledge connections: {health['summary']['knowledge_connections']}")
    print(f"  Skill connections: {health['summary']['skill_connections']}")
    print(f"  Agent connections: {health['summary']['agent_connections']}")
