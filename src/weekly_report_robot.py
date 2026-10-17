#!/usr/bin/env python3
"""
WEEKLY REPORT ROBOT
--------------------
روبوت يجمع التقارير الأسبوعية للنظام:
- ملخص الأنشطة (board, tasks, knowledge)
- كتابة الدروس المست-conjugate
- تقرير لصالح الإنسان (الرئيسي)
- تحديث في الإحصائيات
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REPORT_FILE = DATA_DIR / "weekly_report.json"
SUMMARY_FILE = DATA_DIR / "weekly_summary.md"

AGENT = "weekly_report"


def load_board():
    """تحميل لوحة الوكلاء."""
    board_file = DATA_DIR / "agent_board.json"
    if board_file.exists():
        try:
            with open(board_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def load_tasks():
    """تحميل المهام المقترحة."""
    task_file = DATA_DIR / "agent_proposed_tasks.json"
    if task_file.exists():
        try:
            with open(task_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def load_lessons():
    """تحميل الدروس المست-conjugated."""
    lessons_file = DATA_DIR / "lessons.json"
    if lessons_file.exists():
        try:
            with open(lessons_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"seen": [], "diagnosed": 0, "fixes_proposed": 0}


def load_skill_tracker():
    """تحميل ملف تتبيل المهارات."""
    tracker_file = DATA_DIR / "skill_tracker.json"
    if tracker_file.exists():
        try:
            with open(tracker_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"skills": [], "adopted": [], "results": [], "last_updated": None}


def load_skill_candidates():
    """تحميل مرشحات المهارات."""
    skills_file = DATA_DIR / "skill_candidates.json"
    if skills_file.exists():
        try:
            with open(skills_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def generate_report():
    """توليد التقرير الأسبوعي."""
    print(f"\n📊 {AGENT} يجمع التقارير...")

    board = load_board()
    tasks = load_tasks()
    lessons = load_lessons()
    tracker = load_skill_tracker()
    candidates = load_skill_candidates()

    # الإحصائيات
    agent_count = len([m for m in board if isinstance(m, dict) and "agent" in m])
    message_count = len([m for m in board if isinstance(m, dict) and "text" in m])
    task_count = len(tasks)
    proposed_count = len([t for t in tasks if t.get("status") == "proposed"])
    done_count = len([t for t in tasks if t.get("status") == "done"])

    skill_count = len([s for s in tracker.get("skills", []) if s.get("outcome") == "adopted"])
    total_skills = len([s for s in tracker.get("skills", [])])

    # استخراج ملاحظات الأسبوع
    seen_lessons = lessons.get("seen", [])
    recent_lessons = seen_lessons[-10:] if seen_lessons else []

    # تقرير HTML
    report_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>تقرير الأسبوع - EsprieAether</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; color: #333; }}
            .container {{ max-width: 1000px; margin: 0 auto; }}
            h1 {{ color: #2c3e50; }}
            h2 {{ color: #34495e; }}
            .card {{ background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .stat {{ display: inline-block; width: 30%; padding: 15px; margin: 10px; background: #f8f9fa; border-radius: 8px; text-align: center; }}
            .stat .number {{ font-size: 28px; font-weight: bold; color: #3498db; }}
            .stat .label {{ color: #6c757d; }}
            .tag {{ display: inline-block; background: #e9ecef; color: #495057; padding: 2px 8px; border-radius: 3px; font-size: 12px; margin-right: 5px; }}
            .lesson {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 10px 0; border-radius: 4px; }}
            .badge {{ display: inline-block; padding: 3px 8px; border-radius: 3px; font-size: 12px; color: white; }}
            .badge-green {{ background: #28a745; }}
            .badge-blue {{ background: #17a2b8; }}
            .badge-orange {{ background: #fd7e14; }}
            footer {{ text-align: center; color: #999; padding: 20px; }}
        </style>
    </head>
    <body>
    <div class="container">
        <h1>📊 تقرير الأسبوع - EsprieAether</h1>
        <p class="subtitle">تاريخ التقرير: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC</p>

        <div class="stats">
            <div class="stat">
                <div class="number">{message_count}</div>
                <div class="label">رسائل المedian</div>
            </div>
            <div class="stat">
                <div class="number">{task_count}</div>
                <div class="label">المهام الإجمالية</div>
            </div>
            <div class="stat">
                <div class="number">{proposed_count}</div>
                <div class="label">المهام المقترحة</div>
            </div>
            <div class="stat">
                <div class="number">{done_count}</div>
                <div class="label">المهام المكتملة</div>
            </div>
            <div class="stat">
                <div class="number">{skill_count}</div>
                <div class="label">مهارات تم اعتمادها</div>
            </div>
            <div class="stat">
                <div class="number">{total_skills}</div>
                <div class="label">مهارات متابعة</div>
            </div>
        </div>

        <div class="card">
            <h2>🧠 الدروس المست-conjugate الأسبوعية</h2>
            <p class="subtitle">أحدث {len(recent_lessons)} كلمة رائجة لدى النظام</p>
            <div id="lessons">
                {''.join(f'<div class="lesson">📌 {escape_html(str(l)[:150])}</div>' for l in recent_lessons)}
            </div>
        </div>

        <div class="card">
            <h2>🔗 تتبيل المهارات</h2>
            <p class="subtitle">المهارات المقترحة: {candidates.get('total', 0)} | الم cutoffs: {skill_count}</p>
            <div id="skills">
                {''.join(f'<span class="tag">✅ {escape_html(s.get("name",""))}</span>' for s in tracker.get("skills", [])[:10])}
            </div>
        </div>

        <div class="card">
            <h2>📋 أنشطة الأسبوع</h2>
            <p class="subtitle">رسائل المedian ({agent_count})</p>
            <div id="activities">
                {''.join(f'<span class="tag">{escape_html(str(m.get("agent","")))}: {escape_html(str(m.get("text",""))[:80])}</span>' for m in board[:10])}
            </div>
        </div>

        <footer>
            <p>EsprieAether Sovereign Local AI · تقارير الأسبوع</p>
        </footer>
    </div>
    </body>
    </html>
    """

    # save HTML
    REPORT_FILE.write_text(report_html, encoding="utf-8")

    # save markdown summary
    summary_md = f"""# 🎯 تقرير الأسبوع - EsprieAether
*تاريخ التقرير: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC*

## الإحصائيات
| المعلومة | القيمة |
|----------|---------|
| رسائل المedian | {message_count} |
| المهام الإجمالية | {task_count} |
| المهام المقترحة | {proposed_count} |
| المهام المكتملة | {done_count} |
| مهارات تم اعتمادها | {skill_count} |
| مهارات متابعة | {total_skills} |

## الدروس المست-conjugate
"""
    summary_md += "\n".join([f"1. {escape_html(str(l)[:120])}" for l in recent_lessons[:10]]) + "\n"

    SUMMARY_FILE.write_text(summary_md, encoding="utf-8")

    print(f"✅ التقرير مكتوب: {REPORT_FILE}")
    print(f"✅ الملخص: {SUMMARY_FILE}")

    # save to lessons log
    lessons["seen"].append(f"[{AGENT}] report generated: {message_count} messages, {task_count} tasks")
    with open(DATA_DIR / "lessons.json", "w", encoding="utf-8") as f:
        json.dump(lessons, f, ensure_ascii=False, indent=2)

    return report_html


def escape_html(text):
    """تسوية HTML."""
    if not text:
        return ""
    import re
    text = str(text)
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    return text


if __name__ == "__main__":
    generate_report()
