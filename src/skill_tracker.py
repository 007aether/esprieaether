#!/usr/bin/env python3
"""
SKILL ADOPTION TRACKER
----------------------
ربط المهارات (skill candidates) بالنتائج الفعلية.
يقوم بتتبع أي مهارة ناقشتها، وأيها اتخذ، وأي النتائج التي شهدها النظام.

الاستخدام:
  python skill_tracker.py show            # عرض الحالة الحالية
  python skill_tracker.py detect          # اكتشاف الربط الجديد
  python skill_tracker.py report          # تقرير الربط
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SKILLS_FILE = BASE_DIR / "data" / "skill_candidates.json"
TRACKER_FILE = BASE_DIR / "data" / "skill_tracker.json"
VEILLE_FILE = BASE_DIR / "data" / "veille_digest.md"

# Keys في skill_tracker.json
STATUS = {
    "skills": [],          # قائمة بالمهارات المرصولة
    "adopted": [],         # المهارات التي اتخذناها
    "results": [],         # نتائج استخدام المهارة
    "last_updated": None,  # أحدث تحديث
}


def load_tracker():
    """تحميل ملف التتبع."""
    if TRACKER_FILE.exists():
        try:
            with open(TRACKER_FILE, encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception:
            pass
    return {"skills": [], "adopted": [], "results": [], "last_updated": None}


def save_tracker(data):
    """حفظ ملف التتبع."""
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_skills():
    """تحميل مرشحات المهارات من skill_candidates.json."""
    try:
        with open(SKILLS_FILE, encoding="utf-8") as f:
            data = json.load(f)
            return data.get("candidates", [])
    except Exception:
        return []


def load_veille():
    """تحميل الش{verbatim}.
    """
    try:
        with open(VEILLE_FILE, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def detect_skill_usage(skill_names):
    """يجد مرات استخدام مهارة في وثائق النظام (مثلاً أوراق الـ bot والأوامر)."""
    usage = {}
    for name in skill_names:
        # name هنا هو اسم المهارة (string) - لست كائن
        # نبحث في المتغيرات الرئيسية
        count = 0
        files = []

        # نبحث في bot_commands.txt
        bot_cmds = BASE_DIR / "data" / "bot_commands.txt"
        if bot_cmds.exists():
            try:
                content = bot_cmds.read_text(encoding="utf-8", errors="ignore")
                if name.lower() in content.lower():
                    count += 1
                    files.append("bot_commands.txt")
            except Exception:
                pass

        # نبحث في knowledge_router.py
        kr_file = BASE_DIR / "src" / "knowledge_router.py"
        if kr_file.exists():
            try:
                content = kr_file.read_text(encoding="utf-8", errors="ignore")
                if name.lower() in content.lower():
                    count += 1
                    files.append("knowledge_router.py")
            except Exception:
                pass

        if count > 0:
            usage[name] = {"count": count, "files": files}

    return usage


def track_skill(skill_name, outcome, evidence=""):
    """
    تسجيل استخدام مهارة ونتيجة ذلك.
    outcome: "adopted" | "rejected" | "evaluated" | "usage"
    """
    data = load_tracker()
    if skill_name not in [s["name"] for s in data["skills"]]:
        data["skills"].append({
            "name": skill_name,
            "outcome": outcome,
            "count": 1,
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "evidence": evidence,
        })
    else:
        for s in data["skills"]:
            if s["name"] == skill_name:
                s["outcome"] = outcome
                s["count"] = s.get("count", 0) + 1
                s["last_seen"] = datetime.now(timezone.utc).isoformat()
                s["evidence"] = evidence
                break
    save_tracker(data)


def auto_track(skills, veille_content):
    """
    مسح تلقائي للربط بين المهارات والنتائج.
    تبحث عن مراجع للمهارات في كود النظام والوثائق.
    """
    data = load_tracker()
    skill_names = [s.get("name", "") for s in skills]

    # اكتشاف الاستخدام
    usage = detect_skill_usage(skill_names)

    for skill in skills:
        name = skill.get("name", "")
        if name in usage:
            track_skill(
                name,
                outcome="usage",
                evidence=f"تم الاقتباس في {', '.join(usage[name]['files'])}"
            )

    save_tracker(data)
    return data


def summarize():
    """عرض ملخص التتبيل."""
    data = load_tracker()
    skills = load_skills()

    print(f"\n📊 تتبيل المهارات — آخر تحديث: {data.get('last_updated', 'لم يحدث')}")
    print(f"   المهارات المسجَّلة: {len(data['skills'])}")
    print(f"   المهارات المتاحة: {len(skills)}")
    print()

    # المهارات المقترحة
    adopted = [s for s in data["skills"] if s.get("outcome") == "adopted"]
    usage = [s for s in data["skills"] if s.get("outcome") == "usage"]
    rejected = [s for s in data["skills"] if s.get("outcome") == "rejected"]

    print(f"✅ Adopt: {len(adopted)} مهارة")
    for s in adopted[:5]:
        print(f"   - {s['name']} (×{s.get('count', 0)})")

    print(f"\n🔄 Usage: {len(usage)} مهارة")
    for s in usage[:5]:
        print(f"   - {s['name']} (×{s.get('count', 0)})")

    print(f"\n❌ Rejected: {len(rejected)} مهارة")
    for s in rejected[:3]:
        print(f"   - {s['name']}")

    return data


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Skill adoption tracker")
    parser.add_argument("action", choices=["show", "detect", "report", "track"])
    args = parser.parse_args()

    if args.action == "show":
        summarize()
    elif args.action == "detect":
        skills = load_skills()
        veille = load_veille()
        data = auto_track(skills, veille)
        summarize()
        print(f"\n✅ تم التحديث ({data.get('last_updated')})")
    elif args.action == "report":
        summarize()
    elif args.action == "track":
        # استدعاء للربط يدوياً
        print("استدعاء للربط يدوياً - لا يوجد بيانات")
