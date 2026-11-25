#!/usr/bin/env python3
"""
KNOWLEDGE INTERFACE (API)
--------------------------
واجهة برمجية للمعرفة (knowledge interface) تعمل على:
  - /knowledge/search?q=<word>   - بحث عن معلومة
  - /knowledge/stats             - إحصائيات المعرفة
  - /knowledge/recent            - آخر المعرفة المضافة

الاستخدام:
  من Flask app: من الشكل التالي نضيف الـ blueprint
  app.register_blueprint(knowledge_bp, url_prefix="/api")

  GET /knowledge/search?q= الذكاء
  GET /knowledge/stats
  GET /knowledge/recent
"""

from flask import Blueprint, request, jsonify
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
KB_FILE = BASE_DIR / "data" / "knowledge_base" / "knowledge_index.json"

# Blueprint للواجهة البرمجية
api_bp = Blueprint("knowledge_api", __name__, url_prefix="/knowledge")


# ─── Helpers ─────────────────────────────────────────────────

def load_kb():
    """تحميل قاعدة المعرفة."""
    if KB_FILE.exists():
        try:
            with open(KB_FILE, encoding="utf-8") as f:
                data = json.load(f)
                return data.get("items", [])
        except Exception:
            pass
    return []


def search_knowledge(query, limit=50):
    """بحث في المعرفة حسب الكلمة المفتاحية."""
    if not query:
        return []
    q = query.lower().strip()
    items = load_kb()
    results = []
    for item in items:
        text = item.get("text", "")
        tags = " ".join(item.get("tags", []))
        source = item.get("source", "")
        if q in text.lower() or q in tags.lower() or q in source.lower():
            results.append(item)
        if len(results) >= limit:
            break
    return results


# ─── Routes ──────────────────────────────────────────────────

@api_bp.route("/search")
def search():
    """بحث في المعرفة."""
    q = request.args.get("q", "").strip()
    limit = request.args.get("limit", 50, type=int)
    results = search_knowledge(q, limit)
    return jsonify({
        "total": len(results),
        "query": q,
        "results": results,
    })


@api_bp.route("/stats")
def stats():
    """إحصائيات المعرفة."""
    items = load_kb()
    tags = {}
    sources = {}
    for item in items:
        for tag in item.get("tags", []):
            tags[tag] = tags.get(tag, 0) + 1
        src = item.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1

    return jsonify({
        "total": len(items),
        "sources": sources,
        "top_tags": sorted(tags.items(), key=lambda x: x[1], reverse=True)[:10],
        "recent_stored": [item.get("stored_at") for item in items[-10:] if item.get("stored_at")],
    })


@api_bp.route("/recent")
def recent():
    """أحدث المعرفة المضافة."""
    items = load_kb()
    # نرتيب حسب التاريخ
    items.sort(key=lambda x: x.get("stored_at", ""), reverse=True)
    return jsonify({
        "total": len(items),
        "recent": items[:20],
    })


@api_bp.route("/health")
def health():
    """التحقق من صحة الواجهة."""
    if KB_FILE.exists():
        size = KB_FILE.stat().st_size
    else:
        size = 0
    return jsonify({
        "status": "ok",
        "service": "knowledge_api",
        "file": str(KB_FILE),
        "size_bytes": size,
        "records": len(load_kb()),
    })


__all__ = ["api_bp"]
