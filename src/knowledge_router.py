#!/usr/bin/env python3
"""
KNOWLEDGE ROUTER ROBOT
----------------------
بصيص الاتصال بين ذاكرة الش안건 (veille digest + skill candidates)
 ونظام الوكلاء (agent mesh).

المعرفة مش كافية لو ما نقلتوش لنظام اللغة. هذا الربوت:
  1. يقرأ veille digest + skill candidates
  2. يفرّق "ما حددش" و "اقتراح محدد" و "معلومة شغالة"
  3. يضع كل حاجه على ملف المedian (data/agent_board.json)
  4. يقدم مهمة لمهام (propose_task) لوكيل التطوير (evolve)

الاستخدام:
  python knowledge_router.py
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BOARD_FILE = BASE_DIR / "data" / "agent_board.json"
PROPOSED_FILE = BASE_DIR / "data" / "agent_proposed_tasks.json"
VEILLE_FILE = BASE_DIR / "data" / "veille_digest.md"
SKILLS_FILE = BASE_DIR / "data" / "skill_candidates.json"

AGENT = "knowledge"
TAG_KNOWLEDGE = "knowledge"
TAG_ROUTE = "route"
TAG_VERDICT = "verdict"

sys.path.insert(0, str(BASE_DIR / "src"))
try:
    import agent_mesh as am
    HAVE_AM = True
except ImportError:
    HAVE_AM = False


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def knowledge_db_path():
    """مسار قاعدة بيانات المعرفة (مجلد knowledge_base في data/)"""
    kb_dir = BASE_DIR / "data" / "knowledge_base"
    kb_dir.mkdir(parents=True, exist_ok=True)
    return kb_dir / "knowledge_index.json"


def load_knowledge_db():
    """قاعدة المعرفة: تعريفات + نتائج البحث."""
    path = knowledge_db_path()
    if path.exists():
        try:
            return load_json(path, {})
        except Exception:
            pass
    return {"items": [], "searched_at": None}


def save_knowledge_db(db):
    save_json(knowledge_db_path(), db)


def store_knowledge(text, tags=None, source="veille"):
    """يحفظ معلومة في قاعدة المعرفة (capability 2)."""
    db = load_knowledge_db()
    if not isinstance(db, dict):
        db = {"items": [], "searched_at": None}
    item = {
        "text": text,
        "tags": tags or [],
        "source": source,
        "stored_at": datetime.now(timezone.utc).isoformat(),
    }
    db["items"].append(item)
    save_knowledge_db(db)
    return item


def search_knowledge(query, limit=5):
    """يبحث في قاعدة المعرفة (capability 2 - نص قائمة وورد مفتاح)."""
    db = load_knowledge_db()
    items = db.get("items", [])
    if not query:
        return items[:limit]
    q = query.lower().strip()
    results = []
    for item in items:
        hit = False
        if q in item.get("text", "").lower():
            hit = True
        if q in " ".join(item.get("tags", [])).lower():
            hit = True
        if q in item.get("source", "").lower():
            hit = True
        if hit:
            results.append(item)
    # تحميل جديد إذا كان محدود
    if len(results) > limit:
        results = results[:limit]
    return results


def parse_veille_digest(path):
    """يستخرج القوائم تحت كل قسم فيdigest"""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {}

    sections = {}
    current = None
    for line in text.splitlines():
        line = line.strip()
        # Sections: ## name
        m = re.match(r"^##\s+(.+)$", line)
        if m:
            current = m.group(1).strip()
            sections[current] = []
            continue
        # Items: - [stars] [name] — description
        if current and line.startswith("- ["):
            # keep the full line for later processing
            sections[current].append(line)
    return sections


def parse_skill_candidates(path):
    """يستخرج من skill_candidates.json"""
    data = load_json(path, {})
    candidates = data.get("candidates", [])
    status = {
        "total": data.get("total", len(candidates)),
        "adopt": data.get("adopt", 0),
        "reference": data.get("reference", 0),
        "candidates": candidates,
    }
    return status


def classify(line):
    """
    تصنيف السطر: 'unknown' | 'adopted' | 'informational'
    'adopted': يحتوي على كلمات قرار أو نجمة
    """
    text = line.lower()
    if re.search(r"\b(adopt|adopt|build)\b", text):
        return "adopted"
    if re.search(r"\b(reference|read)\b", text):
        return "informational"
    return "unknown"


def build_message(sections, skills):
    parts = []
    total_keywords = 0
    total_unknown = 0

    for section, items in sections.items():
        n_unk = 0
        n_adv = 0
        for item in items:
            if classify(item) == "adopted":
                n_adv += 1
            else:
                n_unk += 1
        if n_unk or n_adv:
            parts.append(f"- [{section}]: {n_adv} اقتراح متوحّد، {n_unk} لم يحدد القرار بعد")
            total_unknown += n_unk
            total_keywords += n_adv

    skills_text = (
        f"{skills.get('total', 0)} مرشح، {skills.get('adopt', 0)} اتخذ، {skills.get('reference', 0)} مرجع"
    )
    return "\n".join(parts) or "لا توجد قوائم بالـ digest للفئة."

def build_task(sections, skills):
    body = build_message(sections, skills)
    return {
        "agent": "evolve",
        "title": f"معالجة معرفة جديدة من الش안건 ({len(sections)} أقسام)",
        "description": body,
        "status": "proposed",
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def post_to_board(text, tags=None):
    """يضع رسالة على ملف المedian (agent_board.json)"""
    board = load_json(BOARD_FILE, [])
    if not isinstance(board, list):
        board = []
    msg = {
        "id": f"route-{int(datetime.now(timezone.utc).timestamp() * 1000)}-{AGENT}",
        "agent": AGENT,
        "text": text,
        "tags": tags or [TAG_KNOWLEDGE, TAG_ROUTE],
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    board.append(msg)
    # حافظ على السعة القصوى 200 رسالة
    if len(board) > 200:
        board = board[-200:]
    save_json(BOARD_FILE, board)
    return msg


def run():
    print(f"\n🔗 [{AGENT}] يربط ذاكرة الش안건 بالنظام...")
    sections = parse_veille_digest(VEILLE_FILE)
    skills = parse_skill_candidates(SKILLS_FILE)

    if not sections:
        print("⚠️  لا يمكن قراءة veille digest، التوقف.")
        return False

    msg_text = build_message(sections, skills)
    task = build_task(sections, skills)

    # capability 2a: store the knowledge to the knowledge base
    store_knowledge(
        text=msg_text,
        tags=[TAG_KNOWLEDGE, TAG_ROUTE, TAG_VERDICT],
        source="veille",
    )

    # capability 2b: auto-search existing knowledge before posting
    # (search queries from the message text for prioritization)
    search_lines = re.findall(r"\[([^\]]+)\]", msg_text)
    for sec in search_lines[:5]:
        results = search_knowledge(sec, limit=3)
        if results:
            print(f"🔎 بحث في {sec!r}: {len(results)} نتائج سابقة مسجّلة")

    # 1) اللصق على الملف
    post_to_board(msg_text, [TAG_KNOWLEDGE, TAG_ROUTE, TAG_VERDICT])
    print(f"✅ وصل إلى المedian ({len(sections)} أقسام)")

    # 2) الإرسال للمهمة لمهام
    if HAVE_AM:
        am.propose_task(task["agent"], task["title"], task["description"])
        print(f"✅ وصلت مهام لـ '{task['agent']}'")
    else:
        # بدون agent_mesh موجود، نكتب المهمة في الملف مباشرة
        tasks = load_json(PROPOSED_FILE, [])
        if not isinstance(tasks, list):
            tasks = []
        tasks.append(task)
        save_json(PROPOSED_FILE, tasks)
        print(f"✅ وصلت مهام لـ '{task['agent']}' (بدون agent_mesh)")

    # 3) اعادة في lessons
    lessons_path = BASE_DIR / "data" / "lessons.json"
    lessons = load_json(lessons_path, {})
    for key in ["seen", "diagnosed", "fixes_proposed"]:
        if not isinstance(lessons.get(key), list):
            lessons[key] = []
    lessons["seen"].append(f"[{AGENT}] route={len(sections)} sections, {skills.get('adopt', 0)} adopt")
    save_json(lessons_path, lessons)

    print("\n📊 الإنجاز:")
    print(f"  - أقسام وشأن: {len(sections)}")
    print(f"  - مهام: {skills.get('total', 0)} (مهمة {skills.get('adopt', 0)} اتخذت)")
    print(f"  - ملف: {BOARD_FILE.name}")
    return True


if __name__ == "__main__":
    run()
