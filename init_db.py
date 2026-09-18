#!/usr/bin/env python3
"""ESPRIEAETHER Database"""

import sqlite3
import os

DB = os.path.expanduser("~/ESPRIEAETHER/data/esprieaether.db")
os.makedirs(os.path.dirname(DB), exist_ok=True)

conn = sqlite3.connect(DB)
c = conn.cursor()

# Kanban
c.execute("CREATE TABLE IF NOT EXISTS boards (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, description TEXT, owner_agent TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
c.execute("CREATE TABLE IF NOT EXISTS columns (id INTEGER PRIMARY KEY AUTOINCREMENT, board_id INTEGER, name TEXT, position INTEGER, wip_limit INTEGER DEFAULT 0)")
c.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, board_id INTEGER, column_id INTEGER, title TEXT, description TEXT, priority TEXT DEFAULT 'medium', status TEXT DEFAULT 'todo', assigned_agent TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, started_at DATETIME, completed_at DATETIME, result TEXT)")

# Code
c.execute("CREATE TABLE IF NOT EXISTS code_projects (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, path TEXT, language TEXT, description TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
c.execute("CREATE TABLE IF NOT EXISTS code_generations (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, project_id INTEGER, prompt TEXT, generated_code TEXT, file_path TEXT, model TEXT, status TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS code_executions (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, project_id INTEGER, file_path TEXT, command TEXT, stdout TEXT, stderr TEXT, exit_code INTEGER, duration REAL)")

# Agents
c.execute("CREATE TABLE IF NOT EXISTS agents (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, role TEXT, model TEXT DEFAULT 'hermes3:latest', status TEXT DEFAULT 'idle', current_task_id INTEGER, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, last_active DATETIME)")

# Conversations
c.execute("CREATE TABLE IF NOT EXISTS conversations (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, user_input TEXT, ai_response TEXT, model TEXT, agent TEXT, response_time REAL)")

# Seed
c.execute("INSERT OR IGNORE INTO boards (name, description, owner_agent) VALUES ('MAIN', 'Main board', 'esprie')")
bid = c.execute("SELECT id FROM boards WHERE name='MAIN'").fetchone()[0]
for i, cn in enumerate(['TODO', 'DOING', 'DONE']):
    c.execute("INSERT OR IGNORE INTO columns (board_id, name, position) VALUES (?, ?, ?)", (bid, cn, i))

for n, r, m in [
    ('hermes_core', 'Chat', 'hermes3:latest'),
    ('dolphin_creative', 'Creative', 'dolphin-llama3:8b'),
    ('deepseek_reasoner', 'Reasoning', 'deepseek-r1:7b'),
    ('kanban_master', 'Orchestration', 'hermes3:latest'),
    ('code_agent', 'Code', 'hermes3:latest'),
]:
    c.execute("INSERT OR IGNORE INTO agents (name, role, model) VALUES (?, ?, ?)", (n, r, m))

conn.commit()
conn.close()
print(f"✅ Database: {DB}")
