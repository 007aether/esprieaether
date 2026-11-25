#!/usr/bin/env python3
"""
ESPRIEAETHER ROBOTS SYSTEM
50 robots across 7 organ systems
Inspired by legacy AETHER v5
"""

import sqlite3
import os
from datetime import datetime

DB = os.path.expanduser("~/ESPRIEAETHER/data/esprieaether.db")


# ============ ROBOTS DEFINITION ============

ROBOTS = {
    # NERVOUS SYSTEM (3)
    "NERVOUS_01": {"name": "SYNAPSE", "system": "nervous", "role": "signal_routing"},
    "NERVOUS_02": {"name": "NEURON", "system": "nervous", "role": "decision_making"},
    "NERVOUS_03": {"name": "REFLEX", "system": "nervous", "role": "quick_response"},
    
    # CIRCULATORY SYSTEM (5)
    "CIRC_01": {"name": "HEART", "system": "circulatory", "role": "core_loop"},
    "CIRC_02": {"name": "ARTERY", "system": "circulatory", "role": "data_transfer"},
    "CIRC_03": {"name": "VEIN", "system": "circulatory", "role": "data_return"},
    "CIRC_04": {"name": "CAPILLARY", "system": "circulatory", "role": "micro_tasks"},
    "CIRC_05": {"name": "PLASMA", "system": "circulatory", "role": "buffer"},
    
    # SKELETAL SYSTEM (6)
    "SKEL_01": {"name": "BONE", "system": "skeletal", "role": "structure"},
    "SKEL_02": {"name": "JOINT", "system": "skeletal", "role": "connection"},
    "SKEL_03": {"name": "SPINE", "system": "skeletal", "role": "backbone"},
    "SKEL_04": {"name": "SKULL", "system": "skeletal", "role": "protection"},
    "SKEL_05": {"name": "RIBS", "system": "skeletal", "role": "guard"},
    "SKEL_06": {"name": "PELVIS", "system": "skeletal", "role": "balance"},
    
    # SENSORY SYSTEM (5)
    "SENS_01": {"name": "EYE", "system": "sensory", "role": "vision"},
    "SENS_02": {"name": "EAR", "system": "sensory", "role": "audio"},
    "SENS_03": {"name": "NOSE", "system": "sensory", "role": "detection"},
    "SENS_04": {"name": "TONGUE", "system": "sensory", "role": "analysis"},
    "SENS_05": {"name": "SKIN", "system": "sensory", "role": "touch"},
    
    # IMMUNE SYSTEM (5)
    "IMM_01": {"name": "WHITE_CELL", "system": "immune", "role": "defense"},
    "IMM_02": {"name": "ANTIBODY", "system": "immune", "role": "neutralize"},
    "IMM_03": {"name": "LYMPH", "system": "immune", "role": "cleanup"},
    "IMM_04": {"name": "SPLEEN", "system": "immune", "role": "filter"},
    "IMM_05": {"name": "THYMUS", "system": "immune", "role": "training"},
    
    # REPRODUCTIVE SYSTEM (6)
    "REP_01": {"name": "SEED", "system": "reproductive", "role": "spawn"},
    "REP_02": {"name": "EGG", "system": "reproductive", "role": "nurture"},
    "REP_03": {"name": "DNA", "system": "reproductive", "role": "config"},
    "REP_04": {"name": "GENE", "system": "reproductive", "role": "feature"},
    "REP_05": {"name": "CELL", "system": "reproductive", "role": "clone"},
    "REP_06": {"name": "SPORE", "system": "reproductive", "role": "backup"},
    
    # EXTERNAL (1 + 19 new = 20)
    "EXT_01": {"name": "NOTEBOOK", "system": "external", "role": "docs"},
    "EXT_02": {"name": "CRYPTO_TRADER", "system": "financial", "role": "trading"},
    "EXT_03": {"name": "STOCK_ANALYZER", "system": "financial", "role": "stocks"},
    "EXT_04": {"name": "NEWS_SCANNER", "system": "media", "role": "news"},
    "EXT_05": {"name": "TRANSLATOR", "system": "language", "role": "translate"},
    "EXT_06": {"name": "CODE_REVIEWER", "system": "programming", "role": "review"},
    "EXT_07": {"name": "DOC_GENERATOR", "system": "documentation", "role": "docs_gen"},
    "EXT_08": {"name": "TEST_RUNNER", "system": "testing", "role": "testing"},
    "EXT_09": {"name": "BACKUP_MANAGER", "system": "backup", "role": "backup"},
    "EXT_10": {"name": "LOG_ANALYZER", "system": "analysis", "role": "logs"},
    "EXT_11": {"name": "PERFORMANCE_MONITOR", "system": "monitoring", "role": "perf"},
    "EXT_12": {"name": "ALERT_MANAGER", "system": "alerts", "role": "alerts"},
    "EXT_13": {"name": "SCHEDULER", "system": "scheduling", "role": "schedule"},
    "EXT_14": {"name": "REPORT_GENERATOR", "system": "reports", "role": "reports"},
    "EXT_15": {"name": "DATA_VISUALIZER", "system": "visualization", "role": "viz"},
    "EXT_16": {"name": "API_GATEWAY", "system": "api", "role": "api"},
    "EXT_17": {"name": "CACHE_MANAGER", "system": "cache", "role": "cache"},
    "EXT_18": {"name": "QUEUE_MANAGER", "system": "queue", "role": "queue"},
    "EXT_19": {"name": "NOTIFICATION_CENTER", "system": "notifications", "role": "notify"},
    "EXT_20": {"name": "SYSTEM_OPTIMIZER", "system": "optimization", "role": "optimize"},

    # ── NEW: AI / AUTOMATION GENERATION (10) ──
    "AI_01": {"name": "HERMES_LINK", "system": "ai", "role": "hermes_bridge"},
    "AI_02": {"name": "PROMPT_ENGINEER", "system": "ai", "role": "prompt_craft"},
    "AI_03": {"name": "AGENT_SPAWNER", "system": "ai", "role": "spawn_agents"},
    "AI_04": {"name": "MODEL_ROUTER", "system": "ai", "role": "route_models"},
    "AI_05": {"name": "EMBEDDER", "system": "ai", "role": "embeddings"},
    "AI_06": {"name": "RAG_KEEPER", "system": "ai", "role": "knowledge_base"},
    "AI_07": {"name": "FINE_TUNER", "system": "ai", "role": "finetuning"},
    "AI_08": {"name": "EVAL_JUDGE", "system": "ai", "role": "model_eval"},
    "AI_09": {"name": "PROXY_MASTER", "system": "ai", "role": "api_proxy"},
    "AI_10": {"name": "TOOL_FORGE", "system": "ai", "role": "tool_builder"},
}


class RobotsSystem:
    def __init__(self):
        self.db = DB
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS robots (
                id TEXT PRIMARY KEY,
                name TEXT,
                system TEXT,
                role TEXT,
                status TEXT DEFAULT 'idle',
                tasks_completed INTEGER DEFAULT 0,
                last_active DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        
        # Register all robots
        for robot_id, info in ROBOTS.items():
            conn.execute('''
                INSERT OR IGNORE INTO robots (id, name, system, role, status)
                VALUES (?, ?, ?, ?, 'idle')
            ''', (robot_id, info["name"], info["system"], info["role"]))
        
        conn.commit()
        conn.close()
    
    def list_robots(self, system=None):
        conn = sqlite3.connect(self.db)
        if system:
            cursor = conn.execute('''
                SELECT id, name, system, role, status FROM robots 
                WHERE system = ? ORDER BY id
            ''', (system,))
        else:
            cursor = conn.execute('''
                SELECT id, name, system, role, status FROM robots ORDER BY system, id
            ''')
        robots = cursor.fetchall()
        conn.close()
        return robots
    
    def get_stats(self):
        conn = sqlite3.connect(self.db)
        cursor = conn.execute("SELECT COUNT(*) FROM robots")
        total = cursor.fetchone()[0]
        cursor = conn.execute("SELECT system, COUNT(*) FROM robots GROUP BY system")
        by_system = dict(cursor.fetchall())
        conn.close()
        return {"total": total, "by_system": by_system}
    
    def print_robots(self):
        stats = self.get_stats()
        print(f"\n{'='*70}")
        print(f"  🤖 ESPRIEAETHER ROBOTS — {stats['total']} registered")
        print(f"{'='*70}\n")
        
        for system, count in stats['by_system'].items():
            print(f"  📂 {system.upper()} ({count}):")
            robots = self.list_robots(system)
            for r in robots:
                icon = {"idle": "⚪", "active": "🟢", "error": "🔴"}.get(r[4], "⚪")
                print(f"    {icon} [{r[0]}] {r[1]:<20} — {r[3]}")
            print()


if __name__ == "__main__":
    rs = RobotsSystem()
    rs.print_robots()
