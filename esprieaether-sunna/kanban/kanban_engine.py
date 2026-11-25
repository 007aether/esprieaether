#!/usr/bin/env python3
"""SUPER KANBAN"""

import sqlite3, os
from datetime import datetime

DB = os.path.expanduser("~/ESPRIEAETHER/data/esprieaether.db")


class KanbanEngine:
    def __init__(self):
        self.db = DB
    
    def conn(self):
        return sqlite3.connect(self.db)
    
    def add_task(self, title, description="", priority="medium"):
        conn = self.conn()
        todo = conn.execute("SELECT id FROM columns WHERE name='TODO'").fetchone()
        tid = conn.execute("INSERT INTO tasks (board_id, column_id, title, description, priority, status) VALUES (1, ?, ?, ?, ?, 'todo')",
                          (todo[0] if todo else None, title, description, priority)).lastrowid
        conn.commit()
        conn.close()
        return tid
    
    def move_task(self, task_id, status):
        conn = self.conn()
        col = conn.execute("SELECT id FROM columns WHERE name=?", (status.upper(),)).fetchone()
        if col:
            conn.execute("UPDATE tasks SET column_id=?, status=? WHERE id=?", (col[0], status, task_id))
            conn.commit()
        conn.close()
    
    def complete_task(self, task_id, result=""):
        conn = self.conn()
        conn.execute("UPDATE tasks SET status='done', result=?, completed_at=? WHERE id=?",
                    (result, datetime.now().isoformat(), task_id))
        conn.commit()
        conn.close()
    
    def get_task(self, task_id):
        conn = self.conn()
        t = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        conn.close()
        return t
    
    def list_tasks(self, status=None):
        conn = self.conn()
        if status:
            tasks = conn.execute("SELECT id,title,description,priority,status FROM tasks WHERE status=? ORDER BY id", (status,)).fetchall()
        else:
            tasks = conn.execute("SELECT id,title,description,priority,status FROM tasks ORDER BY id").fetchall()
        conn.close()
        return tasks
    
    def list_agents(self):
        conn = self.conn()
        a = conn.execute("SELECT id,name,role,model,status FROM agents ORDER BY name").fetchall()
        conn.close()
        return a
    
    def print_board(self):
        todo = self.list_tasks("todo")
        doing = self.list_tasks("doing")
        done = self.list_tasks("done")
        print("\n" + "=" * 80)
        print("  📋 SUPER KANBAN — ESPRIEAETHER")
        print("=" * 80)
        w = 25
        print(f"\n{'TODO (' + str(len(todo)) + ')':<{w}} | {'DOING (' + str(len(doing)) + ')':<{w}} | {'DONE (' + str(len(done)) + ')':<{w}}")
        print("-" * 80)
        def fmt(t):
            if not t: return ""
            icon = {"critical": "🔥", "high": "⚡", "medium": "•", "low": "·"}.get(t[3], "•")
            return f"{icon} [{t[0]}] {t[1][:w-8]}"
        mx = max(len(todo), len(doing), len(done), 1)
        for i in range(min(mx, 15)):
            a = fmt(todo[i]) if i < len(todo) else ""
            b = fmt(doing[i]) if i < len(doing) else ""
            c = fmt(done[i]) if i < len(done) else ""
            print(f"{a:<{w}} | {b:<{w}} | {c:<{w}}")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    KanbanEngine().print_board()
