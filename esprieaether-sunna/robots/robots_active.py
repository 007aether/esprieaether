#!/usr/bin/env python3
"""
ROBOTS ACTIVE - Task assignment for robots
"""

import sqlite3
import os
from datetime import datetime

DB = os.path.expanduser("~/ESPRIEAETHER/data/esprieaether.db")


class RobotsActive:
    def __init__(self):
        self.db = DB
    
    def assign_task(self, robot_id, task):
        """Assign a task to a robot"""
        conn = sqlite3.connect(self.db)
        conn.execute('''
            UPDATE robots
            SET status = 'active', last_active = ?, tasks_completed = tasks_completed
            WHERE id = ?
        ''', (datetime.now().isoformat(), robot_id))
        conn.commit()
        conn.close()
        return True
    
    def complete_task(self, robot_id):
        """Mark task as complete"""
        conn = sqlite3.connect(self.db)
        conn.execute('''
            UPDATE robots
            SET status = 'idle', tasks_completed = tasks_completed + 1
            WHERE id = ?
        ''', (robot_id,))
        conn.commit()
        conn.close()
        return True
    
    def get_active(self):
        conn = sqlite3.connect(self.db)
        cursor = conn.execute('''
            SELECT id, name, system, role, status, tasks_completed
            FROM robots WHERE status = 'active'
        ''')
        robots = cursor.fetchall()
        conn.close()
        return robots
    
    def get_stats(self):
        conn = sqlite3.connect(self.db)
        cursor = conn.execute('''
            SELECT status, COUNT(*) FROM robots GROUP BY status
        ''')
        stats = dict(cursor.fetchall())
        cursor = conn.execute('''
            SELECT SUM(tasks_completed) FROM robots
        ''')
        total_tasks = cursor.fetchone()[0] or 0
        conn.close()
        return {"by_status": stats, "total_tasks": total_tasks}
    
    def auto_assign(self, n=5):
        """Auto-assign tasks to idle robots"""
        conn = sqlite3.connect(self.db)
        cursor = conn.execute('''
            SELECT id, name FROM robots WHERE status = 'idle' LIMIT ?
        ''', (n,))
        idle = cursor.fetchall()
        conn.close()
        
        assigned = []
        for robot_id, name in idle:
            self.assign_task(robot_id, f"Auto task for {name}")
            assigned.append((robot_id, name))
        
        return assigned


if __name__ == "__main__":
    ra = RobotsActive()
    
    print("🤖 ROBOTS ACTIVE — Task Assignment")
    print("=" * 50)
    
    # Auto-assign
    assigned = ra.auto_assign(5)
    print(f"\n✅ Assigned {len(assigned)} tasks:")
    for r_id, name in assigned:
        print(f"  🟢 [{r_id}] {name} — active")
    
    # Stats
    stats = ra.get_stats()
    print(f"\n📊 Stats:")
    for status, count in stats['by_status'].items():
        print(f"  {status}: {count}")
    print(f"  Total tasks completed: {stats['total_tasks']}")
    
    # Show active
    active = ra.get_active()
    print(f"\n🟢 Active robots ({len(active)}):")
    for r in active:
        print(f"  • [{r[0]}] {r[1]} ({r[2]}) — {r[3]}")
