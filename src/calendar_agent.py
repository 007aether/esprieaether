"""Calendar & tasks agent — local SQLite-backed task list with reminders."""
import sqlite3, os
from datetime import datetime, timedelta
from pathlib import Path

DB = os.path.join(str(Path(__file__).parent.parent.parent), "ESPRIEAETHER", "data", "tasks.db")

def _init():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        due TEXT,
        priority TEXT DEFAULT 'normal',
        done INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

def add_task(title: str, due: str = None, priority: str = "normal") -> dict:
    _init()
    conn = sqlite3.connect(DB)
    cur = conn.execute(
        "INSERT INTO tasks (title, due, priority) VALUES (?, ?, ?)",
        (title, due, priority),
    )
    task_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"ok": True, "id": task_id, "title": title, "due": due, "priority": priority}

def list_tasks(show_done: bool = False) -> dict:
    _init()
    conn = sqlite3.connect(DB)
    if show_done:
        rows = conn.execute("SELECT id, title, due, priority, done, created_at FROM tasks ORDER BY id DESC").fetchall()
    else:
        rows = conn.execute("SELECT id, title, due, priority, done, created_at FROM tasks WHERE done=0 ORDER BY due, id").fetchall()
    conn.close()
    tasks = [
        {"id": r[0], "title": r[1], "due": r[2], "priority": r[3], "done": bool(r[4]), "created_at": r[5]}
        for r in rows
    ]
    return {"ok": True, "count": len(tasks), "tasks": tasks}

def complete_task(task_id: int) -> dict:
    _init()
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE tasks SET done=1 WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "completed": task_id}

def delete_task(task_id: int) -> dict:
    _init()
    conn = sqlite3.connect(DB)
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "deleted": task_id}

if __name__ == "__main__":
    import json, sys
    action = sys.argv[1] if len(sys.argv) > 1 else "list"
    if action == "add" and len(sys.argv) > 2:
        due = sys.argv[3] if len(sys.argv) > 3 else None
        r = add_task(sys.argv[2], due)
    elif action == "list":
        r = list_tasks()
    elif action == "done" and len(sys.argv) > 2:
        r = complete_task(int(sys.argv[2]))
    elif action == "delete" and len(sys.argv) > 2:
        r = delete_task(int(sys.argv[2]))
    else:
        r = {"error": "usage: calendar_agent.py <add|list|done|delete> [title/id] [due]"}
    print(json.dumps(r, ensure_ascii=False, indent=2))
